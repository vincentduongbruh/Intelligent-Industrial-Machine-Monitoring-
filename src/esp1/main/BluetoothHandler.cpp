#include "BluetoothHandler.h"
#include <Arduino.h>

class MyServerCallbacks : public BLEServerCallbacks {
public:
    explicit MyServerCallbacks(bool* connectionFlag)
        : deviceConnected(connectionFlag) {}

    void onConnect(BLEServer*) override {
        *deviceConnected = true;
        Serial.println("RPi Connected!");
    }

    void onDisconnect(BLEServer*) override {
        *deviceConnected = false;
        Serial.println("RPi Disconnected. Restarting advertising...");
        BLEDevice::startAdvertising();
    }

private:
    bool* deviceConnected;
};

BluetoothHandler::BluetoothHandler(const char* deviceName,
                                   const char* serviceUUID,
                                   const char* characteristicUUID)
    : pServer(nullptr),
      pCharacteristic(nullptr),
      serverCallbacks(nullptr),
      deviceConnected(false),
      deviceName(deviceName),
      serviceUUID(serviceUUID),
      characteristicUUID(characteristicUUID)
{}

void BluetoothHandler::begin() {
    BLEDevice::init(deviceName);

    pServer = BLEDevice::createServer();

    serverCallbacks = new MyServerCallbacks(&deviceConnected);
    pServer->setCallbacks(serverCallbacks);

    BLEService* pService = pServer->createService(serviceUUID);

    pCharacteristic = pService->createCharacteristic(
        characteristicUUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_NOTIFY
    );

    // Required for notifications
    pCharacteristic->addDescriptor(new BLE2902());

    // Initialize readable value
    SensorPacket zeroPacket{};
    pCharacteristic->setValue((uint8_t*)&zeroPacket, sizeof(SensorPacket));

    pService->start();

    BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(serviceUUID);
    pAdvertising->setScanResponse(false);
    pAdvertising->setMinPreferred(0x00);

    BLEDevice::startAdvertising();
    Serial.println("Waiting for RPi to connect...");
}

void BluetoothHandler::notifySensorData(const SensorPacket& data) {
    if (!deviceConnected || pCharacteristic == nullptr) return;

    pCharacteristic->setValue((uint8_t*)&data, sizeof(SensorPacket));
    pCharacteristic->notify();
}

bool BluetoothHandler::isDeviceConnected() const {
    return deviceConnected;
}