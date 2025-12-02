import asyncio
import struct
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "8f3eec84-a3cd-4991-9f84-b6d6915e7382"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

def callback_handler(sender, data):
    ax, ay, az, temp = struct.unpack('<ffff', data)
    print(f"Received -> Ax: {ax:.2f}, Ay: {ay:.2f}, Az: {az:.2f}, Temp: {temp:.2f}")

async def main():
    print("Scanning for ESP32")
    device = await BleakScanner.find_device_by_name("ESP32_1")

    if not device:
        print("Couldn't find ESP32")
        return
    
    else:
        async with BleakClient(device) as client:
            print("Connected to device")

        await client.start_notify(CHAR_UUID, callback_handler)
        await asyncio.sleep(100)
        await client.stop_notify(CHAR_UUID)

if __name__ == "__main__":
    asyncio.run(main())