#include "ESPNowTransmitter.h"

static bool espNowInitializedTx = false;

ESPNowTransmitter::ESPNowTransmitter(const uint8_t peerMac[6]) {
    memcpy(_peerMac, peerMac, 6);
}

bool ESPNowTransmitter::begin() {
    // ESP-NOW requires STA mode
    WiFi.mode(WIFI_STA);

    // Initialize ESP-NOW once globally
    if (!espNowInitializedTx) {
        if (esp_now_init() != ESP_OK) {
            return false;
        }
        espNowInitializedTx = true;
    }

    // Register send callback (IDF v5)
    esp_now_register_send_cb(ESPNowTransmitter::onSend);

    // Configure peer
    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, _peerMac, 6);
    peer.channel = 0;      // auto
    peer.encrypt = false; // no encryption

    if (esp_now_add_peer(&peer) != ESP_OK) {
        return false;
    }

    return true;
}

bool ESPNowTransmitter::send(const ThreePhaseCurrentPacket& packet) {
    esp_err_t result = esp_now_send(
        _peerMac,
        reinterpret_cast<const uint8_t*>(&packet),
        sizeof(packet)
    );
    return result == ESP_OK;
}

void ESPNowTransmitter::onSend(const wifi_tx_info_t*,
                               esp_now_send_status_t) {
    // Intentionally minimal
    // status indicates success/failure
}