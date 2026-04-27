#include "system/touch_button_manager.h"

#include <Arduino.h>

#include "config.h"

namespace {
constexpr float kBaselineAlpha = 0.08f;
}

TouchButtonManager::TouchButtonManager(
    int pin,
    uint8_t sample_count,
    uint32_t check_interval_ms,
    uint32_t debounce_ms,
    uint32_t short_tap_max_ms,
    uint32_t long_press_ms,
    uint32_t factory_reset_ms,
    uint32_t multi_tap_window_ms,
    int trigger_delta,
    uint32_t raw_log_interval_ms)
    : pin_(pin),
      sample_count_(sample_count == 0 ? 1 : sample_count),
      check_interval_ms_(check_interval_ms),
      debounce_ms_(debounce_ms),
      short_tap_max_ms_(short_tap_max_ms),
      long_press_ms_(long_press_ms),
      factory_reset_ms_(factory_reset_ms),
      multi_tap_window_ms_(multi_tap_window_ms),
      trigger_delta_(trigger_delta),
      raw_log_interval_ms_(raw_log_interval_ms),
      last_check_ms_(0),
      last_debounce_change_ms_(0),
      press_started_ms_(0),
      last_short_release_ms_(0),
      last_log_ms_(0),
      raw_pressed_(false),
      stable_pressed_(false),
      pending_short_tap_(false),
      long_press_emitted_(false),
      factory_reset_emitted_(false),
      untouched_baseline_(0.0f),
      untouched_min_(UINT16_MAX),
      untouched_max_(0),
      touched_min_(UINT16_MAX),
      touched_max_(0),
      last_raw_value_(0) {}

void TouchButtonManager::begin(uint32_t now_ms) {
#if ENABLE_TOUCH_BUTTON
  pinMode(pin_, INPUT);

  // Build a stable initial untouched baseline.
  uint32_t sum = 0;
  constexpr uint8_t kWarmupReads = 20;
  for (uint8_t i = 0; i < kWarmupReads; ++i) {
    sum += touchRead(pin_);
  }
  untouched_baseline_ = static_cast<float>(sum) / static_cast<float>(kWarmupReads);
  untouched_min_ = static_cast<uint16_t>(untouched_baseline_);
  untouched_max_ = static_cast<uint16_t>(untouched_baseline_);
  last_raw_value_ = static_cast<uint16_t>(untouched_baseline_);
  touched_min_ = UINT16_MAX;
  touched_max_ = 0;

  last_check_ms_ = now_ms;
  last_debounce_change_ms_ = now_ms;
  last_log_ms_ = now_ms;

  Serial.printf(
      "[touch] initialized on GPIO%d baseline=%.1f trigger<=%.1f\n",
      pin_,
      untouched_baseline_,
      untouched_baseline_ - static_cast<float>(trigger_delta_));
#else
  (void)now_ms;
#endif
}

uint16_t TouchButtonManager::read_average_raw() const {
  uint32_t sum = 0;
  for (uint8_t i = 0; i < sample_count_; ++i) {
    sum += touchRead(pin_);
  }
  return static_cast<uint16_t>(sum / sample_count_);
}

void TouchButtonManager::update_calibration_ranges(uint16_t raw, bool pressed) {
  if (pressed) {
    if (raw < touched_min_) {
      touched_min_ = raw;
    }
    if (raw > touched_max_) {
      touched_max_ = raw;
    }
    return;
  }

  if (raw < untouched_min_) {
    untouched_min_ = raw;
  }
  if (raw > untouched_max_) {
    untouched_max_ = raw;
  }
}

void TouchButtonManager::maybe_log_calibration(uint32_t now_ms, uint16_t raw, bool pressed) const {
  if (raw_log_interval_ms_ == 0) {
    return;
  }
  if (now_ms - last_log_ms_ < raw_log_interval_ms_) {
    return;
  }

  Serial.printf(
      "[touch] raw=%u baseline=%.1f trigger<=%.1f pressed=%s untouched[min=%u max=%u] touched[min=%u max=%u]\n",
      raw,
      untouched_baseline_,
      untouched_baseline_ - static_cast<float>(trigger_delta_),
      pressed ? "yes" : "no",
      untouched_min_,
      untouched_max_,
      touched_min_ == UINT16_MAX ? 0 : touched_min_,
      touched_max_);
}

TouchButtonEvent TouchButtonManager::update(uint32_t now_ms) {
#if !ENABLE_TOUCH_BUTTON
  (void)now_ms;
  return TouchButtonEvent::kNone;
#else
  if (now_ms - last_check_ms_ < check_interval_ms_) {
    return TouchButtonEvent::kNone;
  }
  last_check_ms_ = now_ms;

  const uint16_t raw = read_average_raw();
  last_raw_value_ = raw;
  const bool is_pressed = raw <= (untouched_baseline_ - static_cast<float>(trigger_delta_));

  if (!is_pressed) {
    // Track untouched baseline slowly over time.
    untouched_baseline_ =
        ((1.0f - kBaselineAlpha) * untouched_baseline_) + (kBaselineAlpha * static_cast<float>(raw));
  }

  update_calibration_ranges(raw, is_pressed);
  maybe_log_calibration(now_ms, raw, is_pressed);
  if (raw_log_interval_ms_ != 0 && now_ms - last_log_ms_ >= raw_log_interval_ms_) {
    last_log_ms_ = now_ms;
  }

  if (is_pressed != raw_pressed_) {
    raw_pressed_ = is_pressed;
    last_debounce_change_ms_ = now_ms;
  }

  if ((now_ms - last_debounce_change_ms_) >= debounce_ms_ && stable_pressed_ != raw_pressed_) {
    stable_pressed_ = raw_pressed_;
    if (stable_pressed_) {
      press_started_ms_ = now_ms;
      long_press_emitted_ = false;
      factory_reset_emitted_ = false;
    } else {
      const uint32_t press_duration = now_ms - press_started_ms_;
      if (!long_press_emitted_ && !factory_reset_emitted_ && press_duration <= short_tap_max_ms_) {
        if (pending_short_tap_ && (now_ms - last_short_release_ms_) <= multi_tap_window_ms_) {
          pending_short_tap_ = false;
          return TouchButtonEvent::kDoubleTap;
        }
        pending_short_tap_ = true;
        last_short_release_ms_ = now_ms;
      } else {
        pending_short_tap_ = false;
      }
    }
  }

  if (stable_pressed_) {
    const uint32_t pressed_ms = now_ms - press_started_ms_;
    if (!factory_reset_emitted_ && pressed_ms >= factory_reset_ms_) {
      factory_reset_emitted_ = true;
      long_press_emitted_ = true;
      pending_short_tap_ = false;
      return TouchButtonEvent::kFactoryReset;
    }
    if (!long_press_emitted_ && pressed_ms >= long_press_ms_) {
      long_press_emitted_ = true;
      pending_short_tap_ = false;
      return TouchButtonEvent::kLongPress;
    }
  }

  if (pending_short_tap_ && (now_ms - last_short_release_ms_) > multi_tap_window_ms_) {
    pending_short_tap_ = false;
    return TouchButtonEvent::kShortTap;
  }

  return TouchButtonEvent::kNone;
#endif
}

TouchDebugInfo TouchButtonManager::get_debug_info() const {
  return TouchDebugInfo{
      last_raw_value_,
      untouched_baseline_,
      untouched_baseline_ - static_cast<float>(trigger_delta_),
      trigger_delta_,
      raw_pressed_,
      stable_pressed_,
      untouched_min_,
      untouched_max_,
      touched_min_ == UINT16_MAX ? static_cast<uint16_t>(0) : touched_min_,
      touched_max_,
  };
}

void TouchButtonManager::print_calibration_summary() const {
  const TouchDebugInfo debug = get_debug_info();
  Serial.printf(
      "[touch] summary raw=%u baseline=%.1f trigger<=%.1f delta=%d raw_pressed=%s stable=%s "
      "untouched[min=%u max=%u] touched[min=%u max=%u]\n",
      debug.raw_value,
      debug.baseline,
      debug.trigger_threshold,
      debug.trigger_delta,
      debug.raw_pressed ? "yes" : "no",
      debug.stable_pressed ? "yes" : "no",
      debug.untouched_min,
      debug.untouched_max,
      debug.touched_min,
      debug.touched_max);
}
