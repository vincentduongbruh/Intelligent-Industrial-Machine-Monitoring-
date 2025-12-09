#ifndef BLUETOOTH_HANDLER_H
#define BLUETOOTH_HANDLER_H

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

/**
 * @brief Struct representing one BLE transmission packet of sensor data.
 */
struct SensorPacket {
    float ax;
    float ay;
    float az;
    float temp;

    float ia;
    float ib;
    float ic;
};

/**
 * @brief Handles BLE setup, connection tracking, and transmitting sensor data.
 *
 * Usage:
 *  1. Create instance with name + UUIDs.
 *  2. Call begin() in setup().
 *  3. Call notifySensorData() in loop().
 */
class BluetoothHandler {
public:
    /**
     * @param deviceName         Name of the BLE device.
     * @param serviceUUID        BLE service UUID.
     * @param characteristicUUID BLE characteristic UUID.
     */
    BluetoothHandler(const char* deviceName,
                     const char* serviceUUID,
                     const char* characteristicUUID);

    /**
     * @brief Initializes BLE stack, advertising, and services.
     */
    void begin();

    /**
     * @brief Sends a binary notification packet if a device is connected.
     * @param data Struct containing sensor values.
     */
    void notifySensorData(const SensorPacket& data);

    /**
     * @return True if a BLE central is connected.
     */
    bool isDeviceConnected() const;

private:
    BLEServer* pServer;
    BLECharacteristic* pCharacteristic;
    bool deviceConnected;

    const char* deviceName;
    const char* serviceUUID;
    const char* characteristicUUID;
};

#endif
