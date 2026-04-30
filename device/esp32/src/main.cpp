#include <Arduino.h>
#include <esp_sleep.h>
#include <WiFi.h>

#include "actuators/light_controller.h"
#include "actuators/pump_controller.h"
#include "config.h"
#include "platform/platform_client.h"
#include "sensors/dht22_sensor.h"
#include "sensors/moisture_sensor.h"
#include "system/power_button.h"
#include "system/status_led.h"
#include "system/touch_button_manager.h"

namespace {
#if ENABLE_TOUCH_BUTTON && (PIN_TOUCH_BUTTON == PIN_POWER_BUTTON)
constexpr bool kSharedUserButton = true;
#else
constexpr bool kSharedUserButton = false;
#endif

Dht22Sensor g_dht22(PIN_DHT22_DATA);
MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
LightController g_growing_light(
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
unsigned long g_last_platform_send_ms = 0;
unsigned long g_last_platform_status_ms = 0;
unsigned long g_last_command_poll_ms = 0;
unsigned long g_last_wifi_attempt_ms = 0;
bool g_provisioning_mode = false;
bool g_wifi_ready = false;
PlatformClient g_platform_client(
    PLANTLAB_PLATFORM_URL,
    PLANTLAB_DEVICE_ID,
    PLANTLAB_DEVICE_TOKEN);
}

bool platform_enabled() {
  return g_platform_client.configured() && String(PLANTLAB_WIFI_SSID).length() > 0;
}

void ensure_wifi_connected(unsigned long now) {
  if (!platform_enabled() || g_provisioning_mode) {
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!g_wifi_ready) {
      g_wifi_ready = true;
      Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    return;
  }

  g_wifi_ready = false;
  if (now - g_last_wifi_attempt_ms < 5000) {
    return;
  }

  g_last_wifi_attempt_ms = now;
  Serial.printf("[wifi] connecting to %s\n", PLANTLAB_WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(PLANTLAB_WIFI_SSID, PLANTLAB_WIFI_PASSWORD);

  const unsigned long started_at = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started_at < PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    g_wifi_ready = true;
    Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[wifi] connect timed out");
    WiFi.disconnect();
  }
}

PlatformReading read_platform_reading() {
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
      "[actuators] growing_light=%s pump=%s\n",
      g_growing_light.is_on() ? "on" : "off",
      g_pump.is_on() ? "on" : "off");

  PlatformReading platform_reading{};
  platform_reading.temperature_c = reading.temperature_c;
  platform_reading.humidity_percent = reading.humidity_percent;
  platform_reading.moisture_percent = moisture.moisture_percent;
  platform_reading.temperature_valid = reading.valid;
  platform_reading.humidity_valid = reading.valid;
  platform_reading.moisture_valid = moisture.valid;
  platform_reading.light_on = g_growing_light.is_on();
  platform_reading.pump_on = g_pump.is_on();
  platform_reading.pump_status = g_pump.is_on() ? "running" : "idle";
  return platform_reading;
}

PlatformStatus platform_status(const String& message) {
  PlatformStatus status{};
  status.light_on = g_growing_light.is_on();
  status.pump_on = g_pump.is_on();
  status.message = message;
  return status;
}

void send_platform_reading(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_platform_send_ms < PLANTLAB_SENSOR_SEND_INTERVAL_MS) {
    return;
  }
  g_last_platform_send_ms = now;

  const PlatformReading reading = read_platform_reading();
  String error;
  if (g_platform_client.send_reading(reading, &error)) {
    Serial.println("[platform] reading sent");
  } else {
    Serial.printf("[platform] reading upload failed: %s\n", error.c_str());
  }
}

void send_platform_status(unsigned long now, const String& message = "online") {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_platform_status_ms < PLANTLAB_STATUS_INTERVAL_MS) {
    return;
  }
  g_last_platform_status_ms = now;

  String error;
  if (!g_platform_client.send_status(platform_status(message), &error)) {
    Serial.printf("[platform] status upload failed: %s\n", error.c_str());
  }
}

void execute_platform_command(const PlatformCommand& command) {
  String message;
  bool success = true;

  if (command.target == "light") {
    if (command.action == "on") {
      g_growing_light.set_on(true);
      message = "growing light turned on";
    } else if (command.action == "off") {
      g_growing_light.set_on(false);
      message = "growing light turned off";
    } else {
      success = false;
      message = "unsupported growing light command";
    }
  } else if (command.target == "pump") {
    if (command.action == "run") {
      const unsigned long seconds =
          command.value.length() > 0 ? static_cast<unsigned long>(command.value.toInt()) : 5UL;
      g_pump.start_for_ms(seconds * 1000UL);
      message = "pump started for " + String(seconds) + " seconds";
    } else if (command.action == "off") {
      g_pump.stop();
      message = "pump turned off";
    } else {
      success = false;
      message = "unsupported pump command";
    }
  } else {
    success = false;
    message = "unsupported command target";
  }

  String status_error;
  g_platform_client.send_status(platform_status(message), &status_error);
  String ack_error;
  if (!g_platform_client.acknowledge_command(
          command.id,
          success ? "completed" : "failed",
          message.c_str(),
          g_growing_light.is_on(),
          g_pump.is_on(),
          &ack_error)) {
    Serial.printf("[platform] command ack failed: %s\n", ack_error.c_str());
  } else {
    Serial.printf("[platform] command %d handled: %s\n", command.id, message.c_str());
  }
}

void poll_platform_commands(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_command_poll_ms < PLANTLAB_COMMAND_POLL_INTERVAL_MS) {
    return;
  }
  g_last_command_poll_ms = now;

  PlatformCommand commands[4]{};
  String error;
  int count = g_platform_client.poll_pending_commands(commands, 4, &error);
  if (count < 0) {
    Serial.printf("[platform] command poll failed: %s\n", error.c_str());
    return;
  }

  for (int i = 0; i < count; ++i) {
    if (!commands[i].valid) {
      continue;
    }
    execute_platform_command(commands[i]);
  }
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
  Serial.printf("Growing light gate pin: GPIO%d\n", PIN_LIGHT_MOSFET_GATE);
  Serial.printf("Pump gate pin: GPIO%d\n", PIN_PUMP_MOSFET_GATE);
  Serial.printf("Power button pin: GPIO%d\n", PIN_POWER_BUTTON);
  Serial.printf("Status LED pin: GPIO%d\n", PIN_STATUS_LED);
#if ENABLE_TOUCH_BUTTON
  Serial.printf("Touch button pin: GPIO%d\n", PIN_TOUCH_BUTTON);
  if (kSharedUserButton) {
    Serial.println("[input] shared user button: power + touch use same GPIO");
  }
#endif
  Serial.println("[power] short press: deep sleep");
  Serial.println("[power] long press: provisioning mode (placeholder)");

  g_status_led.begin();
  g_status_led.set_mode(StatusLedMode::kBooting);
  if (!kSharedUserButton) {
    g_power_button.begin();
  }
  g_dht22.begin();
  g_moisture.begin();
  g_growing_light.begin();
  g_pump.begin();
#if ENABLE_TOUCH_BUTTON
  g_touch_button.begin(millis());
  Serial.println("[touch] short tap: blink status LED");
  Serial.println("[touch] double tap: blink status LED");
  Serial.println("[touch] long press 5s: status LED feedback only");
  Serial.println("[touch] long press 10s: status LED feedback only");
#endif
  Serial.println("[dht22] sensor initialized");
  Serial.println("[moisture] sensor initialized");
  Serial.println("[growing-light] initialized OFF");
  Serial.println("[pump] initialized OFF");
  if (platform_enabled()) {
    Serial.printf("[platform] base_url: %s\n", g_platform_client.base_url().c_str());
    Serial.printf("[platform] device_id: %d\n", g_platform_client.device_id());
  } else {
    Serial.println("[platform] disabled (missing Wi-Fi or platform credentials)");
  }

  const esp_sleep_wakeup_cause_t wake_cause = esp_sleep_get_wakeup_cause();
  if (wake_cause == ESP_SLEEP_WAKEUP_EXT0) {
    Serial.println("[power] woke from deep sleep by power button");
  } else {
    Serial.printf("[power] wake cause: %d\n", static_cast<int>(wake_cause));
  }

  g_status_led.set_mode(StatusLedMode::kNormal);
  if (platform_enabled()) {
    ensure_wifi_connected(millis());
  }
}

void loop() {
  const unsigned long now = millis();
  g_status_led.update(now);
  g_pump.update();
  ensure_wifi_connected(now);

#if ENABLE_TOUCH_BUTTON
  const TouchButtonEvent touch_event = g_touch_button.update(now);
  switch (touch_event) {
    case TouchButtonEvent::kShortTap:
      g_status_led.signal_user_feedback(now);
      Serial.println("[touch] short tap -> status LED feedback");
      break;
    case TouchButtonEvent::kDoubleTap:
      g_status_led.signal_user_feedback(now);
      Serial.println("[touch] double tap -> status LED feedback");
      break;
    case TouchButtonEvent::kLongPress:
      g_status_led.signal_user_feedback(now);
      Serial.println("[touch] long press detected -> status LED feedback");
      break;
    case TouchButtonEvent::kFactoryReset:
      g_status_led.signal_user_feedback(now);
      Serial.println("[touch] very long press detected -> status LED feedback");
      break;
    case TouchButtonEvent::kNone:
    default:
      break;
  }
#endif

  if (!kSharedUserButton) {
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
  }

  if (g_provisioning_mode) {
    if (now - g_last_provisioning_heartbeat_ms >= 5000) {
      g_last_provisioning_heartbeat_ms = now;
      Serial.println("[provisioning] waiting (Wi-Fi + provisioning flow not implemented yet)");
    }
    return;
  }

  if (platform_enabled()) {
    poll_platform_commands(now);
    send_platform_status(now);
    send_platform_reading(now);
  }

  if (now - g_last_dht22_read_ms >= DHT22_READ_INTERVAL_MS) {
    g_last_dht22_read_ms = now;
    if (!platform_enabled()) {
      read_platform_reading();
    }
  }
}
