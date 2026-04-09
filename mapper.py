"© 2026 Punksm4ck. All rights reserved."
import asyncio
from bleak import BleakScanner, BleakClient

TARGET_MAC = "23:01:02:24:7C:EE"

async def interrogate():
    print(f"Scanning for {TARGET_MAC}...")
    device = await BleakScanner.find_device_by_address(TARGET_MAC, timeout=10.0)

    if not device:
        print("✖ Strip not found. Make sure it is plugged in and the phone app is CLOSED.")
        return

    print("✔ Device found! Bypassing security and establishing uplink...")
    try:
        async with BleakClient(device) as client:
            print("\n================ DEEP GATT BLUEPRINT ================\n")
            for service in client.services:
                print(f"[Service] {service.uuid}")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"  ├── [Channel] {char.uuid}")
                    print(f"  └── [Properties] {props}\n")
            print("=====================================================")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(interrogate())
