import struct
import lzma
import hashlib
from Crypto.Cipher import AES

KEY = b"eibohjeCh6uegahf"
IV  = b"miefeinuShu9eilo"
HEADER_SIZE = 0x1000

def analyze(target_bin):
    with open(target_bin, "rb") as f:
        data = f.read()
    
    # Decrypt and Decompress
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = cipher.decrypt(data[HEADER_SIZE:])
    
    # LZMA1 Params
    filters = [{"id": lzma.FILTER_LZMA1, "lc": 3, "lp": 0, "pb": 2, "dict_size": 16384}]
    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
    # Skip 13-byte LZMA header
    image = decompressor.decompress(decrypted[13:])
    
    print(f"--- Raw Image Analysis ---")
    print(f"Total Image Size: {len(image)} bytes")
    print(f"Image MD5:        {hashlib.md5(image).hexdigest()}")
    
    version, count = struct.unpack_from("<II", image, 0)
    print(f"Version: {version} | Entry Count: {count}")
    
    first_offset = struct.unpack_from("<II", image, 8 + 4)[0]
    table_end = 8 + (count * 8)
    print(f"Table ends at:   0x{table_end:X}")
    print(f"First MP3 starts: 0x{first_offset - 0x80000:X}")
    
    gap = (first_offset - 0x80000) - table_end
    print(f"Padding after table: {gap} bytes")

    print("\n--- First 5 Entries ---")
    for i in range(5):
        size, abs_off = struct.unpack_from("<II", image, 8 + (i*8))
        rel_off = abs_off - 0x80000
        print(f"Entry {i:02d}: Size {size:6} | Rel Offset 0x{rel_off:05X}")

if __name__ == "__main__":
    analyze("VP_english_UPG_03.bin")