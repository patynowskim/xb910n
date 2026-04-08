import struct
import lzma
import os
import sys
import hashlib
from Crypto.Cipher import AES

# --- Sony Constants ---
KEY = b"eibohjeCh6uegahf"
IV  = b"miefeinuShu9eilo"
HEADER_SIZE = 0x1000
BASE_OFFSET = 0x80000 # 512KB base offset for guidance region

def pkcs7_pad(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len]) * pad_len

def build_audio_image(input_dir: str) -> bytes:
    """Reconstructs the guidance image. Files must be named prompt_00.mp3, etc."""
    files = sorted(f for f in os.listdir(input_dir) if f.endswith(".mp3"))
    num_entries = len(files)
    
    # Image Header: Version (1), Count (54)
    image = bytearray(struct.pack("<II", 1, num_entries))
    
    table_size = num_entries * 8
    audio_data = bytearray()
    
    # Initial offset: Base (0x80000) + Header (8) + Table Size
    current_abs_offset = BASE_OFFSET + 8 + table_size

    # Build entry table and collect audio data
    for filename in files:
        path = os.path.join(input_dir, filename)
        with open(path, "rb") as f:
            mp3 = f.read()
        
        # Entry: [Size(u32)][Absolute Offset(u32)]
        image.extend(struct.pack("<II", len(mp3), current_abs_offset))
        audio_data.extend(mp3)
        current_abs_offset += len(mp3)

    return bytes(image + audio_data)

def repack(original_bin, input_dir, output_bin):
    print(f"[*] Loading original: {original_bin}")
    with open(original_bin, "rb") as f:
        full_data = f.read()
    
    orig_header = bytearray(full_data[:HEADER_SIZE])
    orig_body = full_data[HEADER_SIZE:]

    # --- Decrypt Original for Comparison ---
    cipher_dec = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted_orig_body = cipher_dec.decrypt(orig_body)
    
    # Parse 13-byte Sony LZMA header: [Props(1)][Dict(4)][UncompSize(8)]
    orig_props = decrypted_orig_body[0]
    orig_dict = struct.unpack_from("<I", decrypted_orig_body, 1)[0]
    orig_uncomp_size = struct.unpack_from("<Q", decrypted_orig_body, 5)[0]

    # Extract original image for diagnostic
    filters = [{"id": lzma.FILTER_LZMA1, "lc": 3, "lp": 0, "pb": 2, "dict_size": orig_dict}]
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
    # We strip the 13-byte header before decompressing
    orig_image_raw = decompressor.decompress(decrypted_orig_body[13:])

    # --- Build New Image ---
    print(f"[*] Building new image from {input_dir}...")
    new_image = build_audio_image(input_dir)
    
    # DIAGNOSTIC: Parity Check
    if hashlib.sha256(new_image).digest() == hashlib.sha256(orig_image_raw).digest():
        print("[+] SUCCESS: Uncompressed image parity achieved.")
    else:
        print("[!] WARNING: Uncompressed images differ! Parity will fail.")
        print(f"    Orig MD5: {hashlib.md5(orig_image_raw).hexdigest()}")
        print(f"    New MD5:  {hashlib.md5(new_image).hexdigest()}")

    # --- Compress and Encrypt ---
    print("[*] Compressing (LZMA1)...")
    # Tweak: Use MODE_NORMAL or MODE_FAST to try and match Sony's tool size
    filters[0]["mode"] = lzma.MODE_NORMAL 
    compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters)
    compressed_data = compressor.compress(new_image) + compressor.flush()

    new_lzma_payload = struct.pack("<BIQ", orig_props, orig_dict, len(new_image)) + compressed_data
    padded_payload = pkcs7_pad(new_lzma_payload)

    print("[*] Encrypting (AES-128-CBC)...")
    cipher_enc = AES.new(KEY, AES.MODE_CBC, IV)
    new_body = cipher_enc.encrypt(padded_payload)

    # --- Header Patching (Absolute Offsets from HxD) ---
    print("[*] Patching Header Metadata...")
    # Body Size at 0x10A
    orig_header[0x10A:0x10E] = struct.pack("<I", len(new_body))
    # Decompressed Size at 0x142
    orig_header[0x142:0x146] = struct.pack("<I", len(new_image))
    # SHA-256 of Uncompressed Image at 0x14A
    orig_header[0x14A:0x14A+32] = hashlib.sha256(new_image).digest()

    # --- Final Assemble ---
    with open(output_bin, "wb") as f:
        f.write(orig_header)
        f.write(new_body)

    print(f"\n[DONE] Created {output_bin} ({len(new_body) + 4096} bytes)")
    size_diff = (len(new_body) + 4096) - len(full_data)
    print(f"[Info] Size difference vs original: {size_diff} bytes")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python repack.py <orig.bin> <mp3_dir> <out.bin>")
    else:
        repack(sys.argv[1], sys.argv[2], sys.argv[3])