/**
 * @file MPU9250.h
 * @brief Driver interface for the MPU9250 IMU.
 *
 * Provides initialization and access to accelerometer and gyroscope values
 * over I2C. The accelerometer readings are returned in units of g.
 *
 * Typical usage:
 * @code
 *   MPU9250 imu;
 *   imu.begin();
 *   float ax, ay, az;
 *   imu.readAccel(ax, ay, az);
 * @endcode
 */

#ifndef MPU9250_H
#define MPU9250_H

#include <Wire.h>

class MPU9250 {
public:
    /**
     * @brief Construct an MPU9250 object.
     */
    MPU9250();

    /**
     * @brief Initializes the MPU9250 sensor over I2C.
     * Must be called before any read functions.
     */
    void begin();

    /**
     * @brief Reads accelerometer measurements.
     * @param ax Output acceleration along X-axis in g.
     * @param ay Output acceleration along Y-axis in g.
     * @param az Output acceleration along Z-axis in g.
     * @return true if read was successful.
     */
    bool readAccel(float& ax, float& ay, float& az);

    /**
     * @brief Reads raw 16-bit accelerometer register values.
     * @param ax Raw X-axis reading.
     * @param ay Raw Y-axis reading.
     * @param az Raw Z-axis reading.
     * @return true if read was successful.
     */
    bool readAccelRaw(int16_t& ax, int16_t& ay, int16_t& az);

private:
    uint8_t address;
};

#endif
