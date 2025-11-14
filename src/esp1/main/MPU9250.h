#pragma once
#include <Arduino.h>
#include <Wire.h>

class MPU9250 {
public:
    void begin();
    void readAccel(int16_t &ax, int16_t &ay, int16_t &az);
};