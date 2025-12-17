import asyncio
from bleak import BleakScanner, BleakClient, BleakError
import struct
import time
import numpy as np
from collections import deque

# Import fault detector for advanced Park's vector filtering
from faultdetector import MotorFaultDetector

DEVICE_NAME = "ESP32"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

# Global reference to GUI app (set by motor_gui.py)
gui_app = None
start_time = None

# Initialize fault detector
fault_detector = MotorFaultDetector(fs_target=3600, f0_target=60)

# Buffers for batch processing (store last N samples for filtering)
BUFFER_SIZE = 100  # Number of samples to keep for filtering
current_buffers = {
    'ia': deque(maxlen=BUFFER_SIZE),
    'ib': deque(maxlen=BUFFER_SIZE),
    'ic': deque(maxlen=BUFFER_SIZE),
}

def callback_handler(sender: int, data: bytearray):
    """
    BLE callback handler - receives data from ESP32.
    Computes Park's vector and applies advanced filtering.
    """
    global start_time, gui_app
    
    # Safety check: GUI still exists
    if gui_app is None:
        return
    
    if start_time is None:
        start_time = time.time()
    
    try:
        # Unpack sensor data
        ax, ay, az, temp, ia, ib, ic = struct.unpack("<7f", data[:28])

        print(
            f"ax={ax:.3f}, ay={ay:.3f}, az={az:.3f}, "
            f"temp={temp:.2f} C | "
            f"ia={ia:.3f}, ib={ib:.3f}, ic={ic:.3f}"
        )
        
        # Check if motor is running (phase currents should differ)
        if abs(ia - ib) < 0.001 and abs(ib - ic) < 0.001:
            print("⚠️  WARNING: All phase currents equal - motor may not be running!")
        
        # Add current data to buffers for batch filtering
        current_buffers['ia'].append(ia)
        current_buffers['ib'].append(ib)
        current_buffers['ic'].append(ic)
        
        # Compute raw Park's vector (single point, for immediate display)
        id_val, iq_val = fault_detector.compute_park_vector(
            np.array([ia]), 
            np.array([ib]), 
            np.array([ic])
        )
        id_val = float(id_val[0])
        iq_val = float(iq_val[0])
        
        # Compute filtered Park's vector using accumulated data
        if len(current_buffers['ia']) >= 10:  # Need at least 10 samples for filtering
            # Convert buffers to numpy arrays
            ia_array = np.array(current_buffers['ia'])
            ib_array = np.array(current_buffers['ib'])
            ic_array = np.array(current_buffers['ic'])
            
            try:
                # Apply full filtering pipeline
                # Estimate fundamental frequency (assuming 60Hz motor)
                f0_detected = 60.0
                fs_original = 100.0  # Approximate sample rate (adjust if needed)
                
                # Run the processing pipeline
                id_filtered_array, iq_filtered_array = fault_detector.process_pipeline(
                    ia_array, ib_array, ic_array, 
                    fs_original, f0_detected
                )
                
                # Use the most recent filtered value
                filtered_id = float(id_filtered_array[-1])
                filtered_iq = float(iq_filtered_array[-1])
                
            except Exception as e:
                # Fallback to simple EMA if advanced filtering fails
                if not hasattr(callback_handler, 'error_count'):
                    callback_handler.error_count = 0
                callback_handler.error_count += 1
                
                # Only print error occasionally to avoid spam
                if callback_handler.error_count % 100 == 1:
                    print(f"⚠️  Filtering error (#{callback_handler.error_count}): {e}")
                    print(f"   Using EMA fallback...")
                
                if not hasattr(callback_handler, 'filtered_id'):
                    callback_handler.filtered_id = id_val
                    callback_handler.filtered_iq = iq_val
                else:
                    alpha = 0.3
                    callback_handler.filtered_id = alpha * id_val + (1 - alpha) * callback_handler.filtered_id
                    callback_handler.filtered_iq = alpha * iq_val + (1 - alpha) * callback_handler.filtered_iq
                
                filtered_id = callback_handler.filtered_id
                filtered_iq = callback_handler.filtered_iq
        else:
            # Not enough data yet, use simple EMA
            if not hasattr(callback_handler, 'filtered_id'):
                callback_handler.filtered_id = id_val
                callback_handler.filtered_iq = iq_val
            else:
                alpha = 0.3
                callback_handler.filtered_id = alpha * id_val + (1 - alpha) * callback_handler.filtered_id
                callback_handler.filtered_iq = alpha * iq_val + (1 - alpha) * callback_handler.filtered_iq
            
            filtered_id = callback_handler.filtered_id
            filtered_iq = callback_handler.filtered_iq
        
        # Send data to GUI if available (with safety checks)
        if gui_app is not None:
            timestamp = time.time() - start_time
            try:
                gui_app.add_data_point(
                    timestamp, ax, ay, az, temp, ia, ib, ic,
                    id_val, iq_val, 
                    filtered_id, 
                    filtered_iq
                )
            except Exception as e:
                print(f"❌ Error updating GUI: {e}")
                # GUI might be destroyed, stop trying to send data
                gui_app = None
                
    except Exception as e:
        print(f"❌ Critical error in callback: {e}")
        import traceback
        traceback.print_exc()

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