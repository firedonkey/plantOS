#include "system/status_led.h"

#include <Arduino.h>

StatusLed::StatusLed(int pin, int on_level, int off_level)
    : pin_(pin),
      on_level_(on_level),
      off_level_(off_level),
      mode_(StatusLedMode::kBooting),
      is_on_(false) {}

void StatusLed::begin() {
  pinMode(pin_, OUTPUT);
  apply(false);
}

void StatusLed::set_mode(StatusLedMode mode) {
  mode_ = mode;
}

void StatusLed::apply(bool on) {
  is_on_ = on;
  digitalWrite(pin_, on ? on_level_ : off_level_);
}

void StatusLed::update(uint32_t now_ms) {
  switch (mode_) {
    case StatusLedMode::kNormal:
      apply(true);
      return;
    case StatusLedMode::kProvisioning:
      apply((now_ms / 200) % 2 == 0);
      return;
    case StatusLedMode::kSleepPending:
      apply((now_ms / 80) % 2 == 0);
      return;
    case StatusLedMode::kBooting:
    default:
      apply((now_ms / 400) % 2 == 0);
      return;
  }
}

