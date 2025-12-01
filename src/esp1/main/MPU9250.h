#pragma once
#include <Arduino.h>
#include <Wire.h>

class MPU9250 {
public:
    void begin();
    void readAccel(float &ax, float &ay, float &az);
};