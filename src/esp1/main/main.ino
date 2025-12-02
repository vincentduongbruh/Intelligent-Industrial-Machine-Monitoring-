#include "MPU9250.h"
#include "SHT30.h"
#include "BluetoothHandler.h"

MPU9250 imu;
SHT30 sht;

BluetoothHandler btHandler(
    "ESP32_1", // Device name
    "8f3eec84-a3cd-4991-9f84-b6d6915e7382",  // Service UUID
    "488147e4-8512-4bca-b218-0b84f2f76853"   // Characteristic UUID
);

SensorPacket currentData;
float lastTemp = 0.0f;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22, 50000);

    imu.begin();
    sht.begin();

    btHandler.begin();
}

void loop() {
    int16_t ax, ay, az;
    imu.readAccel(ax, ay, az);

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