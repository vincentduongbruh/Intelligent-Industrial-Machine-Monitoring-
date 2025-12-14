#include "MPU6500.h"

static constexpr float ACC_SENS = 16384.0f;

MPU6500::MPU6500(uint8_t addr, TwoWire &bus) : _addr(addr), _wire(&bus) {}

bool MPU6500::begin(TwoWire &wire, int sda, int scl) {
    _wire = &wire;

    if (sda >= 0 && scl >= 0) _wire->begin(sda, scl);
    else _wire->begin();
    _wire->setClock(100000);

    _wire->beginTransmission(_addr);
    _wire->write(0x6B);
    _wire->write(0x00);
    if (_wire->endTransmission() != 0) return false;

    _wire->beginTransmission(_addr);
    _wire->write(0x1C);
    _wire->write(0x00);
    if (_wire->endTransmission() != 0) return false;

    _wire->beginTransmission(_addr);
    _wire->write(0x1D);
    _wire->write(0x03);
    if (_wire->endTransmission() != 0) return false;

    return true;
}

bool MPU6500::readAccelRaw(int16_t &ax, int16_t &ay, int16_t &az) {
    _wire->beginTransmission(_addr);
    _wire->write(0x3B);
    if (_wire->endTransmission(false) != 0) return false;

    if (_wire->requestFrom((int)_addr, 6) != 6) return false;

    ax = (_wire->read() << 8) | _wire->read();
    ay = (_wire->read() << 8) | _wire->read();
    az = (_wire->read() << 8) | _wire->read();

    return true;
}

bool MPU6500::readAccelG(float &ax, float &ay, float &az) {
    int16_t rx, ry, rz;

    if (!readAccelRaw(rx, ry, rz)) return false;

    ax = (rx - ax_bias) / ACC_SENS;
    ay = (ry - ay_bias) / ACC_SENS;
    az = (rz - az_bias) / ACC_SENS;

    ax = axFilter.update(ax);
    ay = ayFilter.update(ay);
    az = azFilter.update(az);

    return true;
}

void MPU6500::calibrate(int samples) {
    int32_t xs = 0, ys = 0, zs = 0;

    for (int i = 0; i < samples; ++i) {
        int16_t ax, ay, az;
        if (readAccelRaw(ax, ay, az)) {
            xs += ax;
            ys += ay;
            zs += az;
        }
        delay(2);
    }

    ax_bias = xs / samples;
    ay_bias = ys / samples;
    az_bias = (zs / samples) - ACC_SENS;
}
