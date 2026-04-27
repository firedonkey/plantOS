#include <Arduino.h>

#include "config.h"
#include "sensors/moisture_sensor.h"

namespace {
MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
unsigned long g_last_read_ms = 0;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab Moisture Test Firmware ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("Moisture ADC pin: GPIO%d\n", PIN_SOIL_MOISTURE_ADC);
  Serial.printf(
      "Calibration: dry=%d wet=%d\n", MOISTURE_RAW_DRY, MOISTURE_RAW_WET);
  Serial.printf(
      "Averaging: samples=%d sample_delay_ms=%d\n",
      MOISTURE_SAMPLE_COUNT,
      MOISTURE_SAMPLE_DELAY_MS);

  g_moisture.begin();
  Serial.println("[moisture-test] sensor initialized");
}

void loop() {
  const unsigned long now = millis();
  if (now - g_last_read_ms < 1000) {
    delay(10);
    return;
  }
  g_last_read_ms = now;

  const MoistureReading reading = g_moisture.read();
  if (!reading.valid) {
    Serial.println("[moisture-test] read failed");
    return;
  }

  Serial.printf(
      "[moisture-test] raw=%d percent=%.1f%%\n",
      reading.raw_adc,
      reading.moisture_percent);
}
