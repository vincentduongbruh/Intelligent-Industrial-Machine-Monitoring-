#include "ESPNowReceiver.h"

static bool espNowInitializedRx = false;
ESPNowReceiver* ESPNowReceiver::_instance = nullptr;

ESPNowReceiver::ESPNowReceiver() {
    _instance = this;
}

bool ESPNowReceiver::begin() {
    WiFi.mode(WIFI_STA);

    if (!espNowInitializedRx) {
        if (esp_now_init() != ESP_OK) return false;
        espNowInitializedRx = true;
    }

    esp_now_register_recv_cb(ESPNowReceiver::onRecv);
    return true;
}

bool ESPNowReceiver::hasNewPacket() const {
    return _hasNew;
}

ThreePhaseCurrentPacket ESPNowReceiver::getLatest() {
    _hasNew = false;
    return _latest;
}

void ESPNowReceiver::onRecv(const uint8_t* mac,
                            const uint8_t* data,
                            int len) {
    if (_instance) {
        _instance->handleRecv(mac, data, len);
    }
}

void ESPNowReceiver::handleRecv(const uint8_t*, const uint8_t* data, int len) {
    if (len != sizeof(ThreePhaseCurrentPacket)) return;

    memcpy(&_latest, data, sizeof(_latest));
    _hasNew = true;
}