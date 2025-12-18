#include <Servo.h>

const int ESC_PIN = 2;
Servo esc;

int SWITCH_IN = 3;
int SWITCH_OUT = 4;
void setup() {
  Serial.begin(115200);

  esc.attach(ESC_PIN);

  esc.writeMicroseconds(1000);
  delay(3000);

  pinMode(SWITCH_OUT, OUTPUT);
  pinMode(SWITCH_IN, INPUT);
  digitalWrite(SWITCH_OUT, HIGH);
}

void loop() {
  if (digitalRead(SWITCH_IN)){
      esc.writeMicroseconds(1100);
      Serial.println("ON");
  }
  else {
    esc.writeMicroseconds(1000);
    Serial.println("OFF");
  }
}
