import argparse
import hashlib
import lzma
import os
import struct
import sys
from Crypto.Cipher import AES

# Known Sony Airoha FOTA AES-128-CBC keys
MODEL_KEYS = {
    "xb910n": (b"Quah8gangeizagie", b"ahcee8Yo1iekiu6e"),
    "xm4":    (b"eibohjeCh6uegahf", b"miefeinuShu9eilo"),
    "wfxm4":  (b"xoPh9reedaN6hai6", b"Ere8Quaixah0mee3"),
}

HEADER_SIZE = 0x1000
TAG_BASIC_INFO = 0x0011
TAG_MOVER_INFO = 0x0012
TAG_INTEGRITY  = 0x0014


def detect_key_and_decrypt(enc_body: bytes, forced_key: bytes = None, forced_iv: bytes = None):
    candidates = [(forced_key, forced_iv)] if (forced_key and forced_iv) else list(MODEL_KEYS.values())
    for key, iv in candidates:
        dec = AES.new(key, AES.MODE_CBC, iv).decrypt(enc_body)
        props = dec[0]
        dict_size = struct.unpack_from("<I", dec, 1)[0]
        if props <= 224 and dict_size in (4096, 8192, 16384, 32768, 65536):
            lc = props % 9
            rem = props // 9
            lp = rem % 5
            pb = rem // 5
            try:
                filters = [{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp, "pb": pb, "dict_size": dict_size}]
                img = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters).decompress(dec[13:])
                return key, iv, {"props": props, "lc": lc, "lp": lp, "pb": pb, "dict_size": dict_size}, img
            except lzma.LZMAError:
                pass
    raise RuntimeError("Could not decrypt/decompress source .bin with known keys")


def walk_tlv(header: bytes, start: int = 0x100):
    entries = {}
    pos = start
    while pos + 4 <= HEADER_SIZE:
        tag, length = struct.unpack_from("<HH", header, pos)
        if tag == 0 or tag == 0xFFFF or pos + 4 + length > HEADER_SIZE:
            break
        entries[tag] = (pos, length, bytes(header[pos + 4 : pos + 4 + length]))
        pos += 4 + length
    return entries


def patch_header(header: bytearray, body_size: int, decomp_size: int, sha256_digest: bytes):
    tlvs = walk_tlv(header)
    if TAG_BASIC_INFO not in tlvs or TAG_MOVER_INFO not in tlvs or TAG_INTEGRITY not in tlvs:
        raise RuntimeError("Required TLV tags (0x11/0x12/0x14) missing in header")

    pos, length, _ = tlvs[TAG_BASIC_INFO]
    if length < 10:
        raise RuntimeError(f"BASIC_INFO TLV too short: {length}")
    struct.pack_into("<I", header, pos + 4 + 6, body_size)

    pos, length, _ = tlvs[TAG_MOVER_INFO]
    if length < 16:
        raise RuntimeError(f"MOVER_INFO TLV too short: {length}")
    struct.pack_into("<I", header, pos + 4 + 8, decomp_size)

    pos, length, _ = tlvs[TAG_INTEGRITY]
    if length < 36:
        raise RuntimeError(f"INTEGRITY TLV too short: {length}")
    header[pos + 4 + 4 : pos + 4 + 4 + 32] = sha256_digest


class VoiceImage:
    def __init__(self, blob: bytes):
        self.raw_size = len(blob)
        self.version, self.num_entries = struct.unpack_from("<II", blob, 0)
        if self.num_entries == 0 or self.num_entries > 256:
            raise ValueError(f"Unexpected num_entries={self.num_entries}")
        table_end = 8 + self.num_entries * 8
        first_abs = struct.unpack_from("<I", blob, 12)[0]
        self.base_offset = first_abs - table_end

        self.slots = []
        last_end = table_end
        for i in range(self.num_entries):
            sz, abs_off = struct.unpack_from("<II", blob, 8 + i * 8)
            rel = abs_off - self.base_offset
            self.slots.append(blob[rel : rel + sz])
            last_end = max(last_end, rel + sz)

        # Preserve any trailing metadata (e.g. version string '1.0.3' at 0x130FC0 on XB910N)
        self.orig_tail_offset = last_end
        self.orig_tail = blob[last_end:]
        nz = [idx for idx, b in enumerate(self.orig_tail) if b != 0]
        self.first_tail_meta_abs = (last_end + nz[0]) if nz else self.raw_size

    def serialize(self) -> bytes:
        n = len(self.slots)
        out = bytearray(struct.pack("<II", self.version, n))
        out.extend(b"\x00" * (n * 8))
        for i, data in enumerate(self.slots):
            abs_off = self.base_offset + len(out)
            struct.pack_into("<II", out, 8 + i * 8, len(data), abs_off)
            out.extend(data)

        if len(out) > self.first_tail_meta_abs:
            raise ValueError(
                f"Audio payload ({len(out)} B) overlaps trailing image metadata at 0x{self.first_tail_meta_abs:X}"
            )

        # Pad up to raw_size while preserving trailing metadata bytes at their exact offsets
        tail_slice_start = len(out) - self.orig_tail_offset
        if tail_slice_start >= 0:
            out.extend(self.orig_tail[tail_slice_start:])
        else:
            out.extend(b"\x00" * (-tail_slice_start))
            out.extend(self.orig_tail)

        assert len(out) == self.raw_size
        return bytes(out)


def run_repack(orig_bin: str, out_bin: str, input_dir: str = None, slot_overrides: dict = None,
               key_bytes: bytes = None, iv_bytes: bytes = None):
    with open(orig_bin, "rb") as f:
        orig_data = f.read()

    header = bytearray(orig_data[:HEADER_SIZE])
    key, iv, lzma_params, orig_img = detect_key_and_decrypt(orig_data[HEADER_SIZE:], key_bytes, iv_bytes)

    img = VoiceImage(orig_img)
    print(f"Loaded {orig_bin}: ver={img.version}, slots={img.num_entries}, "
          f"base=0x{img.base_offset:08X}, image_size={img.raw_size}")

    if input_dir:
        files = sorted(f for f in os.listdir(input_dir) if f.endswith(".mp3"))
        if len(files) != img.num_entries:
            raise ValueError(f"Expected {img.num_entries} mp3 files in {input_dir}, got {len(files)}")
        for i, fn in enumerate(files):
            with open(os.path.join(input_dir, fn), "rb") as f:
                img.slots[i] = f.read()

    if slot_overrides:
        for slot_idx, mp3_path in slot_overrides.items():
            if not (0 <= slot_idx < img.num_entries):
                raise ValueError(f"Slot {slot_idx} out of range (0..{img.num_entries - 1})")
            with open(mp3_path, "rb") as f:
                new_mp3 = f.read()
            print(f"  Replacing slot {slot_idx:02d}: {len(img.slots[slot_idx])} B -> {len(new_mp3)} B ({mp3_path})")
            img.slots[slot_idx] = new_mp3

    new_image = img.serialize()
    new_sha = hashlib.sha256(new_image).digest()

    filters = [{
        "id": lzma.FILTER_LZMA1,
        "lc": lzma_params["lc"],
        "lp": lzma_params["lp"],
        "pb": lzma_params["pb"],
        "dict_size": lzma_params["dict_size"],
        "preset": 0,
    }]
    compressed = lzma.compress(new_image, format=lzma.FORMAT_RAW, filters=filters)
    lzma_header = struct.pack("<BIQ", lzma_params["props"], lzma_params["dict_size"], len(new_image))
    payload = lzma_header + compressed

    aes_pad = (-len(payload)) % 16
    if aes_pad:
        payload += b"\xFF" * aes_pad

    new_body = AES.new(key, AES.MODE_CBC, iv).encrypt(payload)
    patch_header(header, len(new_body), len(new_image), new_sha)

    full = bytes(header) + new_body
    # Critical integrity hash verified on-device at CheckIntegrity (0x1C01)
    file_checksum = hashlib.sha256(full[0x100:]).digest()
    final_data = file_checksum + full[32:]

    with open(out_bin, "wb") as f:
        f.write(final_data)

    print(f"SUCCESS: {out_bin} ({len(final_data)} B, sha1={hashlib.sha1(final_data).hexdigest()})")
    print(f"  Header SHA-256 (0x000): {file_checksum.hex()[:16]}...")
    print(f"  Image  SHA-256 (0x14A): {new_sha.hex()[:16]}...")


def main():
    p = argparse.ArgumentParser(description="Repack Sony Airoha voice prompt .bin (WH-XB910N / WH-1000XM4)")
    p.add_argument("orig_bin", help="Original VP_*.bin template")
    p.add_argument("input_dir_or_out", help="MP3 folder (legacy 3-arg mode) or output .bin path (with --slot)")
    p.add_argument("out_bin", nargs="?", help="Output .bin path (legacy 3-arg mode)")
    p.add_argument("--slot", action="append", default=[], metavar="N=PATH",
                   help="Replace slot index N with MP3 file PATH (repeatable)")
    p.add_argument("--key", help="Optional 16-byte ASCII AES key")
    p.add_argument("--iv", help="Optional 16-byte ASCII AES IV")
    args = p.parse_args()

    overrides = {}
    for spec in args.slot:
        idx_s, path = spec.split("=", 1)
        overrides[int(idx_s)] = path

    if args.out_bin:
        input_dir = args.input_dir_or_out
        out_bin = args.out_bin
    else:
        input_dir = None
        out_bin = args.input_dir_or_out

    key_b = args.key.encode() if args.key else None
    iv_b = args.iv.encode() if args.iv else None
    run_repack(args.orig_bin, out_bin, input_dir=input_dir, slot_overrides=overrides, key_bytes=key_b, iv_bytes=iv_b)


if __name__ == "__main__":
    main()
