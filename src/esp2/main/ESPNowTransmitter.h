#ifndef ESPNOW_TRANSMITTER_H
#define ESPNOW_TRANSMITTER_H

#include <WiFi.h>
#include <esp_now.h>
#include "ThreePhaseCurrentPacket.h"

/**
 * @brief ESP-NOW transmitter for three-phase current packets.
 *
 * Initializes ESP-NOW in STA mode and transmits fixed-size
 * ThreePhaseCurrentPacket payloads to a configured peer.
 *
 * Compatible with ESP-IDF v5 (Arduino ESP32 core >= 3.x).
 */
class ESPNowTransmitter {
public:
    /**
     * @brief Construct a transmitter targeting a specific peer MAC address.
     *
     * @param peerMac 6-byte MAC address of the receiver ESP32.
     */
    explicit ESPNowTransmitter(const uint8_t peerMac[6]);

    /**
     * @brief Initialize WiFi and ESP-NOW transmit mode.
     *
     * Sets WiFi to STA mode, initializes ESP-NOW (once globally),
     * registers the send callback, and adds the peer.
     *
     * @return true if initialization succeeded.
     */
    bool begin();

    /**
     * @brief Send a three-phase current packet.
     *
     * @param packet Packet to send.
     * @return true if the packet was queued successfully.
     */
    bool send(const ThreePhaseCurrentPacket& packet);

private:
    uint8_t _peerMac[6];

    /**
     * @brief ESP-NOW send callback (ESP-IDF v5 signature).
     *
     * Called by the ESP-NOW stack when a packet transmission completes.
     * Runs in WiFi task context — keep this minimal.
     *
     * @param info   Transmission metadata (includes destination MAC)
     * @param status ESP_NOW_SEND_SUCCESS or ESP_NOW_SEND_FAIL
     */
    static void onSend(const wifi_tx_info_t* info,
                       esp_now_send_status_t status);
};

#endif