#include "MPU9250.h"

MPU9250 imu;

void setup() {
  Serial.begin(115200);
  imu.begin();
}

void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  imu.readAccel(ax, ay, az);
  imu.readGyro(gx, gy, gz);

  Serial.print(ax); Serial.print(" ");
  Serial.print(ay); Serial.print(" ");
  Serial.print(az); Serial.print(" ");
  Serial.print(gx); Serial.print(" ");
  Serial.print(gy); Serial.print(" ");
  Serial.println(gz);

  delay(100);
}