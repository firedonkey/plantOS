#include <Arduino.h>

#include "actuators/light_controller.h"
#include "actuators/pump_controller.h"
#include "config.h"

namespace {
LightController g_light(
    PIN_LIGHT_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PumpController g_pump(PIN_PUMP_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);

enum class ToggleTarget { kLight, kPump };
ToggleTarget g_toggle_target = ToggleTarget::kLight;
String g_line_buffer;
}

void print_help() {
  Serial.println("Commands:");
  Serial.println("  [Space]       toggle selected target (light/pump)");
  Serial.println("  l             select light for [Space] toggle");
  Serial.println("  p             select pump for [Space] toggle");
  Serial.println("  light on");
  Serial.println("  light off");
  Serial.println("  light toggle");
  Serial.println("  pump on");
  Serial.println("  pump off");
  Serial.println("  pump run <seconds>");
  Serial.println("  status");
  Serial.println("  help");
}

void print_status() {
  const char* target =
      g_toggle_target == ToggleTarget::kLight ? "light" : "pump";
  Serial.printf(
      "[status] light=%s pump=%s pump_timed=%s selected=%s\n",
      g_light.is_on() ? "on" : "off",
      g_pump.is_on() ? "on" : "off",
      g_pump.is_timed_run_active() ? "active" : "inactive",
      target);
}

void handle_command(const String& line) {
  if (line == "light on") {
    g_light.set_on(true);
    Serial.println("[light] ON");
    return;
  }
  if (line == "light off") {
    g_light.set_on(false);
    Serial.println("[light] OFF");
    return;
  }
  if (line == "light toggle") {
    g_light.toggle();
    Serial.printf("[light] %s\n", g_light.is_on() ? "ON" : "OFF");
    return;
  }
  if (line == "pump on") {
    g_pump.set_on(true);
    Serial.println("[pump] ON");
    return;
  }
  if (line == "pump off") {
    g_pump.stop();
    Serial.println("[pump] OFF");
    return;
  }
  if (line.startsWith("pump run ")) {
    const int seconds = line.substring(9).toInt();
    if (seconds <= 0) {
      Serial.println("[pump] invalid seconds");
      return;
    }
    g_pump.start_for_ms(static_cast<unsigned long>(seconds) * 1000UL);
    Serial.printf("[pump] ON for %d second(s)\n", seconds);
    return;
  }
  if (line == "status") {
    print_status();
    return;
  }
  if (line == "help") {
    print_help();
    return;
  }

  Serial.printf("[error] unknown command: %s\n", line.c_str());
  print_help();
}

void handle_shortcut_key(char ch) {
  if (ch == 'l' || ch == 'L') {
    g_toggle_target = ToggleTarget::kLight;
    Serial.println("[shortcut] selected light");
    print_status();
    return;
  }
  if (ch == 'p' || ch == 'P') {
    g_toggle_target = ToggleTarget::kPump;
    Serial.println("[shortcut] selected pump");
    print_status();
    return;
  }
  if (ch == ' ') {
    if (g_toggle_target == ToggleTarget::kLight) {
      g_light.toggle();
      Serial.printf("[shortcut] light %s\n", g_light.is_on() ? "ON" : "OFF");
    } else {
      if (g_pump.is_on()) {
        g_pump.stop();
        Serial.println("[shortcut] pump OFF");
      } else {
        g_pump.set_on(true);
        Serial.println("[shortcut] pump ON");
      }
    }
    print_status();
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab Actuators Test Firmware ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("Light gate pin: GPIO%d\n", PIN_LIGHT_MOSFET_GATE);
  Serial.printf("Pump gate pin: GPIO%d\n", PIN_PUMP_MOSFET_GATE);

  g_light.begin();
  g_pump.begin();
  Serial.println("[light] initialized OFF");
  Serial.println("[pump] initialized OFF");

  print_help();
  print_status();
}

void loop() {
  g_pump.update();

  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());

    if (ch == '\r' || ch == '\n') {
      if (!g_line_buffer.isEmpty()) {
        String normalized = g_line_buffer;
        normalized.trim();
        normalized.toLowerCase();
        if (!normalized.isEmpty()) {
          handle_command(normalized);
        }
        g_line_buffer = "";
      }
      continue;
    }

    if (g_line_buffer.isEmpty() && (ch == ' ' || ch == 'l' || ch == 'L' || ch == 'p' ||
                                    ch == 'P')) {
      handle_shortcut_key(ch);
      continue;
    }

    g_line_buffer += ch;
    if (g_line_buffer.length() > 128) {
      g_line_buffer = "";
      Serial.println("[error] input too long, cleared");
    }
  }
}
