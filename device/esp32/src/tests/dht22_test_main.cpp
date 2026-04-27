#include <Arduino.h>

#include "config.h"
#include "sensors/dht22_sensor.h"

namespace {
Dht22Sensor g_dht22(PIN_DHT22_DATA);
unsigned long g_last_dht22_read_ms = 0;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab DHT22 Test Firmware ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("DHT22 pin: GPIO%d\n", PIN_DHT22_DATA);
  Serial.println("[dht22-test] this firmware only validates DHT22");

  g_dht22.begin();
  Serial.println("[dht22-test] sensor initialized");
}

void loop() {
  const unsigned long now = millis();
  if (now - g_last_dht22_read_ms < DHT22_READ_INTERVAL_MS) {
    delay(10);
    return;
  }
  g_last_dht22_read_ms = now;

  const Dht22Reading reading = g_dht22.read();
  if (!reading.valid) {
    Serial.println("[dht22-test] read failed (NaN)");
    return;
  }

  Serial.printf(
      "[dht22-test] temp_c=%.1f humidity=%.1f%%\n",
      reading.temperature_c,
      reading.humidity_percent);
}
