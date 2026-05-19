#pragma once

#include <Arduino.h>

struct WaterLevelReading {
  int raw;
  String state;
  bool valid;
};

class WaterLevelSensor {
 public:
  WaterLevelSensor(int touch_pin, int sample_count, int sample_delay_ms, int present_raw_threshold);
  void begin();
  WaterLevelReading read();

 private:
  String state_for_raw(int raw) const;

  int touch_pin_;
  int sample_count_;
  int sample_delay_ms_;
  int present_raw_threshold_;
};
