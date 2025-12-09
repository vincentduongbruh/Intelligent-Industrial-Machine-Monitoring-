#include "MPU6500.h"

static constexpr float ACC_SENS = 16384.0f;

MPU6500::MPU6500(uint8_t addr) : _addr(addr) {}

bool MPU6500::begin(int sda, int scl) {
    static bool wireInitialized = false;
    if (!wireInitialized) {
        Wire.begin(sda, scl);
        wireInitialized = true;
    }

    Wire.beginTransmission(_addr);
    Wire.write(0x6B);
    Wire.write(0x00);
    return (Wire.endTransmission() == 0);
}

void MPU6500::readAccel(int16_t &ax, int16_t &ay, int16_t &az) {
    Wire.beginTransmission(_addr);
    Wire.write(0x3B);
    Wire.endTransmission(false);

    Wire.requestFrom((int)_addr, 6, true);

    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();
}

void MPU6500::readAccelG(float &ax, float &ay, float &az) {
    int16_t rx, ry, rz;
    readAccel(rx, ry, rz);

    ax = (rx - ax_bias) / ACC_SENS;
    ay = (ry - ay_bias) / ACC_SENS;
    az = (rz - az_bias) / ACC_SENS;

    ax = axFilter.update(ax);
    ay = ayFilter.update(ay);
    az = azFilter.update(az);
}

void MPU6500::calibrate(int samples) {
    int32_t xs = 0, ys = 0, zs = 0;

    for (int i = 0; i < samples; ++i) {
        int16_t ax, ay, az;
        readAccel(ax, ay, az);
        xs += ax;
        ys += ay;
        zs += az;
        delay(2);
    }

    ax_bias = static_cast<float>(xs) / samples;
    ay_bias = static_cast<float>(ys) / samples;
    az_bias = static_cast<float>(zs) / samples - ACC_SENS;
}