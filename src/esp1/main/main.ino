#include "MPU6500.h"
#include "SHT30.h"
// #include "BluetoothHandler.h"
// Use core-provided Wire (21/22) for IMU + first SHT30, Wire1 (27/33) for second SHT30.

MPU6500 imu1(0x69, Wire);  // board on this bus reports as 0x69
SHT30 sht1;
SHT30 sht2;

// BluetoothHandler btHandler(
//     "ESP32_1", // Device name
//     "8f3eec84-a3cd-4991-9f84-b6d6915e7382",  // Service UUID
//     "488147e4-8512-4bca-b218-0b84f2f76853"   // Characteristic UUID
// );

// SensorPacket currentData;
float lastTemp1 = 0.0f;
float lastTemp2 = 0.0f;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);
    Wire.setClock(100000);
    Wire1.begin(27, 33);
    Wire1.setClock(100000);

    if (!imu1.begin(Wire, 21, 22)) {
        Serial.println("IMU1 init failed (0x69)");
    } else {
        imu1.calibrate(500);
    }

    sht1.begin(Wire);
    sht1.calibrate(20, 23.5f);
    sht2.begin(Wire1);
    sht2.calibrate(20, 23.5f);

    // btHandler.begin();
}

void loop() {
    float ax1, ay1, az1;

    bool ok1 = imu1.readAccelG(ax1, ay1, az1);

    
    float t1, t2;
    if (sht1.readCelsius(t1)) {
        lastTemp1 = t1;
    }
    if (sht2.readCelsius(t2)) {
        lastTemp2 = t2;
    }

    Serial.print("ax1:"); Serial.print(ax1);
    Serial.print(" ay1:"); Serial.print(ay1);
    Serial.print(" az1:"); Serial.print(az1);
    Serial.print(" t1:"); Serial.print(lastTemp1);
    Serial.print(" t2:"); Serial.println(lastTemp2);

    // btHandler.notifySensorData(currentData);

    delay(100);
}
