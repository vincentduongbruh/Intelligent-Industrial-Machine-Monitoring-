#ifndef SHT30_H
#define SHT30_H

#include <Wire.h>
#include "EMAFilter.h"

/**
 * @class SHT30
 * @brief Temperature reader with EMA filtering and affine offset calibration.
 */
class SHT30 {
public:
    /**
     * @brief Construct an SHT30 object.
     */
    SHT30(uint8_t addr = 0x44)
        : _wire(nullptr), address(addr), tempFilter(0.05f), temp_bias(0.0f) {}

    /**
     * @brief Initializes the SHT30 sensor on a given I2C bus.
     * NOTE: Wire.begin() should normally be called in setup().
     * @return true if initialization was successful, false otherwise.
     */
    bool begin(TwoWire& wire = Wire);

    /**
     * @brief Read the raw 16-bit temperature code.
     * @return true if read was successful, false otherwise.
     */
    bool readRaw(uint16_t& raw_t);

    /**
     * @brief Read temperature in °C (calibrated + EMA filtered).
     * @return true if read was successful, false otherwise.
     */
    bool readCelsius(float& temperature);

    /**
     * @brief Calibrate using the known **room temperature in °C**.
     * The model is: T_cal = T_uncal + temp_bias
     */
    void calibrate(int samples, float roomTempC);

private:
    TwoWire* _wire;
    uint8_t address;

    EMAFilter<float> tempFilter{0.05f};
    float temp_bias;
};

#endif