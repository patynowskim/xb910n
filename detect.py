import asyncio
from bleak import BleakScanner

async def scan_brutal():
    print("Skanowanie (15 sekund)... Czekaj.")
    # Zwiększamy timeout i skanujemy wszystko
    devices = await BleakScanner.discover(timeout=15.0)
    
    found_any = False
    for d in devices:
        name = d.name if d.name else "Nieznane"
        print(f"Znaleziono: {name} | Adres: {d.address} ")
        if "WH-XB910N" in name or "Sony" in name:
            print(">>> POTENCJALNY KANDYDAT POWYŻEJ! <<<")
            found_any = True
            
    if not found_any:
        print("\nNadal nic. Jeśli słuchawki migają na niebiesko (parowanie), a ich nie ma, spróbuj zresetować adapter Bluetooth w Windowsie (wyłącz/włącz w menedżerze urządzeń).")

asyncio.run(scan_brutal())