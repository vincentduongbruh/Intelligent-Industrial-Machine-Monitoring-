#include "SHT30.h"

static uint8_t sht30_crc8(const uint8_t* data, int len) {
    uint8_t crc = 0xFF;
    for (int i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int j = 0; j < 8; ++j) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0x31;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

bool SHT30::begin(TwoWire& w) {
    _wire = &w;
    return true;
}

bool SHT30::readRaw(uint16_t& raw_t) {
    if (!_wire) return false;

    _wire->beginTransmission(address);
    _wire->write(0x2C);
    _wire->write(0x06);
    if (_wire->endTransmission() != 0) return false;

    delay(20);

    if (_wire->requestFrom(address, (uint8_t)6) != 6) {
        return false;
    }

    if (_wire->available() < 6) return false;

    uint8_t t_msb = _wire->read();
    uint8_t t_lsb = _wire->read();
    uint8_t t_crc = _wire->read();

    uint8_t t_data[2] = { t_msb, t_lsb };
    if (sht30_crc8(t_data, 2) != t_crc) {
        _wire->read();
        _wire->read();
        _wire->read();
        return false;
    }

    raw_t = (uint16_t(t_msb) << 8) | t_lsb;

    _wire->read();
    _wire->read();
    _wire->read();

    return true;
}

bool SHT30::readCelsius(float& t) {
    uint16_t raw;
    if (!readRaw(raw)) return false;

    float t_uncal = -45.0f + 175.0f * (float(raw) / 65535.0f);
    float t_cal = t_uncal + temp_bias;
    t = tempFilter.update(t_cal);

    return true;
}

void SHT30::calibrate(int samples, float roomTempC) {
    if (samples <= 0) return;

    float sum = 0.0f;
    int count = 0;

    for (int i = 0; i < samples; ++i) {
        uint16_t raw;
        if (readRaw(raw)) {
            float t_uncal = -45.0f + 175.0f * (float(raw) / 65535.0f);
            sum += t_uncal;
            ++count;
        }
        delay(20);
    }

    if (count == 0) return;

    float avg_uncal = sum / count;
    temp_bias = roomTempC - avg_uncal;
}
