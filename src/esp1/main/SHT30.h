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
     */
    bool begin(TwoWire& wire = Wire);

    /**
     * @brief Read the raw 16-bit temperature code.
     */
    bool readRaw(uint16_t& raw_t);

    /**
     * @brief Read temperature in °C (calibrated + EMA filtered).
     */
    bool readCelsius(float& temperature);

    /**
     * @brief Calibrate using the known **room temperature in °C**.
     *
     * The model is:
     *      T_cal = T_uncal + temp_bias
     *
     * @param samples Number of samples to average.
     * @param roomTempC Known actual room temperature in °C.
     */
    void calibrate(int samples, float roomTempC);

private:
    TwoWire* _wire;
    uint8_t address;

    EMAFilter<float> tempFilter{0.05f};
    float temp_bias;
};

#endif