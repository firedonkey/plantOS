#include <Arduino.h>

#include "actuators/light_controller.h"
#include "config.h"
#include "system/touch_button_manager.h"

namespace {
LightController g_light(PIN_LIGHT_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
TouchButtonManager g_touch_button(
    PIN_TOUCH_BUTTON,
    TOUCH_SAMPLE_COUNT,
    TOUCH_CHECK_INTERVAL_MS,
    TOUCH_DEBOUNCE_MS,
    TOUCH_SHORT_TAP_MAX_MS,
    TOUCH_LONG_PRESS_MS,
    TOUCH_FACTORY_RESET_MS,
    TOUCH_MULTI_TAP_WINDOW_MS,
    TOUCH_TRIGGER_DELTA,
    0);  // No periodic raw logging for clean event-only test output.
bool g_verbose_debug = true;
unsigned long g_last_verbose_log_ms = 0;
constexpr unsigned long kVerboseIntervalMs = 250;
}

void print_verbose_help() {
  Serial.println("[touch-test] serial commands:");
  Serial.println("  v  toggle verbose raw debug stream");
  Serial.println("  s  print one calibration summary line");
  Serial.println("  h  print this help");
}

void maybe_print_verbose_debug(unsigned long now_ms) {
  if (!g_verbose_debug) {
    return;
  }
  if (now_ms - g_last_verbose_log_ms < kVerboseIntervalMs) {
    return;
  }
  g_last_verbose_log_ms = now_ms;
  const TouchDebugInfo debug = g_touch_button.get_debug_info();
  Serial.printf(
      "[touch-debug] raw=%u baseline=%.1f trigger<=%.1f delta=%d raw=%s stable=%s "
      "untouched[%u..%u] touched[%u..%u]\n",
      debug.raw_value,
      debug.baseline,
      debug.trigger_threshold,
      debug.trigger_delta,
      debug.raw_pressed ? "pressed" : "open",
      debug.stable_pressed ? "pressed" : "open",
      debug.untouched_min,
      debug.untouched_max,
      debug.touched_min,
      debug.touched_max);
}

void handle_serial_commands() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == 'v' || ch == 'V') {
      g_verbose_debug = !g_verbose_debug;
      Serial.printf("[touch-test] verbose debug %s\n", g_verbose_debug ? "ON" : "OFF");
      continue;
    }
    if (ch == 's' || ch == 'S') {
      g_touch_button.print_calibration_summary();
      continue;
    }
    if (ch == 'h' || ch == 'H' || ch == '?') {
      print_verbose_help();
      continue;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(800);

  Serial.println();
  Serial.println("=== PlantLab Touch Button Test ===");
#if ENABLE_TOUCH_BUTTON
  Serial.printf("[touch-test] touch pin: GPIO%d\n", PIN_TOUCH_BUTTON);
  Serial.printf("[touch-test] light pin: GPIO%d\n", PIN_LIGHT_MOSFET_GATE);
  Serial.println("[touch-test] short tap: toggle light");
  Serial.println("[touch-test] double tap: camera capture request log");
  Serial.println("[touch-test] long press 5s: status-only log");
  Serial.println("[touch-test] very long press 10s: status-only log");
  Serial.println("[touch-test] verbose raw debug: ON");

  g_light.begin();
  g_touch_button.begin(millis());
  print_verbose_help();
  Serial.println("[touch-test] ready");
#else
  Serial.println("[touch-test] ENABLE_TOUCH_BUTTON is 0 in config.h");
#endif
}

void loop() {
#if ENABLE_TOUCH_BUTTON
  const unsigned long now = millis();
  const TouchButtonEvent touch_event = g_touch_button.update(now);
  switch (touch_event) {
    case TouchButtonEvent::kShortTap:
      g_light.toggle();
      Serial.printf("[touch-test] short tap -> light %s\n", g_light.is_on() ? "on" : "off");
      break;
    case TouchButtonEvent::kDoubleTap:
      Serial.println("[touch-test] double tap -> camera capture requested");
      break;
    case TouchButtonEvent::kLongPress:
      Serial.println("[touch-test] long press detected (status-only)");
      break;
    case TouchButtonEvent::kFactoryReset:
      Serial.println("[touch-test] very long press detected (status-only)");
      break;
    case TouchButtonEvent::kNone:
    default:
      break;
  }

  handle_serial_commands();
  maybe_print_verbose_debug(now);
#endif
}
