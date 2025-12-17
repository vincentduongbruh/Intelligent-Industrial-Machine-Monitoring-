#!/usr/bin/env python3
"""
Motor Diagnostics Tool
======================
This script helps diagnose motor and data streaming issues.

Run this to check:
1. Are the phase currents actually varying? (Motor running?)
2. Is Park's vector being computed correctly?
3. Is data flowing continuously?
"""

import asyncio
from bleak import BleakScanner, BleakClient
import struct
import numpy as np
import time
from collections import deque

DEVICE_NAME = "ESP32"
CHAR_UUID = "488147e4-8512-4bca-b218-0b84f2f76853"

# Statistics tracking
data_count = 0
start_time = None
current_history = deque(maxlen=100)

def compute_park_vector(ia, ib, ic):
    """Compute Park's vector"""
    id_val = (np.sqrt(2/3) * ia) - (ib / np.sqrt(6)) - (ic / np.sqrt(6))
    iq_val = (ib / np.sqrt(2)) - (ic / np.sqrt(2))
    return id_val, iq_val

def analyze_currents(history):
    """Analyze current statistics"""
    if len(history) < 10:
        return None
    
    ia_vals = [h['ia'] for h in history]
    ib_vals = [h['ib'] for h in history]
    ic_vals = [h['ic'] for h in history]
    
    # Check variance
    ia_std = np.std(ia_vals)
    ib_std = np.std(ib_vals)
    ic_std = np.std(ic_vals)
    
    # Check if all are equal
    all_equal = all(abs(ia_vals[i] - ib_vals[i]) < 0.001 and 
                   abs(ib_vals[i] - ic_vals[i]) < 0.001 
                   for i in range(len(ia_vals)))
    
    return {
        'ia_mean': np.mean(ia_vals),
        'ib_mean': np.mean(ib_vals),
        'ic_mean': np.mean(ic_vals),
        'ia_std': ia_std,
        'ib_std': ib_std,
        'ic_std': ic_std,
        'all_equal': all_equal,
        'varying': ia_std > 0.01 or ib_std > 0.01 or ic_std > 0.01
    }

def callback(sender: int, data: bytearray):
    """BLE callback for diagnostics"""
    global data_count, start_time
    
    if start_time is None:
        start_time = time.time()
    
    data_count += 1
    ax, ay, az, temp, ia, ib, ic = struct.unpack("<7f", data[:28])
    
    # Store in history
    current_history.append({
        'ia': ia,
        'ib': ib,
        'ic': ic,
        'time': time.time()
    })
    
    # Compute Park's vector
    id_val, iq_val = compute_park_vector(ia, ib, ic)
    
    # Print every 20 samples
    if data_count % 20 == 0:
        elapsed = time.time() - start_time
        rate = data_count / elapsed
        
        print(f"\n{'='*70}")
        print(f"📊 DIAGNOSTIC REPORT (Sample #{data_count}, Rate: {rate:.1f} Hz)")
        print(f"{'='*70}")
        
        # Current values
        print(f"\n🔌 Phase Currents:")
        print(f"   ia = {ia:8.3f} A")
        print(f"   ib = {ib:8.3f} A")
        print(f"   ic = {ic:8.3f} A")
        
        # Check if equal
        if abs(ia - ib) < 0.001 and abs(ib - ic) < 0.001:
            print(f"   ⚠️  WARNING: All currents are equal!")
            print(f"   ⚠️  Motor may NOT be running!")
        else:
            print(f"   ✅ Currents differ (motor likely running)")
        
        # Park's vector
        print(f"\n🔄 Park's Vector:")
        print(f"   id = {id_val:8.3f}")
        print(f"   iq = {iq_val:8.3f}")
        print(f"   |PV| = {np.sqrt(id_val**2 + iq_val**2):8.3f}")
        
        # Statistics
        stats = analyze_currents(current_history)
        if stats:
            print(f"\n📈 Statistics (last {len(current_history)} samples):")
            print(f"   Mean: ia={stats['ia_mean']:.3f}, ib={stats['ib_mean']:.3f}, ic={stats['ic_mean']:.3f}")
            print(f"   StdDev: ia={stats['ia_std']:.3f}, ib={stats['ib_std']:.3f}, ic={stats['ic_std']:.3f}")
            
            if stats['all_equal']:
                print(f"   ❌ All currents ALWAYS equal - motor NOT running!")
            elif not stats['varying']:
                print(f"   ⚠️  Very low variation - motor may be stalled")
            else:
                print(f"   ✅ Currents varying - motor IS running")
        
        # Sensor data
        print(f"\n📡 Sensor Data:")
        print(f"   Accel: ({ax:.3f}, {ay:.3f}, {az:.3f}) g")
        print(f"   Temp: {temp:.2f} °C")
        
        print(f"\n{'='*70}\n")

async def main():
    """Main diagnostic routine"""
    print("🔍 Motor Health Diagnostic Tool")
    print("=" * 70)
    print("Scanning for ESP32...")
    
    devices = await BleakScanner.discover(timeout=5.0)
    device = None
    
    for d in devices:
        if d.name and DEVICE_NAME in d.name:
            print(f"✅ Found {d.name} [{d.address}]")
            device = d
            break
    
    if not device:
        print("❌ ESP32 not found!")
        return
    
    print(f"\n📡 Connecting...")
    client = BleakClient(device)
    
    try:
        await client.connect()
        print(f"✅ Connected!")
        
        print(f"\n🎧 Starting notifications...")
        await client.start_notify(CHAR_UUID, callback)
        
        print(f"✅ Receiving data...")
        print(f"\n{'='*70}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")
        
        # Run indefinitely
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    finally:
        if client.is_connected:
            print("📡 Disconnecting...")
            await client.disconnect()
        print("✅ Done!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")

