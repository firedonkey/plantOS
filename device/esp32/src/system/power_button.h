#pragma once

#include <stdint.h>

enum class PowerButtonEvent {
  kNone = 0,
  kShortPress,
  kLongPress,
};

class PowerButton {
 public:
  PowerButton(
      int pin,
      int active_level,
      uint32_t debounce_ms,
      uint32_t long_press_ms);

  void begin();
  PowerButtonEvent update(uint32_t now_ms);
  bool is_pressed() const;

 private:
  bool read_pressed() const;

  int pin_;
  int active_level_;
  uint32_t debounce_ms_;
  uint32_t long_press_ms_;

  bool last_raw_pressed_;
  bool stable_pressed_;
  bool long_press_fired_;
  uint32_t last_change_ms_;
  uint32_t pressed_since_ms_;
};

