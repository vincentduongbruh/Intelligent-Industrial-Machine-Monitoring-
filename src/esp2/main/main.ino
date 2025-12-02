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
