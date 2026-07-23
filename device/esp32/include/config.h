#pragma once

#if __has_include("platform_secrets.h")
#include "platform_secrets.h"
#elif __has_include("platform_secrets.example.h")
#include "platform_secrets.example.h"
#endif

// PlantLab v2 - Phase 1 local bring-up
// Board: ESP32-S3-DevKitC-1-N32R16V

#ifndef BOARD_NAME
#define BOARD_NAME "ESP32-S3-DevKitC-1-N32R16V"
#endif

// Sensors
// GPIO1 is reserved on the EVT main board for the WS2811 ambient LED belt DIN.
// The previous soil-moisture ADC placeholder used GPIO1; keep it disabled
// until hardware assigns a separate confirmed ADC-capable pin.
#ifndef PIN_SOIL_MOISTURE_ADC
#define PIN_SOIL_MOISTURE_ADC -1
#endif
// Water-level capacitive pads use the ESP32-S3 touch peripheral.
#define WATER_LEVEL_TOP_GPIO 4
#define WATER_LEVEL_TOP_TOUCH_CHANNEL 4
#define WATER_LEVEL_MIDDLE_GPIO 5
#define WATER_LEVEL_MIDDLE_TOUCH_CHANNEL 5
#define WATER_LEVEL_BOTTOM_GPIO 6
#define WATER_LEVEL_BOTTOM_TOUCH_CHANNEL 6

// Moisture ADC behavior
#define MOISTURE_SAMPLE_COUNT 10
#define MOISTURE_SAMPLE_DELAY_MS 5

// Three-pad capacitive water-level behavior.
// The firmware persists dry/wet calibration in NVS and derives each pad's
// polarity from the measured dry/wet pair; it does not assume wet readings are
// always higher or always lower.
#define WATER_LEVEL_FILTER_SAMPLE_COUNT 5
#define WATER_LEVEL_SAMPLE_INTERVAL_MS 100
#define WATER_LEVEL_STARTUP_SETTLE_MS 2000
#define WATER_LEVEL_CHANNEL_DEBOUNCE_MS 1500
#define WATER_LEVEL_STATE_DEBOUNCE_MS 2000
#define WATER_LEVEL_INCONSISTENT_GRACE_MS 10000
#define WATER_LEVEL_THRESHOLD_PERCENT 50
#define WATER_LEVEL_HYSTERESIS_PERCENT 10
#define WATER_LEVEL_MIN_SIGNAL_DELTA 25
#define WATER_LEVEL_MAX_STABLE_SPREAD 300
#define WATER_LEVEL_READ_FAILURE_TIMEOUT_MS 5000
#define WATER_LEVEL_DIAGNOSTIC_INTERVAL_MS 500

// Calibration defaults (adjust later with real calibration)
// Typical capacitive sensors read higher when dry and lower when wet.
#define MOISTURE_RAW_DRY 3000
#define MOISTURE_RAW_WET 1200

// I2C environmental sensors on the current main-board harness.
#define PIN_I2C_SDA 47
#define PIN_I2C_SCL 48

// Top grow-light panel, driven through AL8860 CTRL inputs.
#define PIN_GROW_LIGHT_RED_CTRL 18
#define PIN_GROW_LIGHT_WHITE_CTRL 8
// Legacy single-channel name retained for older tests and diagnostics. The
// production grow light uses the red/white CTRL pins above.
#define PIN_LIGHT_MOSFET_GATE PIN_GROW_LIGHT_WHITE_CTRL
// Legacy pump support is retained in firmware, but it must not share the grow
// LED pin. GPIO16 is unused on the current PCB.
#define PIN_PUMP_MOSFET_GATE 16

#define ACTUATOR_ON_LEVEL HIGH
#define ACTUATOR_OFF_LEVEL LOW

// Grow LED intensity control uses PWM on the MOSFET gate. Set this to 0 for
// relay or other on/off-only light hardware.
#ifndef PLANTLAB_LIGHT_INTENSITY_CONTROL_ENABLED
#define PLANTLAB_LIGHT_INTENSITY_CONTROL_ENABLED 1
#endif

// AL8860 CTRL PWM frequency. Keep this above the audible range to reduce coil
// or ceramic-capacitor noise when the grow LEDs are dimmed.
#ifndef PLANTLAB_GROW_LIGHT_PWM_FREQUENCY_HZ
#define PLANTLAB_GROW_LIGHT_PWM_FREQUENCY_HZ 25000
#endif

// 24 V WS2811 FCOB ambient LED belt. The purchased belt has about 630 physical
// emitters, but WS2811 belts usually address groups of emitters through one IC.
// Only logical WS2811 control segments are allocated and transmitted.
#ifndef AMBIENT_LED_BELT_DATA_GPIO
#define AMBIENT_LED_BELT_DATA_GPIO 1
#endif
#define PIN_AMBIENT_LED_BELT_DIN AMBIENT_LED_BELT_DATA_GPIO
#define AMBIENT_LED_BELT_PHYSICAL_LED_COUNT 630
#define AMBIENT_LED_BELT_LOGICAL_PIXEL_COUNT 14
#define AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS 120
#define AMBIENT_LED_BELT_COLOR_ORDER "RGB"
#define AMBIENT_LED_BELT_MAX_BRIGHTNESS 51
#define AMBIENT_LED_BELT_DEFAULT_BRIGHTNESS 26
#define AMBIENT_LED_BELT_DIAGNOSTIC_MAX_BRIGHTNESS 26
#define AMBIENT_LED_BELT_MAX_FPS 30
#define AMBIENT_LED_BELT_START_ENABLED 0

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
#define TOUCH_FACTORY_RESET_MS 20000
#define TOUCH_MULTI_TAP_WINDOW_MS 500

// Touch threshold model:
// touch is considered active when raw <= (untouched_baseline - TOUCH_TRIGGER_DELTA)
#define TOUCH_TRIGGER_DELTA 25
#define TOUCH_RAW_LOG_INTERVAL_MS 0

// ESP-NOW link test (master <-> camera node)
#define ESPNOW_TEST_WIFI_CHANNEL 1
#define ESPNOW_TEST_SEND_INTERVAL_MS 2000

#ifndef ESPNOW_PROVISION_CONFIG_VERSION
#define ESPNOW_PROVISION_CONFIG_VERSION 1
#endif

#ifndef ESPNOW_PROVISION_CAMERA_NODE_INDEX
#define ESPNOW_PROVISION_CAMERA_NODE_INDEX 1
#endif

#ifndef ESPNOW_PROVISION_PLATFORM_DEVICE_ID
#define ESPNOW_PROVISION_PLATFORM_DEVICE_ID 1
#endif

#ifndef ESPNOW_PROVISION_DEVICE_TOKEN
#define ESPNOW_PROVISION_DEVICE_TOKEN "espnow-shared-device-token"
#endif

#ifndef ESPNOW_PROVISION_ACK_TIMEOUT_MS
#define ESPNOW_PROVISION_ACK_TIMEOUT_MS 1500UL
#endif

#ifndef ESPNOW_PROVISION_MAX_RETRIES
#define ESPNOW_PROVISION_MAX_RETRIES 3
#endif

// Timing
#define PLANTLAB_LOCAL_SENSOR_READ_INTERVAL_MS 2000

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

#ifndef PLANTLAB_PROVISIONING_API_URL
#define PLANTLAB_PROVISIONING_API_URL ""
#endif

#ifndef PLANTLAB_ENV_LABEL
#define PLANTLAB_ENV_LABEL "custom"
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
#define PLANTLAB_IMAGE_INTERVAL_MS 3600000UL
#endif

#ifndef PLANTLAB_CAMERA_CAPTURE_ENABLED
#define PLANTLAB_CAMERA_CAPTURE_ENABLED 0
#endif

#ifndef PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS
#define PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS PLANTLAB_IMAGE_INTERVAL_MS
#endif

#ifndef PLANTLAB_WIFI_CONNECT_TIMEOUT_MS
#define PLANTLAB_WIFI_CONNECT_TIMEOUT_MS 20000UL
#endif

#ifndef PLANTLAB_NTP_SERVER_1
#define PLANTLAB_NTP_SERVER_1 "pool.ntp.org"
#endif

#ifndef PLANTLAB_NTP_SERVER_2
#define PLANTLAB_NTP_SERVER_2 "time.google.com"
#endif

#ifndef PLANTLAB_NTP_SYNC_TIMEOUT_MS
#define PLANTLAB_NTP_SYNC_TIMEOUT_MS 15000UL
#endif

#ifndef PLANTLAB_NTP_RETRY_INTERVAL_MS
#define PLANTLAB_NTP_RETRY_INTERVAL_MS 300000UL
#endif

#ifndef PLANTLAB_CAMERA_HEARTBEAT_INTERVAL_MS
#define PLANTLAB_CAMERA_HEARTBEAT_INTERVAL_MS 45000UL
#endif

#ifndef PLANTLAB_WIFI_MAX_TX_POWER
#define PLANTLAB_WIFI_MAX_TX_POWER 40
#endif

#ifndef PLANTLAB_CAMERA_IDLE_CPU_MHZ
#define PLANTLAB_CAMERA_IDLE_CPU_MHZ 80
#endif

#ifndef PLANTLAB_CAMERA_ACTIVE_CPU_MHZ
#define PLANTLAB_CAMERA_ACTIVE_CPU_MHZ 160
#endif
