#ifndef ESPNOW_RECEIVER_H
#define ESPNOW_RECEIVER_H

#include <WiFi.h>
#include <esp_now.h>
#include "ThreePhaseCurrentPacket.h"

/**
 * @brief ESP-NOW receiver for three-phase current packets.
 */
class ESPNowReceiver {
public:
    ESPNowReceiver();

    /**
     * @brief Initialize WiFi/ESPNOW and register callback.
     * @return true if initialization succeeded.
     */
    bool begin();

    /**
     * @brief Whether a new packet has been received.
     */
    bool hasNewPacket() const;

    /**
     * @brief Retrieve the most recent packet (clears flag).
     */
    ThreePhaseCurrentPacket getLatest();

private:
    static ESPNowReceiver* _instance;
    volatile bool _hasNew = false;
    ThreePhaseCurrentPacket _latest{};

    static void onRecv(const uint8_t* mac, const uint8_t* data, int len);
    void handleRecv(const uint8_t* mac, const uint8_t* data, int len);
};

#endif