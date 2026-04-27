#pragma once

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

// Timing
#define DHT22_READ_INTERVAL_MS 2000
