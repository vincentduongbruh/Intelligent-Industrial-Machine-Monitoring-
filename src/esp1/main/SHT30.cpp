#include "SHT30.h"

bool SHT30::begin(TwoWire &w) {
    _wire = &w;
    _wire->begin();
    return true;
}

bool SHT30::readRaw(uint16_t &raw_t) {
    if (!_wire) return false;

    _wire->beginTransmission(address);
    _wire->write(0x2C);
    _wire->write(0x06);
    if (_wire->endTransmission() != 0) return false;

    delay(15);

    _wire->requestFrom(address, (uint8_t)6);
    if (_wire->available() < 6) return false;

    raw_t = (uint16_t(_wire->read()) << 8) | _wire->read();

    _wire->read();
    _wire->read();
    _wire->read();
    _wire->read();

    return true;
}

bool SHT30::readCelsius(float &t) {
    uint16_t raw;
    if (!readRaw(raw)) return false;

    float t_uncal = -45.0f + 175.0f * (float(raw) / 65535.0f);
    float t_cal = t_uncal + temp_bias;
    t = tempFilter.update(t_cal);

    return true;
}

void SHT30::calibrate(int samples, float roomTempC) {
    if (samples <= 0) return;

    float sum = 0;
    int count = 0;

    for (int i = 0; i < samples; i++) {
        uint16_t raw;
        if (readRaw(raw)) {
            float t_uncal = -45.0f + 175.0f * (float(raw) / 65535.0f);
            sum += t_uncal;
            count++;
        }
        delay(20);
    }

    if (count == 0) return;

    float avg_uncal = sum / count;
    temp_bias = roomTempC - avg_uncal;
}