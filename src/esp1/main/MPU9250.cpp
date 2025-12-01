#include "MPU9250.h"

#define MPU 0x68
#define ACCEL_XOUT_H 0x3B

static const float ACCEL_SENS = 16384.0f;
static const float G_TO_MS2 = 9.80665f;

void MPU9250::begin() {
    Wire.begin();

    // Wake up MPU9250
    Wire.beginTransmission(MPU); 
    Wire.write(0x6B); 
    Wire.write(0x00); 
    Wire.endTransmission();

    // Set Accelerometer Range to +-2g
    Wire.beginTransmission(MPU); 
    Wire.write(0x1C); 
    Wire.write(0x00); 
    Wire.endTransmission();
}

void MPU9250::readAccel(float &ax, float &ay, float &az) {

    Wire.beginTransmission(MPU);
    Wire.write(ACCEL_XOUT_H);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 6); // Request 6B for Accel X, Y, Z

    float raw_ax = Wire.read() << 8 | Wire.read();
    float raw_ay =Wire.read() << 8 | Wire.read();
    float raw_az = Wire.read() << 8 | Wire.read();
    ax = (raw_ax / ACCEL_SENS) * G_TO_MS2;
    ay = (raw_ay / ACCEL_SENS) * G_TO_MS2;
    az = (raw_az / ACCEL_SENS) * G_TO_MS2;
}