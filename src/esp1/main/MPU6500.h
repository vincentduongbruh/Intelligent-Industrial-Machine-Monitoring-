#ifndef MPU6500_H
#define MPU6500_H

#include <Arduino.h>
#include <Wire.h>
#include "EMAFilter.h"

/**
 * @file MPU6500.h
 * @brief Minimal accelerometer-only driver for the MPU6500 IMU.
 *
 * Provides raw and calibrated accelerometer readings using an affine
 * sensor model:
 *
 *     a = (raw - bias_raw) / sensitivity
 *
 * Biases are collected in raw units via calibrate(), assuming the sensor
 * is held still with Z ≈ +1g.
 */
class MPU6500 {
public:
    /**
     * @brief Construct an MPU6500 object.
     * @param addr I2C address (0x68 if AD0=LOW, 0x69 if AD0=HIGH)
     */
    MPU6500(uint8_t addr = 0x68, TwoWire &bus = Wire);

    /**
     * @brief Initialize the MPU6500 over I2C.
     *        Configures accelerometer for ±2g and enables LPF,
     *        matching MPU9250 behavior.
     * @param wire I2C bus to use.
     * @param sda SDA pin (optional, for ESP32 secondary bus).
     * @param scl SCL pin (optional, for ESP32 secondary bus).
     * @return true if initialization succeeded.
     */
    bool begin(TwoWire &wire = Wire, int sda = -1, int scl = -1);

    /**
     * @brief Read raw 16-bit accelerometer values.
     *        Returns false if I2C transaction fails.
     */
    bool readAccelRaw(int16_t &ax, int16_t &ay, int16_t &az);

    /**
     * @brief Read calibrated accelerometer values in g.
     * Applies: (raw - bias_raw) / sensitivity.
     * @return true if read succeeded.
     */
    bool readAccelG(float &ax, float &ay, float &az);

    /**
     * @brief Estimate raw accelerometer biases by averaging samples.
     * Assumes the sensor is stationary with Z ≈ +1g.
     * @param samples Number of readings to average.
     */
    void calibrate(int samples);

private:
    uint8_t _addr;
    TwoWire* _wire;
    float ax_bias = 0.0f;
    float ay_bias = 0.0f;
    float az_bias = 0.0f;

    EMAFilter<float> axFilter{0.2f};
    EMAFilter<float> ayFilter{0.2f};
    EMAFilter<float> azFilter{0.2f};
};

#endif
