#include "sensors/water_level_sensor.h"

#include <Arduino.h>

WaterLevelSensor::WaterLevelSensor(
    int touch_pin,
    int sample_count,
    int sample_delay_ms,
    int present_raw_threshold)
    : touch_pin_(touch_pin),
      sample_count_(sample_count > 0 ? sample_count : 1),
      sample_delay_ms_(sample_delay_ms > 0 ? sample_delay_ms : 0),
      present_raw_threshold_(present_raw_threshold) {}

void WaterLevelSensor::begin() {}

WaterLevelReading WaterLevelSensor::read() {
  uint64_t total = 0;
  for (int i = 0; i < sample_count_; ++i) {
    total += touchRead(touch_pin_);
    if (sample_delay_ms_ > 0 && i < sample_count_ - 1) {
      delay(sample_delay_ms_);
    }
  }

  WaterLevelReading result{};
  result.raw = static_cast<int>(total / static_cast<uint64_t>(sample_count_));
  result.state = state_for_raw(result.raw);
  result.valid = true;
  return result;
}

String WaterLevelSensor::state_for_raw(int raw) const {
  if (present_raw_threshold_ < 0) {
    return "unknown";
  }
  return raw <= present_raw_threshold_ ? "ok" : "low";
}
