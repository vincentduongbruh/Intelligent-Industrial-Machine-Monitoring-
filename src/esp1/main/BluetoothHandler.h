#ifndef BLUETOOTH_HANDLER_H
#define BLUETOOTH_HANDLER_H

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

/**
 * @brief Struct representing one BLE transmission packet of sensor data.
 */
struct __attribute__((packed)) SensorPacket {
    float ax;
    float ay;
    float az;
    float temp;
    float ia;
    float ib;
    float ic;
};

class BluetoothHandler {
public:
    BluetoothHandler(const char* deviceName,
                     const char* serviceUUID,
                     const char* characteristicUUID);

    void begin();
    void notifySensorData(const SensorPacket& data);
    bool isDeviceConnected() const;

private:
    BLEServer* pServer;
    BLECharacteristic* pCharacteristic;
    BLEServerCallbacks* serverCallbacks;

    bool deviceConnected;

    const char* deviceName;
    const char* serviceUUID;
    const char* characteristicUUID;
};

#endif