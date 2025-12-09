#include "ThreePhaseCurrentPacket.h"
#include "ESPNowTransmitter.h"

const uint_8_t RECEIVER_MAC_ADDR[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}; // get mac address of esp1

ESPNowTransmitter esp_transmitter(RECEIVER_MAC_ADDR) // create new ESPNow transmitter

const int BIAS_PIN = 32;
const int SHUNT_PIN_1 = 33;
const int SHUNT_PIN_2 = 34;
const int SHUNT_PIN_3 = 35;


const float R_SHUNT = 210;
const float ADC_REF = 3.3;
const int ADC_MAX = 4095;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  if (!esp_transmitter.begin()) {
    Serial.println("Error with ESP-NOW transmitter");
    delay(100);
  }
}

float currentRead(int pin) {
  int adcValue = analogRead(pin);
  float voltage = (adcValue * ADC_REF) / ADC_MAX; //If noisy, change to BIAS_PIN value
  float current = voltage / R_SHUNT;
  return current;
}

void loop() {
  Serial.print("i_a: ");
  Serial.print(currentRead(SHUNT_PIN_1));
  Serial.println(" A");

  Serial.print("i_b: ");
  Serial.print(currentRead(SHUNT_PIN_2));
  Serial.println(" A");

  Serial.print("i_c: ");
  Serial.print(currentRead(SHUNT_PIN_3));
  Serial.println(" A");
  delay(200);
}
