#include "dht22_sensor.h"

#include <DHTesp.h>

namespace {
DHTesp g_dht;
}  // namespace

Dht22Sensor::Dht22Sensor(int data_pin) : data_pin_(data_pin) {}

void Dht22Sensor::begin() {
  g_dht.setup(data_pin_, DHTesp::DHT22);
}

Dht22Reading Dht22Sensor::read() {
  const TempAndHumidity values = g_dht.getTempAndHumidity();

  Dht22Reading result{};
  result.temperature_c = values.temperature;
  result.humidity_percent = values.humidity;
  result.valid = !isnan(result.temperature_c) && !isnan(result.humidity_percent);
  return result;
}
