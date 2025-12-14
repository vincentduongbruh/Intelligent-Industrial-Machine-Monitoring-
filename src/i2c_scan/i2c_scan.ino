#include <Wire.h>

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);   // SDA, SCL
    Wire.setClock(100000);
}

void loop() {
    Serial.println("Scanning I2C bus...");
    uint8_t found = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.print("Found device at 0x");
            if (addr < 16) Serial.print('0');
            Serial.println(addr, HEX);
            found++;
        }
        delay(2);
    }
    if (found == 0) {
        Serial.println("No I2C devices found.");
    }
    Serial.println("----------------------");
    delay(2000);
}
