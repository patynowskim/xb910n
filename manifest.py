import requests
from Crypto.Cipher import AES

# Klucz do manifestów Sony (wyciągnięty z APK)
MANIFEST_KEY = bytes.fromhex("4fa27999ffd08b1fe4d260d57b6d3c17")

# Przykładowy URL manifestu dla serii XB (może wymagać dopasowania ID modelu)
# ID dla XB910N to często 'HP004' lub podobne
url = "https://info.update.sony.net/HP002/VGIDLPB0401/info/info.xml"

def fetch_manifest(url):
    print(f"Pobieranie manifestu: {url}")
    r = requests.get(url)
    if r.status_code != 200:
        print("Błąd pobierania")
        return

    # Manifesty Sony mają nagłówek tekstowy, a potem zaszyfrowane body po podwójnym \n
    parts = r.content.split(b"\n\n")
    if len(parts) < 2:
        print("Niepoprawny format manifestu")
        return

    encrypted_body = parts[1]
    
    # Deszyfrowanie AES-128-ECB
    cipher = AES.new(MANIFEST_KEY, AES.MODE_ECB)
    decrypted = cipher.decrypt(encrypted_body)
    
    # Usuwamy padding i drukujemy XML
    print("\n--- ZDEKODOWANY MANIFEST ---")
    print(decrypted.decode('utf-8', errors='ignore'))

fetch_manifest(url)