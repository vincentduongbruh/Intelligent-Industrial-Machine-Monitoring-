#pragma once
#include <Arduino.h>
#include <Wire.h>

class MPU6050Minimal {
public:
  bool begin(int sda = 21, int scl = 22, uint8_t addr = 0x68, uint32_t i2cHz = 400000);
  bool read(float& ax_g, float& ay_g, float& az_g,
            float& gx_dps, float& gy_dps, float& gz_dps,
            float& temp_c);

private:
  bool writeReg(uint8_t reg, uint8_t val);
  bool readRegs(uint8_t reg, uint8_t* buf, size_t len);
  uint8_t addr_ = 0x68;
};