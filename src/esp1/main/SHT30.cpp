#include "SHT30.h"

bool SHT30::begin(TwoWire &w) {
    wire = &w;
    wire->begin();
    return true;
}

bool SHT30::read(float &t) {
    wire->beginTransmission(address);
    wire->write(0x2C);
    wire->write(0x06);
    if (wire->endTransmission() != 0) return false;
    delay(15);

    wire->requestFrom(address, (uint8_t)6);
    if (wire->available() < 6) return false;

    uint16_t rt = wire->read() << 8 | wire->read();
    wire->read();
    wire->read();
    wire->read();
    wire->read();

    t = -45 + 175 * (rt / 65535.0f);
    t = tempFilter.update(t);
    return true;
}