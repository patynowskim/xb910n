import struct
import lzma
import os
import sys
import hashlib
from Crypto.Cipher import AES

# Sony Keys
KEY = b"eibohjeCh6uegahf"
IV  = b"miefeinuShu9eilo"
HEADER_SIZE = 0x1000

def repack(original_bin, input_dir, output_bin):
    with open(original_bin, "rb") as f:
        orig_data = f.read()
    
    orig_header = bytearray(orig_data[:HEADER_SIZE])
    
    # --- 1. Identify Original Metadata ---
    # We need to know EXACTLY what we are replacing.
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted_body = cipher.decrypt(orig_data[HEADER_SIZE:])
    
    # Get original decompressed size from the 13-byte LZMA header
    orig_uncomp_size = struct.unpack_from("<Q", decrypted_body, 5)[0]
    orig_body_size = len(orig_data) - HEADER_SIZE
    
    # Get original image SHA
    filters = [{"id": lzma.FILTER_LZMA1, "lc": 3, "lp": 0, "pb": 2, "dict_size": 16384}]
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
    orig_image = decompressor.decompress(decrypted_body[13:])
    orig_sha256 = hashlib.sha256(orig_image).digest()

    # --- 2. Create New Content ---
    from repack_vp import build_image # Assuming your build_image logic is same
    new_image = build_image(input_dir)
    new_sha256 = hashlib.sha256(new_image).digest()
    new_uncomp_size = len(new_image)

    compressor = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filters)
    compressed = compressor.compress(new_image) + compressor.flush()
    
    # 13-byte Sony LZMA Header
    lzma_head = struct.pack("<BIQ", (2*5+0)*9+3, 16384, new_uncomp_size)
    new_payload = lzma_head + compressed
    
    # AES-CBC requires 16-byte alignment. Use Null padding.
    pad_len = (16 - (len(new_payload) % 16)) % 16
    new_payload += b'\x00' * pad_len
    
    cipher_enc = AES.new(KEY, AES.MODE_CBC, IV)
    new_body_encrypted = cipher_enc.encrypt(new_payload)
    new_body_size = len(new_body_encrypted)

    # --- 3. Surgical Header Patching ---
    # Fix Image SHA-256
    sha_pos = orig_header.find(orig_sha256)
    if sha_pos != -1:
        orig_header[sha_pos:sha_pos+32] = new_sha256
        print(f"[*] Patched Image SHA at {hex(sha_pos)}")

    # Fix Uncompressed Size (Look for 4-byte and 8-bit versions)
    u_pos = orig_header.find(struct.pack("<I", int(orig_uncomp_size)))
    if u_pos != -1:
        orig_header[u_pos:u_pos+4] = struct.pack("<I", new_uncomp_size)
        print(f"[*] Patched Uncomp Size at {hex(u_pos)}")

    # Fix Body Size (The encrypted size)
    b_pos = orig_header.find(struct.pack("<I", orig_body_size))
    if b_pos != -1:
        orig_header[b_pos:b_pos+4] = struct.pack("<I", new_body_size)
        print(f"[*] Patched Body Size at {hex(b_pos)}")

    # --- 4. THE CRITICAL 99% FIX ---
    # Recalculate the first 32 bytes of the file. 
    # This is the SHA-256 of the header block itself (offset 32 to 4096).
    print("[!] Recalculating Master Header Checksum...")
    master_hash = hashlib.sha256(orig_header[32:]).digest()
    orig_header[0:32] = master_hash

    # --- 5. Save ---
    with open(output_bin, "wb") as f:
        f.write(orig_header)
        f.write(new_body_encrypted)
    
    print(f"Done. Custom size: {os.path.getsize(output_bin)}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python repack_vp.py <orig.bin> <mp3_folder> <out.bin>")
    else:
        repack(sys.argv[1], sys.argv[2], sys.argv[3])