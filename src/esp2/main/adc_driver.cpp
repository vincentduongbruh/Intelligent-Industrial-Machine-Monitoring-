#include "adc_driver.h"

bool adc_configure(uint8_t pin,
                   uint8_t width_bits,
                   adc_attenuation_t attenuation) {
    // Configure ADC resolution globally and attenuation per pin.
    analogReadResolution(width_bits);
    analogSetPinAttenuation(pin, attenuation);
    return true;
}

uint16_t adc_read_raw(uint8_t pin) {
    int val = analogRead(pin);
    return (val < 0) ? 0 : static_cast<uint16_t>(val);
}

float adc_raw_to_voltage(uint16_t raw, float vref, uint16_t max_count) {
    if (max_count == 0) return 0.0f;
    return (static_cast<float>(raw) * vref) / static_cast<float>(max_count);
}

float adc_read_voltage(uint8_t pin, float vref, uint16_t max_count) {
    // Prefer calibrated millivolts if available in Arduino core.
    return static_cast<float>(adc_read_mv(pin)) / 1000.0f;
}

uint16_t adc_read_mv(uint8_t pin) {
    //  eFuse calibration for better accuracy compred to current ADC (from the arudino)
    int mv = analogReadMilliVolts(pin);
    return (mv < 0) ? 0 : static_cast<uint16_t>(mv);
}

uint16_t adc_read_rms_mv(uint8_t pin,
                         uint16_t sample_count,
                         uint32_t sample_delay_us) {
    if (sample_count == 0) return 0;

    float mean = 0.0f;
    float m2 = 0.0f; 

    for (uint16_t i = 1; i <= sample_count; i++) {
        float x = static_cast<float>(adc_read_mv(pin));
        float delta = x - mean;
        mean += delta / i;
        m2 += delta * (x - mean);
        if (sample_delay_us) delayMicroseconds(sample_delay_us);
    }

    float rms = sqrtf(m2 / sample_count);  // AC RMS (bias removed) in mV
    return static_cast<uint16_t>(rms);
}

float adc_read_rms_v(uint8_t pin,
                     uint16_t sample_count,
                     uint32_t sample_delay_us) {
    return static_cast<float>(adc_read_rms_mv(pin, sample_count, sample_delay_us)) / 1000.0f;
}

float adc_read_irms(uint8_t pin,
                    float volts_per_amp,
                    uint16_t sample_count,
                    uint32_t sample_delay_us) {
    if (volts_per_amp <= 0.0f) return 0.0f;
    float vrms = adc_read_rms_v(pin, sample_count, sample_delay_us);
    return vrms / volts_per_amp;
}
