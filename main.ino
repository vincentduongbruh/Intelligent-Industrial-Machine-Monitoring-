#include "MPU6050.h"

MPU6050Minimal imu;

void setup() {
  Serial.begin(115200);
  if (imu.begin()) Serial.println("MPU6050 initialized successfully.");
}

void loop() {
  float ax, ay, az, gx, gy, gz, tc;
  if (imu.read(ax, ay, az, gx, gy, gz, tc)) {
    Serial.printf("A[g]: %.2f %.2f %.2f  G[dps]: %.2f %.2f %.2f  T[C]: %.2f\n", ax, ay, az, gx, gy, gz, tc);
  }
  delay(100);
}