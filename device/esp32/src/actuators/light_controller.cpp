#include "actuators/light_controller.h"

#include <Arduino.h>

namespace {
int clamp_percent(int percent) {
  if (percent < 0) {
    return 0;
  }
  if (percent > 100) {
    return 100;
  }
  return percent;
}
}

LightController::LightController(int pin, int on_level, int off_level, bool intensity_control_enabled)
    : LightController(pin, -1, on_level, off_level, intensity_control_enabled) {}

LightController::LightController(
    int primary_pin,
    int secondary_pin,
    int on_level,
    int off_level,
    bool intensity_control_enabled)
    : primary_pin_(primary_pin),
      secondary_pin_(secondary_pin),
      on_level_(on_level),
      off_level_(off_level),
      intensity_control_enabled_(intensity_control_enabled),
      intensity_percent_(0),
      is_on_(false) {}

void LightController::begin() {
  write_digital_all(off_level_);
  pinMode(primary_pin_, OUTPUT);
  if (has_secondary_channel()) {
    pinMode(secondary_pin_, OUTPUT);
  }
  write_digital_all(off_level_);
  intensity_percent_ = 0;
  is_on_ = false;
  if (intensity_control_enabled_) {
    write_pwm_all(pwm_duty_for_percent(0));
  }
}

void LightController::set_on(bool on) {
  if (intensity_control_enabled_) {
    set_intensity_percent(on ? 100 : 0);
    return;
  }
  intensity_percent_ = on ? 100 : 0;
  is_on_ = on;
  write_digital_all(is_on_ ? on_level_ : off_level_);
}

bool LightController::set_intensity_percent(int percent) {
  if (!intensity_control_enabled_) {
    return false;
  }
  intensity_percent_ = clamp_percent(percent);
  is_on_ = intensity_percent_ > 0;
  write_pwm_all(pwm_duty_for_percent(intensity_percent_));
  return true;
}

void LightController::toggle() {
  is_on_ = !is_on_;
  intensity_percent_ = is_on_ ? 100 : 0;
  if (intensity_control_enabled_) {
    write_pwm_all(pwm_duty_for_percent(intensity_percent_));
  } else {
    write_digital_all(is_on_ ? on_level_ : off_level_);
  }
}

bool LightController::is_on() const {
  return is_on_;
}

int LightController::intensity_percent() const {
  return intensity_percent_;
}

bool LightController::supports_intensity_control() const {
  return intensity_control_enabled_;
}

bool LightController::has_secondary_channel() const {
  return secondary_pin_ >= 0;
}

int LightController::primary_pin() const {
  return primary_pin_;
}

int LightController::secondary_pin() const {
  return secondary_pin_;
}

int LightController::pwm_duty_for_percent(int percent) const {
  const int bounded = clamp_percent(percent);
  int duty = (bounded * 255) / 100;
  if (on_level_ == LOW && off_level_ == HIGH) {
    duty = 255 - duty;
  }
  return duty;
}

void LightController::write_digital_all(int level) {
  digitalWrite(primary_pin_, level);
  if (has_secondary_channel()) {
    digitalWrite(secondary_pin_, level);
  }
}

void LightController::write_pwm_all(int duty) {
  analogWrite(primary_pin_, duty);
  if (has_secondary_channel()) {
    analogWrite(secondary_pin_, duty);
  }
}
