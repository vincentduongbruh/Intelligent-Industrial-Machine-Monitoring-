# Intelligent Industrial Motor Monitoring

**Real-Time Fault Detection Using Current, Vibration, and Temperature Sensing**

This project presents an intelligent motor health monitoring system designed to detect early-stage electrical and mechanical faults in industrial motors. The system continuously measures **3-phase current**, **vibration**, and **temperature**, analyzes these signals in real time, and visualizes motor health indicators through a graphical user interface (GUI).

The work was conducted in collaboration with **NASA Ames Research Center** and builds upon prior research on generalized fault detection using the **Filtered Park’s Vector Approach (FPVA)**. While traditional fault-detection methods often remain confined to offline analysis or simulation, this project focuses on a **deployable, sensor-driven monitoring platform** suitable for real-world industrial environments.

---

## Motivation

Induction motors account for approximately **90% of electrically driven industrial machinery**, including:
- Manufacturing robots
- CNC machines
- Conveyors
- HVAC systems
- Aerospace actuators and pumps

Despite their ubiquity, motor faults such as **bearing wear**, **shaft misalignment**, **gear damage**, and **electrical phase imbalance** often go undetected until catastrophic failure. These faults manifest as changes in:
- Current signatures
- Vibration spectra
- Operating temperature

This project bridges the gap between **fault-detection algorithms** and **physical monitoring infrastructure**, enabling early detection and improved system reliability.

---

## System Overview

The system is composed of three primary subsystems:

1. **Temperature & Vibration Sensing PCB**
2. **3-Phase Current Sensing PCB**
3. **Data Processing Server and GUI**

Sensor data is transmitted to the processing server via a combination of **USB** and **Bluetooth Low Energy (BLE)** links.

> Note: Due to limited access to industrial induction motors, testing was performed using **ESC-driven brushless motors**. While this changes the expected current waveforms, the monitoring approach remains applicable to industrial motors and VFD-driven systems.

---

## Hardware Architecture

### Sensors
- **Temperature**: Dual SHT30 temperature sensors mounted near motor windings
- **Vibration**: Dual MPU6500 IMUs measuring linear acceleration
- **Current**: Non-invasive current transformer measuring 3-phase current

### Electronics
- **ESP32 Microcontrollers**
  - One ESP32 for temperature & vibration sensing
  - One ESP32 for high-speed current acquisition

### Physical Testing Rig
- Custom **3D-printed rig** for:
  - Mechanical stability
  - Consistent sensor placement
  - Repeatable experiments

---

## Embedded Software

### Sensor Drivers
- Custom I2C drivers for temperature and IMU sensors
- Register-level configuration based on manufacturer datasheets
- Real-time data acquisition

### Sensor Calibration
- **Affine sensor model** used to correct bias and sensitivity
- Gravity-based calibration for IMUs
- Known-reference calibration for temperature sensors

### Signal Conditioning
- **Exponential Moving Average (EMA) low-pass filtering**
  - Reduces high-frequency noise
  - Lightweight and suitable for real-time embedded systems

### Communication
- **BLE (1 kHz)**: Temperature and vibration data
- **USB (10 kHz)**: Phase-accurate 3-phase current data
  - Chosen to avoid wireless latency and phase misalignment

---

## Data Processing

### Park’s Vector Approach
- Converts 3-phase currents into the rotating **d–q reference frame**
- Enables fault detection through geometric patterns in the id–iq plane

Under ideal conditions:
- Healthy motor → circular Park’s Vector trajectory
- Faulted motor → distorted or asymmetric trajectory

For ESC-driven motors:
- Healthy motor → six-pointed star pattern
- Phase fault → collapsed or triangular pattern

The system adapts the interpretation of Park’s Vector results based on the motor drive method.

---

## Graphical User Interface (GUI)

The GUI provides real-time visualization of:

1. **3-Phase Current Waveforms**
2. **Filtered Park’s Vector Plot**
3. **Vibration (Time + Frequency Domain)**
   - RMS vibration
   - FFT-based frequency analysis
4. **Temperature Monitoring**

Threshold-based alerts notify the user of potential electrical or mechanical faults.

---

## Testing and Validation

Fault conditions were intentionally introduced to validate system behavior:
- **Phase imbalance** via diode-induced waveform distortion
- **Mechanical vibration** using off-center rotating loads
- **Thermal stress** via high-throttle motor operation

The system consistently distinguished healthy and faulted operating states across current, vibration, and temperature modalities.

---

## Challenges and Limitations

- **Wireless latency** caused phase misalignment (resolved by USB current transmission)
- **ESC-driven motors** produce non-sinusoidal waveforms
- **High sampling rates** (≥10 kHz) required for accurate current analysis
- Limited access to industrial induction motors for final validation

---

## Future Work

- Deploy and validate system on industrial induction motors
- Apply machine learning for **multi-class fault classification**
- Extract higher-level features from current, vibration, and thermal data
- Improve fault localization and severity estimation

---

## Team

- **Nick Bui**
- **Mohamed Homsi**
- **Aashrith Beesabathuni**
- **Vincent Duong**
- **Carter Chen**

---

## Acknowledgements

We thank:
- Professor Dutta
- Paul De La Sayette
- Matteo Guarrera
- Dr. Rodney Martin
- Isak Bolin (NASA Ames Research Center)

for their guidance and foundational research support.

---

## References

- Bolin, I. *Generalized Fault Detection of Broken Rotor Bars in Induction Motors*, Uppsala University, 2024.

---

## To run GUI on Raspberry Pi or Laptop: 
<pre>cd src/raspberry_pi </pre>
<pre>python -m venv env</pre>
<pre>source env/bin/activate</pre>
<pre>pip install -r requirements.txt</pre>
<pre>python gui.py</pre>

## Troubleshooting FAQ:
#### BLE Connection Failing: 
- Ctrl+C to terminate
- Reset ESP 1
- <pre>python gui.py</pre>
#### CT Data Missing:
- Ctrl+C to terminate
- Reset ESP2
- <pre>python gui.py</pre>
