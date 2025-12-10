import asyncio
import struct
import math
from bleak import BleakClient, BleakScanner


SERVICE_UUID = "8f3eec84-a3cd-4991-9f84-b6d6915e7382"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

def callback_handler(sender, data):
    ax, ay, az, temp = struct.unpack('<ffff', data)
    print(f"Received -> Ax: {ax:.2f}, Ay: {ay:.2f}, Az: {az:.2f}, Temp: {temp:.2f}")

def direct_axis_current(i_a, i_b, i_c):
    i_d = (math.sqrt(2/3) * i_a) - (i_b / math.sqrt(6)) - (i_c / math.sqrt(6))
    return i_d
    
def quadrature_axis_current(i_a, i_b, i_c, theta):
    i_q = (i_b / math.sqrt(2)) - (i_c / math.sqrt(2))
    return i_q

def park_vector_modulus(i_d, i_q):
    PVM = math.sqrt((i_d ** 2) + (i_q ** 2))
    return PVM


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
