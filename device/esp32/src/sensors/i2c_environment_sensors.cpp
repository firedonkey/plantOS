#include "sensors/i2c_environment_sensors.h"

#include <Arduino.h>
#include <Wire.h>

namespace {
constexpr uint8_t kAht20Address = 0x38;
constexpr uint8_t kAht20InitCommand = 0xBE;
constexpr uint8_t kAht20MeasureCommand = 0xAC;
constexpr uint8_t kAht20StatusBusyMask = 0x80;
constexpr uint8_t kAht20StatusCalibratedMask = 0x08;
constexpr uint8_t kMcp9808Address = 0x18;
constexpr uint8_t kMcp9808TemperatureRegister = 0x05;
constexpr uint8_t kMcp9808MaxReadFailuresBeforeProbe = 3;
constexpr uint32_t kI2cClockHz = 100000UL;
constexpr uint16_t kI2cTimeoutMs = 80;

bool write_command(uint8_t address, const uint8_t* bytes, size_t length) {
  Wire.beginTransmission(address);
  for (size_t index = 0; index < length; ++index) {
    Wire.write(bytes[index]);
  }
  return Wire.endTransmission() == 0;
}
}  // namespace

I2cEnvironmentSensors::I2cEnvironmentSensors(int sda_pin, int scl_pin)
    : sda_pin_(sda_pin), scl_pin_(scl_pin) {}

void I2cEnvironmentSensors::begin() {
  Wire.begin(sda_pin_, scl_pin_);
  Wire.setClock(kI2cClockHz);
  Wire.setTimeOut(kI2cTimeoutMs);

  aht20_present_ = probe_address(kAht20Address);
  if (aht20_present_) {
    aht20_present_ = initialize_aht20();
  }
  mcp9808_present_ = probe_address(kMcp9808Address);
}

I2cEnvironmentReading I2cEnvironmentSensors::read() {
  I2cEnvironmentReading reading{};
  reading.aht20_valid = read_aht20(&reading.aht20_temperature_c, &reading.aht20_humidity_percent);
  reading.mcp9808_valid = read_mcp9808(&reading.mcp9808_temperature_c);
  return reading;
}

bool I2cEnvironmentSensors::aht20_present() const {
  return aht20_present_;
}

bool I2cEnvironmentSensors::mcp9808_present() const {
  return mcp9808_present_;
}

int I2cEnvironmentSensors::sda_pin() const {
  return sda_pin_;
}

int I2cEnvironmentSensors::scl_pin() const {
  return scl_pin_;
}

bool I2cEnvironmentSensors::probe_address(unsigned char address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

bool I2cEnvironmentSensors::initialize_aht20() {
  uint8_t command[] = {kAht20InitCommand, 0x08, 0x00};
  if (!write_command(kAht20Address, command, sizeof(command))) {
    return false;
  }
  delay(10);
  const int bytes_read = Wire.requestFrom(static_cast<int>(kAht20Address), 1);
  if (bytes_read != 1) {
    return true;
  }
  const uint8_t status = Wire.read();
  return (status & kAht20StatusCalibratedMask) != 0;
}

bool I2cEnvironmentSensors::read_aht20(float* temperature_c, float* humidity_percent) {
  if (!aht20_present_ || temperature_c == nullptr || humidity_percent == nullptr) {
    return false;
  }

  uint8_t command[] = {kAht20MeasureCommand, 0x33, 0x00};
  if (!write_command(kAht20Address, command, sizeof(command))) {
    return false;
  }
  delay(80);

  const int bytes_read = Wire.requestFrom(static_cast<int>(kAht20Address), 6);
  if (bytes_read != 6) {
    while (Wire.available() > 0) {
      Wire.read();
    }
    return false;
  }

  uint8_t data[6]{};
  for (uint8_t index = 0; index < 6; ++index) {
    data[index] = Wire.read();
  }
  if ((data[0] & kAht20StatusBusyMask) != 0) {
    return false;
  }

  const uint32_t raw_humidity =
      (static_cast<uint32_t>(data[1]) << 12) |
      (static_cast<uint32_t>(data[2]) << 4) |
      (static_cast<uint32_t>(data[3]) >> 4);
  const uint32_t raw_temperature =
      ((static_cast<uint32_t>(data[3]) & 0x0F) << 16) |
      (static_cast<uint32_t>(data[4]) << 8) |
      static_cast<uint32_t>(data[5]);

  *humidity_percent = (static_cast<float>(raw_humidity) * 100.0f) / 1048576.0f;
  *temperature_c = (static_cast<float>(raw_temperature) * 200.0f) / 1048576.0f - 50.0f;
  return *humidity_percent >= 0.0f && *humidity_percent <= 100.0f &&
         *temperature_c > -40.0f && *temperature_c < 125.0f;
}

bool I2cEnvironmentSensors::ensure_mcp9808_present() {
  if (mcp9808_present_) {
    return true;
  }
  mcp9808_present_ = probe_address(kMcp9808Address);
  if (mcp9808_present_) {
    mcp9808_read_failures_ = 0;
    Serial.println("[mcp9808] detected at I2C address 0x18");
  }
  return mcp9808_present_;
}

bool I2cEnvironmentSensors::read_mcp9808(float* temperature_c) {
  if (temperature_c == nullptr || !ensure_mcp9808_present()) {
    return false;
  }

  Wire.beginTransmission(kMcp9808Address);
  Wire.write(kMcp9808TemperatureRegister);
  if (Wire.endTransmission(false) != 0) {
    ++mcp9808_read_failures_;
    if (mcp9808_read_failures_ >= kMcp9808MaxReadFailuresBeforeProbe) {
      mcp9808_present_ = probe_address(kMcp9808Address);
      mcp9808_read_failures_ = mcp9808_present_ ? 0 : kMcp9808MaxReadFailuresBeforeProbe;
    }
    return false;
  }
  const int bytes_read = Wire.requestFrom(static_cast<int>(kMcp9808Address), 2);
  if (bytes_read != 2) {
    while (Wire.available() > 0) {
      Wire.read();
    }
    ++mcp9808_read_failures_;
    if (mcp9808_read_failures_ >= kMcp9808MaxReadFailuresBeforeProbe) {
      mcp9808_present_ = probe_address(kMcp9808Address);
      mcp9808_read_failures_ = mcp9808_present_ ? 0 : kMcp9808MaxReadFailuresBeforeProbe;
    }
    return false;
  }

  const uint16_t raw = (static_cast<uint16_t>(Wire.read()) << 8) | static_cast<uint16_t>(Wire.read());
  float value = static_cast<float>(raw & 0x0FFF) * 0.0625f;
  if ((raw & 0x1000) != 0) {
    value -= 256.0f;
  }
  *temperature_c = value;
  const bool valid = value > -40.0f && value < 125.0f;
  if (valid) {
    mcp9808_read_failures_ = 0;
  } else {
    ++mcp9808_read_failures_;
  }
  return valid;
}
