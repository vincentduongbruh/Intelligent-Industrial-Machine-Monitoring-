#include <Servo.h>

const int ESC_PIN = 2;
Servo esc;

void setup() {
  Serial.begin(115200);

  esc.attach(ESC_PIN);

  esc.writeMicroseconds(1000);
  delay(3000);
}

void loop() {
  esc.writeMicroseconds(1800);
  delay(5000);
  
  esc.writeMicroseconds(1000);
  delay(5000);
}
