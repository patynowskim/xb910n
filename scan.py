import asyncio
from bleak import BleakClient, exc

# Adres MAC Twoich słuchawek XB910N (musisz go znaleźć np. skanując BLE)
#DEVICE_MAC = "14:3F:A6:E2:1F:8A"
#DEVICE_MAC = "50:66:00:5F:A4:B1" #LE
DEVICE_MAC = "50:C6:C0:37:85:F4"
# UUID z artykułu
TX_UUID = "bfd869fa-a3f2-4c2f-bcff-3eb1ec80cead"
RX_UUID = "2a6b6575-faf6-418c-923f-ccd63a56d955"

dumped_data = bytearray()

def notification_handler(sender, data):
    # Logujemy wszystko co przychodzi, żeby zobaczyć strukturę
    print(f"DEBUG: Otrzymano surowe dane: {data.hex()}")
    # Zazwyczaj pierwsze bajty odpowiedzi to nagłówek RACE, który potem odetniemy
    dumped_data.extend(data)

def build_race_pkt(msg_type, payload):
    """Buduje ramkę RACE: [0x05, 0x5A, Length(2b), MsgType(2b), Payload, Checksum]"""
    # Długość to MsgType (2b) + Payload
    length = 2 + len(payload)
    pkt = bytearray([0x05, 0x5A])
    pkt.extend(length.to_bytes(2, 'little'))
    pkt.extend(msg_type.to_bytes(2, 'little'))
    pkt.extend(payload)
    # Prosta suma kontrolna (XOR wszystkich bajtów od długości)
    checksum = 0
    for b in pkt[2:]:
        checksum ^= b
    pkt.append(checksum)
    return pkt

async def main():
    async with BleakClient(DEVICE_MAC) as client:
        print(f"Połączono. Startuję notyfikacje na {RX_UUID}")
        await client.start_notify(RX_UUID, notification_handler)
        
        # 0x0403 to RACE_STORAGE_PAGE_READ
        msg_type = 0x0403
        
        # Testujemy tylko stronę 0 i 1
        for page in range(2):
            # Payload dla 0x0403 to zazwyczaj 2-bajtowy numer strony
            payload = page.to_bytes(2, 'little')
            packet = build_race_pkt(msg_type, payload)
            
            print(f"Wysyłam stronę {page}: {packet.hex()}")
            await client.write_gatt_char(TX_UUID, packet, response=True)
            await asyncio.sleep(1.0) # Dajemy mu sekundę na "namysł"

        if len(dumped_data) > 0:
            with open("xb910n_test.bin", "wb") as f:
                f.write(dumped_data)
            print(f"Sukces! Dane zapisane.")
        else:
            print("Cisza... spróbujmy bez sumy kontrolnej lub z innym msg_type.")

asyncio.run(main())