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
    : actuator_(pin, on_level, off_level),
      pin_(pin),
      on_level_(on_level),
      off_level_(off_level),
      intensity_control_enabled_(intensity_control_enabled),
      intensity_percent_(0) {}

void LightController::begin() {
  actuator_.begin();
  intensity_percent_ = 0;
  if (intensity_control_enabled_) {
    analogWrite(pin_, pwm_duty_for_percent(0));
  }
}

void LightController::set_on(bool on) {
  if (intensity_control_enabled_) {
    set_intensity_percent(on ? 100 : 0);
    return;
  }
  intensity_percent_ = on ? 100 : 0;
  actuator_.set_on(on);
}

bool LightController::set_intensity_percent(int percent) {
  if (!intensity_control_enabled_) {
    return false;
  }
  intensity_percent_ = clamp_percent(percent);
  actuator_.set_on(intensity_percent_ > 0);
  analogWrite(pin_, pwm_duty_for_percent(intensity_percent_));
  return true;
}

void LightController::toggle() {
  actuator_.toggle();
  intensity_percent_ = actuator_.is_on() ? 100 : 0;
  if (intensity_control_enabled_) {
    analogWrite(pin_, pwm_duty_for_percent(intensity_percent_));
  }
}

bool LightController::is_on() const {
  return actuator_.is_on();
}

int LightController::intensity_percent() const {
  return intensity_percent_;
}

bool LightController::supports_intensity_control() const {
  return intensity_control_enabled_;
}

int LightController::pwm_duty_for_percent(int percent) const {
  const int bounded = clamp_percent(percent);
  int duty = (bounded * 255) / 100;
  if (on_level_ == LOW && off_level_ == HIGH) {
    duty = 255 - duty;
  }
  return duty;
}
