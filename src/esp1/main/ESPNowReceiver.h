#ifndef ESPNOW_RECEIVER_H
#define ESPNOW_RECEIVER_H

#include <WiFi.h>
#include <esp_now.h>
#include "ThreePhaseCurrentPacket.h"

/**
 * @brief ESP-NOW receiver for three-phase current packets.
 *
 * This class initializes ESP-NOW in STA mode and registers a receive callback.
 * Incoming packets are copied into a local buffer and exposed via a polling API
 * to avoid doing work in ISR context.
 *
 * Compatible with ESP-IDF v5 (Arduino ESP32 core >= 3.x).
 */
class ESPNowReceiver {
public:
    /**
     * @brief Construct a new ESPNowReceiver.
     *
     * Only one instance is supported. The most recent instance
     * becomes the active receive handler.
     */
    ESPNowReceiver();

    /**
     * @brief Initialize WiFi and ESP-NOW receive mode.
     *
     * Sets WiFi to STA mode, initializes ESP-NOW (once globally),
     * and registers the receive callback.
     *
     * @return true if initialization succeeded, false otherwise.
     */
    bool begin();

    /**
     * @brief Check whether a new packet has been received.
     *
     * This flag is set by the ESP-NOW receive callback and cleared
     * when getLatest() is called.
     *
     * @return true if a new packet is available.
     */
    bool hasNewPacket() const;

    /**
     * @brief Retrieve the most recent packet.
     *
     * Copies the latest received packet and clears the "new packet" flag.
     * This function is interrupt-safe.
     *
     * @return The most recent ThreePhaseCurrentPacket.
     */
    ThreePhaseCurrentPacket getLatest();

private:
    /// Singleton instance used by the static ESP-NOW callback
    static ESPNowReceiver* _instance;

    /// Flag indicating a new packet has been received
    volatile bool _hasNew = false;

    /// Storage for the most recently received packet
    ThreePhaseCurrentPacket _latest{};

    /**
     * @brief ESP-NOW receive callback (ESP-IDF v5 signature).
     *
     * This function runs in ISR context and should do minimal work.
     * It forwards packet data to the active instance.
     *
     * @param info  Metadata about the received packet (sender MAC, etc.)
     * @param data  Pointer to received payload
     * @param len   Length of payload in bytes
     */
    static void onRecv(const esp_now_recv_info* info,
                       const uint8_t* data,
                       int len);

    /**
     * @brief Handle a received ESP-NOW packet.
     *
     * Validates packet size, copies payload into local storage,
     * and sets the "new packet" flag.
     *
     * @param data Pointer to payload bytes
     * @param len  Payload length in bytes
     */
    void handleRecv(const uint8_t* data, int len);
};

#endif