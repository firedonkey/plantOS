#include "sensors/water_temperature_sensor.h"

#include <Arduino.h>
#include <math.h>

WaterTemperatureSensor::WaterTemperatureSensor(int data_pin)
    : one_wire_(data_pin),
      dallas_(&one_wire_) {}

void WaterTemperatureSensor::begin() {
  dallas_.begin();
}

WaterTemperatureReading WaterTemperatureSensor::read() {
  WaterTemperatureReading result{};
  result.valid = false;

  dallas_.requestTemperatures();
  result.temperature_c = dallas_.getTempCByIndex(0);
  result.valid = !isnan(result.temperature_c) && result.temperature_c != DEVICE_DISCONNECTED_C;
  return result;
}
