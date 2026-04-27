#pragma once

struct Dht22Reading {
  float temperature_c;
  float humidity_percent;
  bool valid;
};

class Dht22Sensor {
 public:
  explicit Dht22Sensor(int data_pin);
  void begin();
  Dht22Reading read();

 private:
  int data_pin_;
};
