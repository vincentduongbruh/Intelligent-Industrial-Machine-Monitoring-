import asyncio
import struct
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "12345678" # placeholder for now, probably need to create UUID based on MAC address
CHAR_UUID = "87654321" # placeholder for now, probably need to create UUID based on MAC address

def callback_handler(sender, data):
    ax, ay, az, temp = struct.unpack('<ffff', data)
    print(f"Received -> Ax: {ax:.2f}, Ay: {ay:.2f}, Az: {az:.2f}, Temp: {temp:.2f}")

async def main():
    print("Scanning for ESP32")
    device = await BleakScanner.find_device_by_name("ESP2_001") # placeholder name for now

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