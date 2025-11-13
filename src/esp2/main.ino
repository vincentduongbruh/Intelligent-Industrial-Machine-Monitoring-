const int SHUNT_PIN = 34;
const float R_SHUNT = 0.1;
const float ADC_REF = 3.3;
const int ADC_MAX = 4095;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

void loop() {
  int adcValue = analogRead(SHUNT_PIN);
  float voltage = (adcValue * ADC_REF) / ADC_MAX;
  float current = voltage / R_SHUNT;
  Serial.print(current);
  Serial.println(" A");
  delay(200);
}