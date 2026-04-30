#pragma once

#if __has_include("platform_secrets.h")
#include "platform_secrets.h"
#elif __has_include("platform_secrets.example.h")
#include "platform_secrets.example.h"
#endif

// PlantLab v2 - Phase 1 local bring-up
// Board: ESP32-S3-DevKitC-1-N32R16V

#define BOARD_NAME "ESP32-S3-DevKitC-1-N32R16V"

// Sensors
#define PIN_SOIL_MOISTURE_ADC 1
#define PIN_DHT22_DATA 4

// Moisture ADC behavior
#define MOISTURE_SAMPLE_COUNT 10
#define MOISTURE_SAMPLE_DELAY_MS 5

// Calibration defaults (adjust later with real calibration)
// Typical capacitive sensors read higher when dry and lower when wet.
#define MOISTURE_RAW_DRY 3000
#define MOISTURE_RAW_WET 1200

// Optional I2C (only used if SHT31 or OLED is enabled later)
#define PIN_I2C_SDA 8
#define PIN_I2C_SCL 9

// Actuators (AO3400A low-side MOSFET gate control)
#define PIN_LIGHT_MOSFET_GATE 16
#define PIN_PUMP_MOSFET_GATE 15

#define ACTUATOR_ON_LEVEL HIGH
#define ACTUATOR_OFF_LEVEL LOW

// Power button + status LED
// Power button input (active low with internal pull-up).
// Do not use GPIO0 for power-button behavior in this project.
#define PIN_POWER_BUTTON 14
#define POWER_BUTTON_ACTIVE_LEVEL LOW

// Status LED default: external LED pin. Change to your wired LED GPIO.
#define PIN_STATUS_LED 2
#define STATUS_LED_ON_LEVEL HIGH
#define STATUS_LED_OFF_LEVEL LOW

// Button behavior
#define POWER_BUTTON_DEBOUNCE_MS 30
#define POWER_BUTTON_LONG_PRESS_MS 5000

// Capacitive touch button (ESP32-S3 touch-capable GPIO)
#define ENABLE_TOUCH_BUTTON 1
// Shared physical user button: same GPIO as power button.
#define PIN_TOUCH_BUTTON 14

// Touch tuning values.
// Calibrate these with your real enclosure and wiring.
#define TOUCH_SAMPLE_COUNT 10
#define TOUCH_CHECK_INTERVAL_MS 30
#define TOUCH_DEBOUNCE_MS 80
#define TOUCH_SHORT_TAP_MAX_MS 500
#define TOUCH_LONG_PRESS_MS 5000
#define TOUCH_FACTORY_RESET_MS 10000
#define TOUCH_MULTI_TAP_WINDOW_MS 500

// Touch threshold model:
// touch is considered active when raw <= (untouched_baseline - TOUCH_TRIGGER_DELTA)
#define TOUCH_TRIGGER_DELTA 25
#define TOUCH_RAW_LOG_INTERVAL_MS 0

// ESP-NOW link test (master <-> camera node)
#define ESPNOW_TEST_WIFI_CHANNEL 1
#define ESPNOW_TEST_SEND_INTERVAL_MS 2000

// Timing
#define DHT22_READ_INTERVAL_MS 2000

#ifndef PLANTLAB_WIFI_SSID
#define PLANTLAB_WIFI_SSID ""
#endif

#ifndef PLANTLAB_WIFI_PASSWORD
#define PLANTLAB_WIFI_PASSWORD ""
#endif

#ifndef PLANTLAB_PLATFORM_URL
#define PLANTLAB_PLATFORM_URL ""
#endif

#ifndef PLANTLAB_DEVICE_ID
#define PLANTLAB_DEVICE_ID 0
#endif

#ifndef PLANTLAB_DEVICE_TOKEN
#define PLANTLAB_DEVICE_TOKEN ""
#endif

#ifndef PLANTLAB_SENSOR_SEND_INTERVAL_MS
#define PLANTLAB_SENSOR_SEND_INTERVAL_MS 10000UL
#endif

#ifndef PLANTLAB_COMMAND_POLL_INTERVAL_MS
#define PLANTLAB_COMMAND_POLL_INTERVAL_MS 2000UL
#endif

#ifndef PLANTLAB_STATUS_INTERVAL_MS
#define PLANTLAB_STATUS_INTERVAL_MS 10000UL
#endif

#ifndef PLANTLAB_IMAGE_INTERVAL_MS
#define PLANTLAB_IMAGE_INTERVAL_MS 15000UL
#endif

#ifndef PLANTLAB_WIFI_CONNECT_TIMEOUT_MS
#define PLANTLAB_WIFI_CONNECT_TIMEOUT_MS 20000UL
#endif
