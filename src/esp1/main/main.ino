#include "MPU6500.h"
#include "SHT30.h"
#include "BluetoothHandler.h"
#include "ESPNowReceiver.h"
#include "ThreePhaseCurrentPacket.h"

MPU6500 imu(0x69, Wire); 
SHT30 sht1;
SHT30 sht2;

BluetoothHandler btHandler(
    "ESP32_1", // Device name
    "8f3eec84-a3cd-4991-9f84-b6d6915e7382",  // Service UUID
    "488147e4-8512-4bca-b218-0b84f2f76853"   // Characteristic UUID
);

SensorPacket packet;
ESPNowReceiver esp_receiver;

float lastTemp1 = 0.0f;
float lastTemp2 = 0.0f;

void setup() {
    Serial.begin(115200);

    Wire.begin(21, 22);
    Wire.setClock(100000);
    Wire1.begin(27, 33);
    Wire1.setClock(100000);

    imu.begin(Wire);
    imu.calibrate(500);

    sht1.begin(Wire);
    sht1.calibrate(20, 23.5f);
    sht2.begin(Wire1);
    sht2.calibrate(20, 23.5f);

    if (!esp_receiver.begin()) {
        Serial.println("ESP-Now receiver: Fail");
        delay(100);
    }
    Serial.println("ESP-NOW receiver: Ready");

    btHandler.begin();
}

void loop() {
    float ax, ay, az, temp, ia, ib, ic, t1, t2;
    
    imu.readAccelG(ax, ay, az);
    sht1.readCelsius(t1);
    sht2.readCelsius(t2);

    temp = 0.5f * (t1 + t2);

    if (esp_receiver.hasNewPacket()) {
        ThreePhaseCurrentPacket pkt = esp_receiver.getLatest();
        ia = pkt.ia;
        ib = pkt.ib;
        ic = pkt.ic;
    }

    packet.ax = static_cast<float>(ax);
    packet.ay = static_cast<float>(ay);
    packet.az = static_cast<float>(az);
    packet.temp = static_cast<float>(temp);
    packet.ia = static_cast<float>(ia);
    packet.ib = static_cast<float>(ib);
    packet.ic = static_cast<float>(ic);

    Serial.printf("ax:%f ay:%f az:%f temp:%f ia:%f ib:%f ic:%f\n",
                  ax, ay, az, temp, ia, ib, ic);
    
    btHandler.notifySensorData(packet);
    delay(1);
}