#include "MPU6500.h"
#include "SHT30.h"
// #include "BluetoothHandler.h"
// Use core-provided Wire (21/22) only.

MPU6500 imu1(0x69, Wire);  // board on this bus reports as 0x69
SHT30 sht;

// BluetoothHandler btHandler(
//     "ESP32_1", // Device name
//     "8f3eec84-a3cd-4991-9f84-b6d6915e7382",  // Service UUID
//     "488147e4-8512-4bca-b218-0b84f2f76853"   // Characteristic UUID
// );

// SensorPacket currentData;
float lastTemp = 0.0f;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);
    Wire.setClock(100000);

    if (!imu1.begin(Wire, 21, 22)) {
        Serial.println("IMU1 init failed (0x69)");
    } else {
        imu1.calibrate(500);
    }

    sht.begin(Wire);
    sht.calibrate(20, 23.5f);

    // btHandler.begin();
}

void loop() {
    float ax1, ay1, az1;

    bool ok1 = imu1.readAccelG(ax1, ay1, az1);

    
    float temp;
    if (sht.readCelsius(temp)) {
        lastTemp = temp;
    }

    Serial.print("ax1:"); Serial.print(ax1);
    Serial.print(" ay1:"); Serial.print(ay1);
    Serial.print(" az1:"); Serial.print(az1);
    Serial.print(" temp:"); Serial.println(lastTemp);

    // btHandler.notifySensorData(currentData);

    delay(100);
}
