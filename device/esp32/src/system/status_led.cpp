#include "system/status_led.h"

#include <Arduino.h>

StatusLed::StatusLed(int pin, int on_level, int off_level)
    : pin_(pin),
      on_level_(on_level),
      off_level_(off_level),
      mode_(StatusLedMode::kBooting),
      is_on_(false),
      feedback_until_ms_(0) {}

void StatusLed::begin() {
  pinMode(pin_, OUTPUT);
  apply(false);
}

void StatusLed::set_mode(StatusLedMode mode) {
  mode_ = mode;
}

void StatusLed::signal_user_feedback(uint32_t now_ms) {
  feedback_until_ms_ = now_ms + 600;
}

void StatusLed::apply(bool on) {
  is_on_ = on;
  digitalWrite(pin_, on ? on_level_ : off_level_);
}

void StatusLed::update(uint32_t now_ms) {
  if (feedback_until_ms_ != 0 && now_ms < feedback_until_ms_) {
    apply((now_ms / 75) % 2 == 0);
    return;
  }
  feedback_until_ms_ = 0;

  switch (mode_) {
    case StatusLedMode::kOff:
      apply(false);
      return;
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
