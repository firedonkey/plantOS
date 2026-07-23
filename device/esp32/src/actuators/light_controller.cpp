#include "actuators/light_controller.h"

#include <Arduino.h>

namespace {
constexpr int kDefaultPwmFrequencyHz = 1000;

int clamp_percent(int percent) {
  if (percent < 0) {
    return 0;
  }
  if (percent > 100) {
    return 100;
  }
  return percent;
}

int valid_pwm_frequency_hz(int frequency_hz) {
  return frequency_hz > 0 ? frequency_hz : kDefaultPwmFrequencyHz;
}
}

LightController::LightController(
    int pin,
    int on_level,
    int off_level,
    bool intensity_control_enabled,
    int pwm_frequency_hz)
    : LightController(pin, -1, on_level, off_level, intensity_control_enabled, pwm_frequency_hz) {}

LightController::LightController(
    int primary_pin,
    int secondary_pin,
    int on_level,
    int off_level,
    bool intensity_control_enabled,
    int pwm_frequency_hz)
    : primary_pin_(primary_pin),
      secondary_pin_(secondary_pin),
      on_level_(on_level),
      off_level_(off_level),
      intensity_control_enabled_(intensity_control_enabled),
      pwm_frequency_hz_(valid_pwm_frequency_hz(pwm_frequency_hz)),
      intensity_percent_(0),
      primary_intensity_percent_(0),
      secondary_intensity_percent_(0),
      is_on_(false) {}

void LightController::begin() {
  write_digital_all(off_level_);
  pinMode(primary_pin_, OUTPUT);
  if (has_secondary_channel()) {
    pinMode(secondary_pin_, OUTPUT);
  }
  write_digital_all(off_level_);
  intensity_percent_ = 0;
  primary_intensity_percent_ = 0;
  secondary_intensity_percent_ = 0;
  is_on_ = false;
  if (intensity_control_enabled_) {
    analogWriteFrequency(pwm_frequency_hz_);
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
  const int bounded = clamp_percent(percent);
  primary_intensity_percent_ = bounded;
  secondary_intensity_percent_ = has_secondary_channel() ? bounded : 0;
  sync_combined_state();
  write_pwm_all(pwm_duty_for_percent(bounded));
  return true;
}

bool LightController::set_primary_intensity_percent(int percent) {
  if (!intensity_control_enabled_) {
    return false;
  }
  primary_intensity_percent_ = clamp_percent(percent);
  sync_combined_state();
  write_pwm_primary(pwm_duty_for_percent(primary_intensity_percent_));
  return true;
}

bool LightController::set_secondary_intensity_percent(int percent) {
  if (!intensity_control_enabled_ || !has_secondary_channel()) {
    return false;
  }
  secondary_intensity_percent_ = clamp_percent(percent);
  sync_combined_state();
  write_pwm_secondary(pwm_duty_for_percent(secondary_intensity_percent_));
  return true;
}

void LightController::toggle() {
  is_on_ = !is_on_;
  primary_intensity_percent_ = is_on_ ? 100 : 0;
  secondary_intensity_percent_ = has_secondary_channel() ? primary_intensity_percent_ : 0;
  sync_combined_state();
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

int LightController::primary_intensity_percent() const {
  return primary_intensity_percent_;
}

int LightController::secondary_intensity_percent() const {
  return secondary_intensity_percent_;
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

int LightController::pwm_frequency_hz() const {
  return pwm_frequency_hz_;
}

void LightController::sync_combined_state() {
  intensity_percent_ = has_secondary_channel()
                           ? (primary_intensity_percent_ > secondary_intensity_percent_
                                  ? primary_intensity_percent_
                                  : secondary_intensity_percent_)
                           : primary_intensity_percent_;
  is_on_ = intensity_percent_ > 0;
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

void LightController::write_pwm_primary(int duty) {
  analogWrite(primary_pin_, duty);
}

void LightController::write_pwm_secondary(int duty) {
  if (has_secondary_channel()) {
    analogWrite(secondary_pin_, duty);
  }
}
