#include <Arduino.h>
#include <esp_sleep.h>

#include "actuators/light_controller.h"
#include "actuators/pump_controller.h"
#include "config.h"
#include "sensors/dht22_sensor.h"
#include "sensors/moisture_sensor.h"
#include "system/power_button.h"
#include "system/status_led.h"
#include "system/touch_button_manager.h"

namespace {
Dht22Sensor g_dht22(PIN_DHT22_DATA);
MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
LightController g_light(
    PIN_LIGHT_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PumpController g_pump(PIN_PUMP_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PowerButton g_power_button(
    PIN_POWER_BUTTON,
    POWER_BUTTON_ACTIVE_LEVEL,
    POWER_BUTTON_DEBOUNCE_MS,
    POWER_BUTTON_LONG_PRESS_MS);
StatusLed g_status_led(PIN_STATUS_LED, STATUS_LED_ON_LEVEL, STATUS_LED_OFF_LEVEL);
#if ENABLE_TOUCH_BUTTON
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
    TOUCH_RAW_LOG_INTERVAL_MS);
#endif
unsigned long g_last_dht22_read_ms = 0;
unsigned long g_last_provisioning_heartbeat_ms = 0;
bool g_provisioning_mode = false;
}

void enter_deep_sleep() {
  Serial.println("[power] entering deep sleep (press power button to wake)");
  g_status_led.set_mode(StatusLedMode::kSleepPending);

  const int wake_level = (POWER_BUTTON_ACTIVE_LEVEL == LOW) ? 0 : 1;
  esp_sleep_enable_ext0_wakeup(static_cast<gpio_num_t>(PIN_POWER_BUTTON), wake_level);

  for (int i = 0; i < 20; ++i) {
    g_status_led.update(millis());
    delay(20);
  }

  Serial.flush();
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab v2 Phase 1: DHT22 Bring-up ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("DHT22 pin: GPIO%d\n", PIN_DHT22_DATA);
  Serial.printf("Moisture ADC pin: GPIO%d\n", PIN_SOIL_MOISTURE_ADC);
  Serial.printf("Light gate pin: GPIO%d\n", PIN_LIGHT_MOSFET_GATE);
  Serial.printf("Pump gate pin: GPIO%d\n", PIN_PUMP_MOSFET_GATE);
  Serial.printf("Power button pin: GPIO%d\n", PIN_POWER_BUTTON);
  Serial.printf("Status LED pin: GPIO%d\n", PIN_STATUS_LED);
#if ENABLE_TOUCH_BUTTON
  Serial.printf("Touch button pin: GPIO%d\n", PIN_TOUCH_BUTTON);
#endif
  Serial.println("[power] short press: deep sleep");
  Serial.println("[power] long press: provisioning mode (placeholder)");

  g_status_led.begin();
  g_status_led.set_mode(StatusLedMode::kBooting);
  g_power_button.begin();
  g_dht22.begin();
  g_moisture.begin();
  g_light.begin();
  g_pump.begin();
#if ENABLE_TOUCH_BUTTON
  g_touch_button.begin(millis());
  Serial.println("[touch] short tap: toggle light");
  Serial.println("[touch] double tap: trigger camera capture test");
  Serial.println("[touch] long press 5s: status event only");
  Serial.println("[touch] long press 10s: status event only");
#endif
  Serial.println("[dht22] sensor initialized");
  Serial.println("[moisture] sensor initialized");
  Serial.println("[light] initialized OFF");
  Serial.println("[pump] initialized OFF");

  const esp_sleep_wakeup_cause_t wake_cause = esp_sleep_get_wakeup_cause();
  if (wake_cause == ESP_SLEEP_WAKEUP_EXT0) {
    Serial.println("[power] woke from deep sleep by power button");
  } else {
    Serial.printf("[power] wake cause: %d\n", static_cast<int>(wake_cause));
  }

  g_status_led.set_mode(StatusLedMode::kNormal);
}

void loop() {
  const unsigned long now = millis();
  g_status_led.update(now);
  g_pump.update();

#if ENABLE_TOUCH_BUTTON
  const TouchButtonEvent touch_event = g_touch_button.update(now);
  switch (touch_event) {
    case TouchButtonEvent::kShortTap:
      g_light.toggle();
      Serial.printf("[touch] short tap -> light %s\n", g_light.is_on() ? "on" : "off");
      break;
    case TouchButtonEvent::kDoubleTap:
      Serial.println("[touch] double tap -> camera capture requested");
      break;
    case TouchButtonEvent::kLongPress:
      Serial.println("[touch] long press detected (status-only test mode)");
      break;
    case TouchButtonEvent::kFactoryReset:
      Serial.println("[touch] very long press detected (status-only test mode)");
      break;
    case TouchButtonEvent::kNone:
    default:
      break;
  }
#endif

  const PowerButtonEvent button_event = g_power_button.update(now);
  if (button_event == PowerButtonEvent::kShortPress) {
    enter_deep_sleep();
    return;
  }
  if (button_event == PowerButtonEvent::kLongPress) {
    g_provisioning_mode = true;
    g_status_led.set_mode(StatusLedMode::kProvisioning);
    Serial.println("[power] provisioning mode requested");
    Serial.println("[provisioning] placeholder mode only in Phase 1");
  }

  if (g_provisioning_mode) {
    if (now - g_last_provisioning_heartbeat_ms >= 5000) {
      g_last_provisioning_heartbeat_ms = now;
      Serial.println("[provisioning] waiting (Wi-Fi + provisioning flow not implemented yet)");
    }
    return;
  }

  if (now - g_last_dht22_read_ms < DHT22_READ_INTERVAL_MS) {
    return;
  }
  g_last_dht22_read_ms = now;

  const Dht22Reading reading = g_dht22.read();
  const MoistureReading moisture = g_moisture.read();

  if (!reading.valid) {
    Serial.println("[dht22] read failed (NaN)");
  } else {
    Serial.printf(
        "[dht22] temp_c=%.1f humidity=%.1f%%\n",
        reading.temperature_c,
        reading.humidity_percent);
  }

  if (!moisture.valid) {
    Serial.println("[moisture] read failed");
  } else {
    Serial.printf(
        "[moisture] raw=%d percent=%.1f%%\n",
        moisture.raw_adc,
        moisture.moisture_percent);
  }

  Serial.printf(
      "[actuators] light=%s pump=%s\n",
      g_light.is_on() ? "on" : "off",
      g_pump.is_on() ? "on" : "off");
}
