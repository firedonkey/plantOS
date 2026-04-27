#include <Arduino.h>

#include "actuators/light_controller.h"
#include "actuators/pump_controller.h"
#include "config.h"
#include "sensors/dht22_sensor.h"
#include "sensors/moisture_sensor.h"

namespace {
Dht22Sensor g_dht22(PIN_DHT22_DATA);
MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
LightController g_light(
    PIN_LIGHT_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PumpController g_pump(PIN_PUMP_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
unsigned long g_last_dht22_read_ms = 0;
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

  g_dht22.begin();
  g_moisture.begin();
  g_light.begin();
  g_pump.begin();
  Serial.println("[dht22] sensor initialized");
  Serial.println("[moisture] sensor initialized");
  Serial.println("[light] initialized OFF");
  Serial.println("[pump] initialized OFF");
}

void loop() {
  g_pump.update();

  const unsigned long now = millis();
  if (now - g_last_dht22_read_ms < DHT22_READ_INTERVAL_MS) {
    delay(10);
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
