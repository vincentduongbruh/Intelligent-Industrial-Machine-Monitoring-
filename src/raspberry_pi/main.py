import asyncio
from bleak import BleakScanner, BleakClient, BleakError
import struct
import math
import time

DEVICE_NAME = "ESP32"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

# EMA filter state for Park's vector
ema_id = None
ema_iq = None
EMA_ALPHA = 0.1  # Smoothing factor

start_time = None
gui_app = None  # Will be set by motor_gui when integration is active

def direct_axis_current(i_a, i_b, i_c):
    i_d = (math.sqrt(2/3) * i_a) - (i_b / math.sqrt(6)) - (i_c / math.sqrt(6))
    return i_d
    
def quadrature_axis_current(i_a, i_b, i_c):
    i_q = (i_b / math.sqrt(2)) - (i_c / math.sqrt(2))
    return i_q

def park_vector_modulus(i_d, i_q):
    PVM = math.sqrt((i_d ** 2) + (i_q ** 2))
    return PVM

def callback_handler(sender: int, data: bytearray):
    global start_time, ema_id, ema_iq
    
    if start_time is None:
        start_time = time.time()
    
    ax, ay, az, temp, ia, ib, ic = struct.unpack("<7f", data[:28])
    
    current_time = time.time() - start_time

    print(
        f"ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, "
        f"temp={temp:.2f} C | "
        f"ia={ia:.3f}, ib={ib:.3f}, ic={ic:.3f}"
    )
    
    # Calculate Park's vector components
    i_d = direct_axis_current(ia, ib, ic)
    i_q = quadrature_axis_current(ia, ib, ic)
    
    # Apply EMA filter for filtered Park's vector
    if ema_id is None:
        ema_id = i_d
        ema_iq = i_q
    else:
        ema_id = EMA_ALPHA * i_d + (1 - EMA_ALPHA) * ema_id
        ema_iq = EMA_ALPHA * i_q + (1 - EMA_ALPHA) * ema_iq
    
    # Send data directly to GUI
    if gui_app is not None:
        gui_app.add_data_point(
            timestamp=current_time,
            ax=ax, ay=ay, az=az,
            temp=temp,
            ia=ia, ib=ib, ic=ic,
            id=i_d, iq=i_q,
            filtered_id=ema_id,
            filtered_iq=ema_iq
        )

async def find_device():
    print("Scanning for ESP32")
    devices = await BleakScanner.discover(timeout=5.0)

    for d in devices:
        if d.name and DEVICE_NAME in d.name:
            print(f"Found {d.name} [{d.address}]")
            return d

    raise RuntimeError("ESP32 not found")

async def connect_and_notify(device):
    client = BleakClient(device)

    try:
        print("Connecting to device")
        await client.connect()

        for _ in range(10):
            if client.is_connected:
                break
            await asyncio.sleep(0.2)

        if not client.is_connected:
            raise BleakError("BLE connection unstable")

        print("Connected to device")

        await asyncio.sleep(0.5)

        print("Starting notifications")
        await client.start_notify(CHAR_UUID, callback_handler)

        print("Listening for notifications (Ctrl+C to exit)")
        while True:
            await asyncio.sleep(1)

    finally:
        if client.is_connected:
            print("Disconnecting")
            await client.disconnect()

async def main():
    device = await find_device()

    for attempt in range(2):
        try:
            await connect_and_notify(device)
        except BleakError as e:
            print(f"BLE error (attempt {attempt + 1}): {e}")
            await asyncio.sleep(1.0)
        else:
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")