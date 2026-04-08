import asyncio
from bleak import BleakClient

DEVICE_MAC = "50:C6:C0:37:85:F4" # Wpisz swój MAC

async def main():
    async with BleakClient(DEVICE_MAC) as client:
        print(f"Połączono: {client.is_connected}")
        for service in client.services:
            print(f"\nService: {service.uuid}")
            for char in service.characteristics:
                print(f"  Char: {char.uuid} | Properties: {', '.join(char.properties)}")

asyncio.run(main())