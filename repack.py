import struct
import lzma
import os
import sys
import hashlib
from Crypto.Cipher import AES

# --- Constants ---
KEY = b"eibohjeCh6uegahf"
IV  = b"miefeinuShu9eilo"
HEADER_SIZE = 0x1000
TARGET_IMAGE_SIZE = 1048576 # 1MB

def build_audio_image_fixed(input_dir: str) -> bytes:
    files = sorted(f for f in os.listdir(input_dir) if f.endswith(".mp3"))
    image = bytearray(struct.pack("<II", 1, len(files)))
    table = bytearray()
    audio = bytearray()
    current_offset = 0x80000 + 8 + (len(files) * 8)

    for filename in files:
        with open(os.path.join(input_dir, filename), "rb") as f:
            data = f.read()
        table.extend(struct.pack("<II", len(data), current_offset))
        audio.extend(data)
        current_offset += len(data)

    full_image = image + table + audio
    return full_image.ljust(TARGET_IMAGE_SIZE, b"\x00")

def patch_header(header: bytearray, new_decomp: int, new_body: int, new_sha: bytes) -> bytearray:
    # Body Size at 0x10A, Decomp at 0x13A, SHA at 0x14A
    # Do NOT overwrite 0x106, that is the header size (4096)!
    header[0x10A:0x10E] = struct.pack("<I", new_body)
    header[0x13A:0x13E] = struct.pack("<I", new_decomp)
    header[0x14A:0x14A+32] = new_sha
    return header

def run_repack(orig_bin, input_dir, out_bin):
    target_total_size = os.path.getsize(orig_bin)
    
    # 1. Rebuild source image
    new_image = build_audio_image_fixed(input_dir)
    new_sha = hashlib.sha256(new_image).digest()
    
    # 2. Compress with RAW LZMA
    filters = [{"id": lzma.FILTER_LZMA1, "lc": 3, "lp": 0, "pb": 2, "dict_size": 16384}]
    compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters)
    compressed = compressor.compress(new_image) + compressor.flush()
    
    # Sony Header: [Props(1)][Dict(4)][UncompSize(8)]
    lzma_header = struct.pack("<BIQ", 0x5D, 16384, len(new_image))
    payload = lzma_header + compressed

    # 3. DYNAMIC BODY SIZE WITH AES ALIGNMENT
    # To prevent failing at 99% upload, we must NOT pad the payload arbitrarily to match
    # the original file size. If we feed thousands of bytes of 0xFF padding into the
    # firmware's LZMA decompressor, it will reject the file as corrupt because it finishes
    # decompressing the stream before consuming all the AES decrypted input bytes!
    # Instead, we only pad up to the next 16-byte block boundary required by AES CBC.
    current_len = len(payload)
    aes_padding = 16 - (current_len % 16)
    if aes_padding == 16: aes_padding = 0
    final_payload = payload + (b"\xFF" * aes_padding)

    # 4. ENCRYPT THE EXACT VALID PAYLOAD
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    new_body = cipher.encrypt(final_payload)
    
    # We do NOT append any unencrypted garbage. The proxy will dynamically compute
    # {FWlength} from the physical file size on disk!
    full_bin_content = new_body


    # 5. Final Patch and Save
    with open(orig_bin, "rb") as f:
        orig_header = bytearray(f.read(HEADER_SIZE))

    # NOTE: The body_size we write to the header MUST be the exact len(new_body), NOT the total padded file length,
    # otherwise Sony's decompressor will try to unpack the 0xFF trailing flash padding and crash at 99%!
    patched_header = patch_header(orig_header, len(new_image), len(new_body), new_sha)

    with open(out_bin, "wb") as f:
        f.write(patched_header)
        f.write(full_bin_content)

    print(f"SUCCESS: {out_bin} created.")
    print(f"Original Size: {target_total_size}")
    print(f"New File Size: {os.path.getsize(out_bin)}")
    print(f"SHA-256 Updated: {new_sha.hex()[:10]}...")

if __name__ == "__main__":
    run_repack(sys.argv[1], sys.argv[2], sys.argv[3])