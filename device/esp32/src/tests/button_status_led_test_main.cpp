#include <Arduino.h>

#include "config.h"
#include "system/power_button.h"
#include "system/status_led.h"

namespace {
enum class LedState {
  kOff = 0,
  kOn,
  kBlink,
};

PowerButton g_button(
    PIN_POWER_BUTTON,
    POWER_BUTTON_ACTIVE_LEVEL,
    POWER_BUTTON_DEBOUNCE_MS,
    POWER_BUTTON_LONG_PRESS_MS);
StatusLed g_status_led(PIN_STATUS_LED, STATUS_LED_ON_LEVEL, STATUS_LED_OFF_LEVEL);

LedState g_led_state = LedState::kOff;

void apply_led_state() {
  switch (g_led_state) {
    case LedState::kOn:
      g_status_led.set_mode(StatusLedMode::kNormal);
      return;
    case LedState::kBlink:
      g_status_led.set_mode(StatusLedMode::kProvisioning);
      return;
    case LedState::kOff:
    default:
      g_status_led.set_mode(StatusLedMode::kOff);
      return;
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(800);

  Serial.println();
  Serial.println("=== PlantLab Button + Status LED Test ===");
  Serial.printf("[button-led-test] button pin: GPIO%d\n", PIN_POWER_BUTTON);
  Serial.printf("[button-led-test] status led pin: GPIO%d\n", PIN_STATUS_LED);
  Serial.println("[button-led-test] short press: toggle status LED ON / OFF");
  Serial.println("[button-led-test] long press (>5s): status LED BLINK");

  g_status_led.begin();
  g_button.begin();

  g_led_state = LedState::kOff;
  apply_led_state();
  Serial.println("[button-led-test] status LED starts OFF");
  Serial.println("[button-led-test] ready");
}

void loop() {
  const unsigned long now = millis();
  const PowerButtonEvent event = g_button.update(now);

  switch (event) {
    case PowerButtonEvent::kShortPress:
      g_led_state = (g_led_state == LedState::kOn) ? LedState::kOff : LedState::kOn;
      apply_led_state();
      Serial.printf(
          "[button-led-test] short press -> status LED %s\n",
          g_led_state == LedState::kOn ? "ON" : "OFF");
      break;
    case PowerButtonEvent::kLongPress:
      g_led_state = LedState::kBlink;
      apply_led_state();
      Serial.println("[button-led-test] long press -> status LED BLINK");
      break;
    case PowerButtonEvent::kNone:
    default:
      break;
  }

  g_status_led.update(now);
}
