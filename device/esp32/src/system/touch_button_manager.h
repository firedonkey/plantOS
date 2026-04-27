#pragma once

#include <stdint.h>

enum class TouchButtonEvent {
  kNone = 0,
  kShortTap,
  kDoubleTap,
  kLongPress,
  kFactoryReset,
};

struct TouchDebugInfo {
  uint16_t raw_value;
  float baseline;
  float trigger_threshold;
  int trigger_delta;
  bool raw_pressed;
  bool stable_pressed;
  uint16_t untouched_min;
  uint16_t untouched_max;
  uint16_t touched_min;
  uint16_t touched_max;
};

class TouchButtonManager {
 public:
  TouchButtonManager(
      int pin,
      uint8_t sample_count,
      uint32_t check_interval_ms,
      uint32_t debounce_ms,
      uint32_t short_tap_max_ms,
      uint32_t long_press_ms,
      uint32_t factory_reset_ms,
      uint32_t multi_tap_window_ms,
      int trigger_delta,
      uint32_t raw_log_interval_ms);

  void begin(uint32_t now_ms);
  TouchButtonEvent update(uint32_t now_ms);
  TouchDebugInfo get_debug_info() const;
  void print_calibration_summary() const;

 private:
  uint16_t read_average_raw() const;
  void update_calibration_ranges(uint16_t raw, bool pressed);
  void maybe_log_calibration(uint32_t now_ms, uint16_t raw, bool pressed) const;

  int pin_;
  uint8_t sample_count_;
  uint32_t check_interval_ms_;
  uint32_t debounce_ms_;
  uint32_t short_tap_max_ms_;
  uint32_t long_press_ms_;
  uint32_t factory_reset_ms_;
  uint32_t multi_tap_window_ms_;
  int trigger_delta_;
  uint32_t raw_log_interval_ms_;

  uint32_t last_check_ms_;
  uint32_t last_debounce_change_ms_;
  uint32_t press_started_ms_;
  uint32_t last_short_release_ms_;
  uint32_t last_log_ms_;

  bool raw_pressed_;
  bool stable_pressed_;
  bool pending_short_tap_;
  bool long_press_emitted_;
  bool factory_reset_emitted_;

  float untouched_baseline_;
  uint16_t untouched_min_;
  uint16_t untouched_max_;
  uint16_t touched_min_;
  uint16_t touched_max_;
  uint16_t last_raw_value_;
};
