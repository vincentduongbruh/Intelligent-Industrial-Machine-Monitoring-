import asyncio
import struct
import time
import re
import threading
from collections import deque

import numpy as np
import serial
from bleak import BleakScanner, BleakClient, BleakError
import pandas as pd
import os

from Fault_Detector import MotorFaultDetector

DEVICE_NAME = "ESP32_1"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

# ---------- Serial ----------
SERIAL_PORT = "/dev/tty.usbserial-D306EM4X"
BAUDRATE = 115200

ser = None

LINE_REGEX = re.compile(
    r"ia:([-+]?\d*\.?\d+)\s+"
    r"ib:([-+]?\d*\.?\d+)\s+"
    r"ic:([-+]?\d*\.?\d+)"
)

def open_serial(port: str, baud: int) -> serial.Serial:
    ser = serial.Serial(port, baud, timeout=0.1)  # short timeout
    time.sleep(1.5)
    return ser

def parse_line(line: str):
    m = LINE_REGEX.search(line)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))

# Latest serial values updated by background thread
latest_currents = {"ia": None, "ib": None, "ic": None, "t": None}

def serial_reader_loop(ser: serial.Serial, stop_event: threading.Event):
    """Continuously read serial lines and update latest_currents."""
    while not stop_event.is_set():
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            vals = parse_line(line)
            if vals is None:
                continue
            ia, ib, ic = vals
            latest_currents["ia"] = ia
            latest_currents["ib"] = ib
            latest_currents["ic"] = ic
            latest_currents["t"] = time.time()
        except Exception:
            # swallow serial parse errors
            continue

# ---------- GUI global (set by motor_gui.py) ----------
class GUIRegistry:
    def __init__(self):
        self.app = None

gui_app = GUIRegistry()
start_time = None

def run_data_acquisition():
    """
    Entry point used by motor_gui.py.
    Runs the BLE + serial acquisition loop in the calling thread.
    """
    asyncio.run(main())

# ---------- Fault detector ----------
fault_detector = MotorFaultDetector(fs_target=3600, f0_target=60)

BUFFER_SIZE = 200
buf = {
    "ia": deque(maxlen=BUFFER_SIZE),
    "ib": deque(maxlen=BUFFER_SIZE),
    "ic": deque(maxlen=BUFFER_SIZE),
}

def callback_handler(sender: int, data: bytearray):
    """BLE notification callback."""
    global start_time, gui_app

    if start_time is None:
        start_time = time.time()

    t = time.time() - start_time

    # 1) Confirm we are receiving notifications
    print(f"BLE notify: {len(data)} bytes")

    # 2) Decode BLE payload safely (don’t crash)
    ax = ay = az = temp = 0.0
    try:
        # Common case: 4 floats = 16 bytes (ax,ay,az,temp)
        if len(data) >= 16:
            ax, ay, az, temp = struct.unpack("<4f", data[:16])
    except Exception as e:
        print(f"⚠️ BLE unpack error: {e}")

    # 3) Get latest serial currents without blocking BLE
    ia = latest_currents["ia"]
    ib = latest_currents["ib"]
    ic = latest_currents["ic"]

    data = {"time": t, "ia": ia, "ib": ib, "ic": ic}

    df = pd.DataFrame(data)

    output_path = "test.csv"
    df.to_csv(output_path, mode='a', header=not os.path.exists(output_path))

    if ia is None or ib is None or ic is None:
        # Serial not ready yet; still show IMU
        print(f"IMU only: ax={ax:.3f} ay={ay:.3f} az={az:.3f} temp={temp:.2f}")
        return

    print(
        f"ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, temp={temp:.2f} | "
        f"ia={ia:.3f}, ib={ib:.3f}, ic={ic:.3f}"
    )

    # 4) DC removal (critical for Park)
    buf["ia"].append(ia)
    buf["ib"].append(ib)
    buf["ic"].append(ic)

    ia_ac = ia - float(np.mean(buf["ia"]))
    ib_ac = ib - float(np.mean(buf["ib"]))
    ic_ac = ic - float(np.mean(buf["ic"]))

    # 5) Park vector (and scaled trajectory) on DC-removed signals.
    # We intentionally do NOT run ODT or filtering here.
    #
    # Compute Park's vector for the entire buffered window, then scale the
    # trajectory, and take the most recent point for plotting.
    ia_ac_win = np.array(buf["ia"], dtype=float) - float(np.mean(buf["ia"]))
    ib_ac_win = np.array(buf["ib"], dtype=float) - float(np.mean(buf["ib"]))
    ic_ac_win = np.array(buf["ic"], dtype=float) - float(np.mean(buf["ic"]))

    id_win, iq_win = fault_detector.compute_park_vector(ia_ac_win, ib_ac_win, ic_ac_win)
    id_scaled_win, iq_scaled_win = fault_detector.scale_trajectory(id_win, iq_win)

    # Latest scaled point (used by GUI for the "Filtered" Park's vector plot)
    filtered_id = float(id_scaled_win[-1])
    filtered_iq = float(iq_scaled_win[-1])

    # Also expose the latest unscaled point (useful for debugging / optional plots)
    id_val = float(id_win[-1])
    iq_val = float(iq_win[-1])

    # 6) Update GUI if present
    if gui_app is not None:
        try:
            gui_app.add_data_point(
                t, ax, ay, az, temp, ia, ib, ic,
                id_val, iq_val,
                filtered_id, filtered_iq
            )
        except Exception as e:
            print(f"❌ GUI update error: {e}")
            gui_app = None

async def find_device():
    print("Scanning for ESP32...")
    devices = await BleakScanner.discover(timeout=5.0)
    for d in devices:
        if d.name and DEVICE_NAME in d.name:
            print(f"Found {d.name} [{d.address}]")
            return d
    raise RuntimeError("ESP32 not found")

async def connect_and_notify(device):
    async with BleakClient(device) as client:
        print("Connecting...")
        await client.connect()
        if not client.is_connected:
            raise BleakError("BLE connection unstable")

        print("Connected.")
        await asyncio.sleep(0.3)

        print("Starting notifications...")
        await client.start_notify(CHAR_UUID, callback_handler)

        print("Listening for notifications (Ctrl+C to exit)")
        while True:
            await asyncio.sleep(1)

async def main():
    device = await find_device()
    await connect_and_notify(device)

if __name__ == "__main__":
    ser = open_serial(SERIAL_PORT, BAUDRATE)

    stop_event = threading.Event()
    t_serial = threading.Thread(target=serial_reader_loop, args=(ser, stop_event), daemon=True)
    t_serial.start()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_event.set()
        try:
            ser.close()
        except Exception:
            pass
