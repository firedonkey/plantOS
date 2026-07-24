#pragma once

#include <stdint.h>

struct I2cEnvironmentReading {
  float aht20_temperature_c = 0.0f;
  float aht20_humidity_percent = 0.0f;
  float mcp9808_temperature_c = 0.0f;
  bool aht20_valid = false;
  bool mcp9808_valid = false;
};

class I2cEnvironmentSensors {
 public:
  I2cEnvironmentSensors(int sda_pin, int scl_pin);

  void begin();
  I2cEnvironmentReading read();

  bool aht20_present() const;
  bool mcp9808_present() const;
  int sda_pin() const;
  int scl_pin() const;

 private:
  bool probe_address(unsigned char address);
  bool initialize_aht20();
  bool read_aht20(float* temperature_c, float* humidity_percent);
  bool ensure_mcp9808_present();
  bool read_mcp9808(float* temperature_c);

  int sda_pin_;
  int scl_pin_;
  bool aht20_present_ = false;
  bool mcp9808_present_ = false;
  uint8_t mcp9808_read_failures_ = 0;
};
