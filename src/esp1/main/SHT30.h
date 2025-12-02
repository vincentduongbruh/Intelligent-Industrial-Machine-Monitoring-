/**
 * @file SHT30.h
 * @brief Driver interface for the Sensirion SHT30 temperature & humidity sensor.
 *
 * Provides temperature and humidity reading via I2C. Uses the recommended
 * measurement mode defined in the datasheet.
 *
 * Typical usage:
 * @code
 *   SHT30 sht;
 *   sht.begin(Wire);
 *
 *   float temperature;
 *   if (sht.read(temperature)) {
 *       ...
 *   }
 * @endcode
 */

#ifndef SHT30_H
#define SHT30_H

#include <Wire.h>

class SHT30 {
public:
    /**
     * @brief Construct an SHT30 object.
     */
    SHT30();

    /**
     * @brief Initializes the SHT30 sensor on a given I2C bus.
     * @param wire I2C interface (default is Wire).
     * @return true if initialization was successful.
     */
    bool begin(TwoWire& wire = Wire);

    /**
     * @brief Reads temperature from the sensor.
     * @param temperature Output temperature in °C.
     * @return true if measurement succeeded and data is valid.
     */
    bool read(float& temperature);

private:
    TwoWire* _wire;
    uint8_t address;
};

#endif