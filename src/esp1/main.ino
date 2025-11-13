#include "MPU9250.h"
#include "SHT30.h"

MPU9250 imu;
SHT30 sht;

void setup() {
  Serial.begin(115200);
  imu.begin();
  sht.begin();
}

void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  imu.readAccel(ax, ay, az);
  imu.readGyro(gx, gy, gz);

  float temp;
  bool ok = sht.read(temp);

  if (ok) {
    Serial.println("%d %d %d %d %d %d %.2f\n",
                  ax, ay, az,
                  gx, gy, gz,
                  temp);
  } else {
    Serial.println("Missing Data");
  }

  delay(100);
}