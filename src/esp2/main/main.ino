#include "ThreePhaseCurrentPacket.h"
// #include "ESPNowTransmitter.h"
#include "adc_driver.h"

// const uint_8_t RECEIVER_MAC_ADDR[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}; // get mac address of esp1

// ESPNowTransmitter esp_transmitter(RECEIVER_MAC_ADDR) // create new ESPNow transmitter

const int BIAS_PIN = 32;
const int SHUNT_PIN_1 = 36;
const int SHUNT_PIN_2 = 37;
const int SHUNT_PIN_3 = 38;


const float R_SHUNT = 210;
const float ADC_REF = 3.3;
const int ADC_MAX = 4095;
const int SAMPLE_COUNT = 256;
const uint32_t SAMPLE_DELAY_US = 500;  // ~2 kHz sampling for 50/60 Hz content
const float CT_SENS_V_PER_A = 0.556f;  // calibrated: ~0.556 V per amp RMS at ADC node

void setup() {
  Serial.begin(115200);
  // Configure ADC for each of the shunt pins
  adc_configure(SHUNT_PIN_1, 12, ADC_11db);
  adc_configure(SHUNT_PIN_2, 12, ADC_11db);
  adc_configure(SHUNT_PIN_3, 12, ADC_11db);

  // if (!esp_transmitter.begin()) {
  //   Serial.println("Error with ESP-NOW transmitter");
  //   delay(100);
  // }
}

void loop() {
  // Measure AC RMS voltage and current on one phase (SHUNT_PIN_2) via helper.
  float vrms = adc_read_rms_v(SHUNT_PIN_2, SAMPLE_COUNT, SAMPLE_DELAY_US);
  float irms = vrms / CT_SENS_V_PER_A;

  Serial.print("v_rms: "); Serial.print(vrms, 5); Serial.print(" V  ");
  Serial.print("i_rms: "); Serial.print(irms, 4); Serial.println(" A");

  delay(100);
}
