#include "MPU9250.h"
#include "SHT30.h"
#include "BluetoothHandler.h"

MPU9250 imu1(0x68);
MPU9250 imu2(0x69);
SHT30 sht;

BluetoothHandler btHandler(
    "ESP32_1", // Device name
    "8f3eec84-a3cd-4991-9f84-b6d6915e7382",  // Service UUID
    "488147e4-8512-4bca-b218-0b84f2f76853"   // Characteristic UUID
);

SensorPacket currentData;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22, 50000);

    imu1.begin();
    imu1.calibrate(1000);

    imu2.begin();
    imu2.calibrate(1000);ß

    sht.begin();

    btHandler.begin();
}

void loop() {
    float ax1, ay1, az1;
    float ax2, ay2, az2;
    float lastTemp = 0.0f;

    imu1.readAccelG(ax1, ay1, az1);
    imu2.readAccelG(ax2, ay2, az2);

    float ax = 0.5 * (ax1 + ax2);
    float ay = 0.5 * (ay1 + ay2);
    float az = 0.5 * (az1 + az2);

    float temp;
    bool ok = sht.read(temp);
    if (ok) {
        lastTemp = temp;
    }

    currentData.ax = static_cast<float>(ax);
    currentData.ay = static_cast<float>(ay);
    currentData.az = static_cast<float>(az);
    currentData.temp = lastTemp;

    Serial.printf("ax:%d ay:%d az:%d temp:%f\n",
                  ax, ay, az, lastTemp);

    btHandler.notifySensorData(currentData);

    delay(100);
}