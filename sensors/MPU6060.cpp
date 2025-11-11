#include "MPU6050.h"

bool MPU6050Minimal::begin(int sda, int scl, uint8_t addr, uint32_t i2cHz) {
  addr_ = addr;
  Wire.begin(sda, scl);
  Wire.setClock(i2cHz);
  Wire.beginTransmission(addr_);
  Wire.write(0x6B);
  Wire.write(0);
  return Wire.endTransmission() == 0;
}

bool MPU6050Minimal::read(float& ax, float& ay, float& az,
                          float& gx, float& gy, float& gz, float& t) {
  Wire.beginTransmission(addr_);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;

  uint8_t buf[14];
  if (Wire.requestFrom((int)addr_, 14) != 14) return false;

  int16_t AcX = buf[0]<<8 | buf[1];
  int16_t AcY = buf[2]<<8 | buf[3];
  int16_t AcZ = buf[4]<<8 | buf[5];
  int16_t Tmp = buf[6]<<8 | buf[7];
  int16_t GyX = buf[8]<<8 | buf[9];
  int16_t GyY = buf[10]<<8 | buf[11];
  int16_t GyZ = buf[12]<<8 | buf[13];

  ax = AcX / 16384.0;
  ay = AcY / 16384.0;
  az = AcZ / 16384.0;
  gx = GyX / 131.0;
  gy = GyY / 131.0;
  gz = GyZ / 131.0;
  t  = Tmp / 340.0 + 36.53;
  return true;
}
