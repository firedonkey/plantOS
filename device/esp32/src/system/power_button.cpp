#include "system/power_button.h"

#include <Arduino.h>

PowerButton::PowerButton(
    int pin,
    int active_level,
    uint32_t debounce_ms,
    uint32_t long_press_ms)
    : pin_(pin),
      active_level_(active_level),
      debounce_ms_(debounce_ms),
      long_press_ms_(long_press_ms),
      last_raw_pressed_(false),
      stable_pressed_(false),
      long_press_fired_(false),
      last_change_ms_(0),
      pressed_since_ms_(0) {}

void PowerButton::begin() {
  pinMode(pin_, INPUT_PULLUP);
  const bool now_pressed = read_pressed();
  last_raw_pressed_ = now_pressed;
  stable_pressed_ = now_pressed;
  last_change_ms_ = millis();
  pressed_since_ms_ = now_pressed ? last_change_ms_ : 0;
  long_press_fired_ = false;
}

bool PowerButton::read_pressed() const {
  return digitalRead(pin_) == active_level_;
}

PowerButtonEvent PowerButton::update(uint32_t now_ms) {
  const bool raw_pressed = read_pressed();
  if (raw_pressed != last_raw_pressed_) {
    last_raw_pressed_ = raw_pressed;
    last_change_ms_ = now_ms;
  }

  if ((now_ms - last_change_ms_) >= debounce_ms_ && raw_pressed != stable_pressed_) {
    stable_pressed_ = raw_pressed;
    if (stable_pressed_) {
      pressed_since_ms_ = now_ms;
      long_press_fired_ = false;
    } else {
      if (!long_press_fired_) {
        return PowerButtonEvent::kShortPress;
      }
      long_press_fired_ = false;
    }
  }

  if (stable_pressed_ && !long_press_fired_) {
    if ((now_ms - pressed_since_ms_) >= long_press_ms_) {
      long_press_fired_ = true;
      return PowerButtonEvent::kLongPress;
    }
  }

  return PowerButtonEvent::kNone;
}

bool PowerButton::is_pressed() const {
  return stable_pressed_;
}

