#include <Wire.h>

void scanBus(TwoWire &bus, const char *name, int sda, int scl) {
    bus.begin(sda, scl);
    bus.setClock(100000);
    Serial.printf("Scan %s (SDA=%d SCL=%d)\n", name, sda, scl);
    for (uint8_t a = 1; a < 127; a++) {
        bus.beginTransmission(a);
        if (bus.endTransmission() == 0) {
            Serial.printf("  found 0x%02X\n", a);
        }
        delay(2);
    }
    Serial.println();
}

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }
    scanBus(Wire,  "Wire",  21, 22);
    scanBus(Wire1, "Wire1", 27, 33);
    // Stop here; use this sketch only for scanning.
    while (true) delay(1000);
}

void loop() {}
