#pragma once
#include <Arduino.h>
#include <Wire.h>

class MPU9250 {
public:
    void begin();
    void readAccel(int16_t &ax, int16_t &ay, int16_t &az);
    void readGyro(int16_t &gx, int16_t &gy, int16_t &gz);
};