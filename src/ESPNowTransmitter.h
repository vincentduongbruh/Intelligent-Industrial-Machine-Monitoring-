#ifndef ESPNOW_TRANSMITTER_H
#define ESPNOW_TRANSMITTER_H

#include <WiFi.h>
#include <esp_now.h>
#include "ThreePhaseCurrentPacket.h"

/**
 * @brief ESP-NOW transmitter for sending three-phase current data.
 */
class ESPNowTransmitter {
public:
    /**
     * @brief Construct a transmitter targeting a specific peer.
     * @param peerMac MAC address of the receiver ESP32.
     */
    ESPNowTransmitter(const uint8_t peerMac[6]);

    /**
     * @brief Initialize WiFi/ESPNOW and register peer.
     * @return true if initialization succeeded.
     */
    bool begin();

    /**
     * @brief Send a 3-phase current packet.
     * @return true if send succeeded.
     */
    bool send(const ThreePhaseCurrentPacket& packet);

private:
    uint8_t _peerMac[6];
};

#endif