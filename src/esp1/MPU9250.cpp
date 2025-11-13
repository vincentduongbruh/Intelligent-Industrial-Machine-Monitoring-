#include "MPU9250.h"

#define MPU 0x68

void MPU9250::begin() {
    Wire.begin();
    Wire.beginTransmission(MPU); Wire.write(0x6B); Wire.write(0x00); Wire.endTransmission();
    Wire.beginTransmission(MPU); Wire.write(0x1C); Wire.write(0x00); Wire.endTransmission();
    Wire.beginTransmission(MPU); Wire.write(0x1B); Wire.write(0x00); Wire.endTransmission();
}

void MPU9250::readAccel(int16_t &ax, int16_t &ay, int16_t &az) {
    Wire.beginTransmission(MPU);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6);
    ax = Wire.read() << 8 | Wire.read();
    ay = Wire.read() << 8 | Wire.read();
    az = Wire.read() << 8 | Wire.read();
}

void MPU9250::readGyro(int16_t &gx, int16_t &gy, int16_t &gz) {
    Wire.beginTransmission(MPU);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6);
    gx = Wire.read() << 8 | Wire.read();
    gy = Wire.read() << 8 | Wire.read();
    gz = Wire.read() << 8 | Wire.read();
}