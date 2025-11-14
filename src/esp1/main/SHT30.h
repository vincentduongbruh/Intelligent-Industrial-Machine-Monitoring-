#pragma once
#include <Arduino.h>
#include <Wire.h>

class SHT30 {
public:
    void begin(TwoWire &w = Wire);
    bool read(float &t);
private:
    TwoWire *wire;
    uint8_t addr = 0x44;
};