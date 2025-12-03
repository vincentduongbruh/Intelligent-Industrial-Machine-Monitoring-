/**
 * @file MPU9250.h
 * @brief Accelerometer-only driver for the MPU9250.
 *
 * Provides initialization, raw accelerometer reading, calibrated
 * accelerometer reading, and bias calibration using an affine model:
 *
 *     a = (raw - bias_raw) / sensitivity
 *
 * Sensitivity for ±2g mode is 16384 LSB/g.
 */

#ifndef MPU9250_H
#define MPU9250_H

#include <Wire.h>
#include "EMAFilter.h"

class MPU9250 {
public:
    /**
     * @brief Construct an MPU9250 driver using the given I2C address.
     * @param addr I2C address (0x68 if AD0=LOW, 0x69 if AD0=HIGH).
     */
    MPU9250(uint8_t addr = 0x68);

    /**
     * @brief Initialize the sensor and configure accelerometer for ±2g.
     * @return true if initialization succeeded.
     */
    bool begin(int sda = -1, int scl = -1);

    /**
     * @brief Read raw accelerometer values from the sensor.
     * @param ax Raw X-axis output.
     * @param ay Raw Y-axis output.
     * @param az Raw Z-axis output.
     * @return true if read succeeded.
     */
    bool readAccelRaw(int16_t& ax, int16_t& ay, int16_t& az);

    /**
     * @brief Read calibrated accelerometer values in g.
     * Applies: (raw - bias_raw) / sensitivity.
     * @param ax Output X-axis acceleration (g).
     * @param ay Output Y-axis acceleration (g).
     * @param az Output Z-axis acceleration (g).
     * @return true if read succeeded.
     */
    bool readAccelG(float& ax, float& ay, float& az);

    /**
     * @brief Compute raw accelerometer biases by averaging samples.
     * Assumes device is stationary with Z ≈ +1g.
     * @param samples Number of samples to average.
     */
    void calibrate(int samples);

private:
    uint8_t address;
    float ax_bias = 0.0f;
    float ay_bias = 0.0f;
    float az_bias = 0.0f;
    EMAFilter<float> axFilter{0.2f};
    EMAFilter<float> ayFilter{0.2f};
    EMAFilter<float> azFilter{0.2f};
};

#endif