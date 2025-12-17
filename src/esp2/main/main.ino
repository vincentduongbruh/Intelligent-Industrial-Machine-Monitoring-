// #include "ThreePhaseCurrentPacket.h"
// #include "ESPNowTransmitter.h"
#include "ADC.h"

// const uint8_t RECEIVER_MAC_ADDR[] = {0x30, 0xAE, 0xA4, 0x05, 0x96, 0xC4};
// ESPNowTransmitter esp_transmitter(RECEIVER_MAC_ADDR);
// ThreePhaseCurrentPacket packet;

const int BIAS_PIN = 32;
const int SHUNT_PIN_1 = 36;
const int SHUNT_PIN_2 = 37;
const int SHUNT_PIN_3 = 38;


const float R_SHUNT = 680;
const float ADC_REF = 3.3;
const int ADC_MAX = 4095;
const int SAMPLE_COUNT = 256;
const uint32_t SAMPLE_DELAY_US = 500;  // ~2 kHz for 50/60 Hz content
const float CT_SENS_V_PER_A = 0.556f;  // ~0.556 V/A RMS at ADC node

void setup() {
  Serial.begin(115200);
  adc_configure(SHUNT_PIN_1, 12, ADC_11db);
  adc_configure(SHUNT_PIN_2, 12, ADC_11db);
  adc_configure(SHUNT_PIN_3, 12, ADC_11db);

  // if (!esp_transmitter.begin()) {
  //   Serial.println("ESP-Now transmitter: Fail");
  //   delay(100);
  // }
  // Serial.println("ESP-NOW transmitter: Ready");
}

void loop() {
  // packet.ia = adc_read_voltage(SHUNT_PIN_1) / R_SHUNT;
  // packet.ib = adc_read_voltage(SHUNT_PIN_2) / R_SHUNT;
  // packet.ic = adc_read_voltage(SHUNT_PIN_3) / R_SHUNT;

  float ia, ib, ic;
  ia = adc_read_voltage(SHUNT_PIN_1) / R_SHUNT;
  ib = adc_read_voltage(SHUNT_PIN_2) / R_SHUNT;
  ic = adc_read_voltage(SHUNT_PIN_3) / R_SHUNT;

  Serial.printf("ia:%f ib:%f ic:%f\n",
              ia, ib, ic);

  // esp_transmitter.send(packet);
  delay(8);
}