#include "ESPNowTransmitter.h"

static bool espNowInitializedTx = false;

ESPNowTransmitter::ESPNowTransmitter(const uint8_t peerMac[6]) {
    memcpy(_peerMac, peerMac, 6);
}

bool ESPNowTransmitter::begin() {
    WiFi.mode(WIFI_STA);

    if (!espNowInitializedTx) {
        if (esp_now_init() != ESP_OK) return false;
        espNowInitializedTx = true;
    }

    esp_now_register_send_cb(onSend);

    esp_now_peer_info_t peer{};
    memcpy(peer.peer_addr, _peerMac, 6);
    peer.channel = 0;
    peer.encrypt = false;

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