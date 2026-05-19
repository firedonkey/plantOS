#pragma once

#include <DallasTemperature.h>
#include <OneWire.h>

struct WaterTemperatureReading {
  float temperature_c;
  bool valid;
};

class WaterTemperatureSensor {
 public:
  explicit WaterTemperatureSensor(int data_pin);
  void begin();
  WaterTemperatureReading read();

 private:
  OneWire one_wire_;
  DallasTemperature dallas_;
};
