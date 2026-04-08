import struct
import lzma
import os
from Crypto.Cipher import AES

# Klucze z modelu XM4 - sprawdzamy czy pasują do XB910N
KEY = b"eibohjeCh6uegahf"
IV  = b"miefeinuShu9eilo"

def try_extract(bin_file):
    print(f"Próba deszyfrowania pliku: {bin_file}")
    with open(bin_file, "rb") as f:
        data = f.read()
    
    # Ciało zaszyfrowane zaczyna się od offsetu 0x1000
    body = data[0x1000:]
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = cipher.decrypt(body)

    try:
        # Sprawdzamy czy pierwsze bajty po deszyfrowaniu to nagłówek LZMA
        # Standardowy nagłówek LZMA zaczyna się od bajtu właściwości (np. 0x5D)
        props = decrypted[0]
        lc, lp, pb = props % 9, (props // 9) % 5, (props // 9) // 5
        dict_size = struct.unpack_from("<I", decrypted, 1)[0]
        
        print(f"Wykryte parametry LZMA: lc={lc}, lp={lp}, pb={pb}, dict={dict_size}")
        
        filters = [{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp, "pb": pb, "dict_size": dict_size}]
        d = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        
        # Próbujemy dekompresować (pominąć 13 bajtów nagłówka LZMA)
        decompressed = d.decompress(decrypted[13:], max_length=0x100000)
        
        if decompressed.startswith(b"\x01\x00\x00\x00"): # Wersja 1 obrazu
            print("SUKCES! Klucz pasuje. Wyodrębniam audio...")
            
            num_entries = struct.unpack_from("<I", decompressed, 4)[0]
            os.makedirs("extracted_audio", exist_ok=True)
            
            # Pierwszy wpis powie nam jaki jest offset bazowy
            first_offset = struct.unpack_from("<I", decompressed, 12)[0]
            base = first_offset - (8 + num_entries * 8)

            for i in range(num_entries):
                off = 8 + i * 8
                size = struct.unpack_from("<I", decompressed, off)[0]
                abs_off = struct.unpack_from("<I", decompressed, off + 4)[0]
                
                with open(f"extracted_audio/prompt_{i:02d}.mp3", "wb") as f_mp3:
                    f_mp3.write(decompressed[abs_off-base : abs_off-base+size])
            
            print(f"Gotowe! Pliki w folderze 'extracted_audio'.")
        else:
            print("Deszyfrowanie przeszło, ale dane nie wyglądają na obraz audio Sony.")
            
    except Exception as e:
        print(f"BŁĄD: Klucz prawdopodobnie nie pasuje. ({e})")

if __name__ == "__main__":
    try_extract("VP_english_UPG_03.bin")