#include <Servo.h>

const int ESC_PIN = 2;   // PWM pin on Nano
Servo esc;

void setup() {
  Serial.begin(115200);

  esc.attach(ESC_PIN);

  // Arm ESC
  esc.writeMicroseconds(1000);
  delay(3000);
}

void loop() {
  esc.writeMicroseconds(1200);   // test throttle
  delay(5000);

  esc.writeMicroseconds(1000);   // back to idle
  delay(5000);
}
