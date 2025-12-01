#include "MPU9250.h"
#include "SHT30.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

MPU9250 imu;
SHT30 sht;

#define SERVICE_UUID        "12345678" // placeholder for now, probably need to create UUID based on MAC address
#define CHAR_UUID "87654321" // placeholder for now, probably need to create UUID based on MAC address

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

struct SensorPacket {
    float ax;
    float ay;
    float az;
    float temp;
};
SensorPacket currentData;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("RPi Connected!");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("RPi Disconnected. Restarting advertising...");
      BLEDevice::startAdvertising();
    }
};

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22, 50000); // Standard I2C pins for ESP32
  imu.begin();
  sht.begin();

  BLEDevice::init("ESP32_001"); // Name of the device, placeholder for now
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHAR_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0); 
  BLEDevice::startAdvertising();
  Serial.println("Waiting for RPi to connect...");
}

void loop() {
  float ax, ay, az;
  imu.readAccel(ax, ay, az);

  float temp;
  if (sht.read(temp)) {
    currentData.temp = temp;
  }
  
  currentData.ax = ax;
  currentData.ay = ay;
  currentData.az = az;

  Serial.printf("X:%.2f Y:%.2f Z:%.2f T:%.2f\n", 
                currentData.ax, currentData.ay, currentData.az, currentData.temp);

  if (deviceConnected) {
      // Cast the struct to a byte array and send it
      pCharacteristic->setValue((uint8_t*)&currentData, sizeof(SensorPacket));
      pCharacteristic->notify();
  }
  
  delay(100); 
}