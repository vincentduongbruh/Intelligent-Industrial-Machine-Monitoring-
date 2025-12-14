#pragma once

#include <Arduino.h>
#include "esp32-hal-adc.h"  // for adc_attenuation_t

// Lightweight ADC helpers for ESP32 (Arduino core).
bool adc_configure(uint8_t pin,
                   uint8_t width_bits = 12,
                   adc_attenuation_t attenuation = ADC_11db);

uint16_t adc_read_raw(uint8_t pin);

float adc_raw_to_voltage(uint16_t raw,
                         float vref = 3.3f,
                         uint16_t max_count = 4095);

float adc_read_voltage(uint8_t pin,
                       float vref = 3.3f,
                       uint16_t max_count = 4095);

uint16_t adc_read_mv(uint8_t pin);  // calibrated mV via analogReadMilliVolts


uint16_t adc_read_rms_mv(uint8_t pin,
                         uint16_t sample_count = 256,
                         uint32_t sample_delay_us = 500);

float adc_read_rms_v(uint8_t pin,
                     uint16_t sample_count = 256,
                     uint32_t sample_delay_us = 500);

float adc_read_irms(uint8_t pin,
                    float volts_per_amp,
                    uint16_t sample_count = 256,
                    uint32_t sample_delay_us = 500);
