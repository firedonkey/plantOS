#include "sensors/moisture_sensor.h"

#include <Arduino.h>

#include "config.h"

namespace {
float clamp_percent(float value) {
  if (value < 0.0f) {
    return 0.0f;
  }
  if (value > 100.0f) {
    return 100.0f;
  }
  return value;
}
}  // namespace

MoistureSensor::MoistureSensor(int adc_pin, int sample_count, int sample_delay_ms)
    : adc_pin_(adc_pin),
      sample_count_(sample_count > 0 ? sample_count : 1),
      sample_delay_ms_(sample_delay_ms > 0 ? sample_delay_ms : 0) {}

void MoistureSensor::begin() {
  pinMode(adc_pin_, INPUT);
  analogReadResolution(12);  // 0..4095
}

MoistureReading MoistureSensor::read() {
  long total = 0;
  for (int i = 0; i < sample_count_; ++i) {
    total += analogRead(adc_pin_);
    if (sample_delay_ms_ > 0 && i < sample_count_ - 1) {
      delay(sample_delay_ms_);
    }
  }

  const int average_raw = static_cast<int>(total / sample_count_);

  MoistureReading result{};
  result.raw_adc = average_raw;
  result.moisture_percent = adc_to_percent(average_raw);
  result.valid = true;
  return result;
}

float MoistureSensor::adc_to_percent(int raw_adc) {
  const float span = static_cast<float>(MOISTURE_RAW_DRY - MOISTURE_RAW_WET);
  if (span == 0.0f) {
    return 0.0f;
  }
  const float normalized = static_cast<float>(MOISTURE_RAW_DRY - raw_adc) / span;
  return clamp_percent(normalized * 100.0f);
}
