#pragma once

struct MoistureReading {
  int raw_adc;
  float moisture_percent;
  bool valid;
};

class MoistureSensor {
 public:
  MoistureSensor(int adc_pin, int sample_count, int sample_delay_ms);
  void begin();
  MoistureReading read();

 private:
  static float adc_to_percent(int raw_adc);

  int adc_pin_;
  int sample_count_;
  int sample_delay_ms_;
};
