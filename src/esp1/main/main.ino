#include "MPU9250.h"
#include "SHT30.h"

MPU9250 imu;
SHT30 sht;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22, 50000);
  imu.begin();
  sht.begin();
}

void loop() {
  int16_t ax, ay, az;
  imu.readAccel(ax, ay, az);

  float lastTemp;
  float temp;
  bool ok = sht.read(temp);

  if (ok) {
    lastTemp = temp;
  }

  Serial.printf("ax:%d ay:%d az:%d temp:%f\n",
                ax, ay, az, 
                lastTemp);

  delay(100);
}