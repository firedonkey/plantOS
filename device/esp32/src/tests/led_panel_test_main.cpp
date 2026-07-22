#include <Arduino.h>

#include "config.h"

#ifndef PIN_LED_PANEL_RED_GATE
#define PIN_LED_PANEL_RED_GATE 18
#endif

#ifndef PIN_LED_PANEL_WHITE_GATE
#define PIN_LED_PANEL_WHITE_GATE 8
#endif

#ifndef LED_PANEL_ON_LEVEL
#define LED_PANEL_ON_LEVEL ACTUATOR_ON_LEVEL
#endif

#ifndef LED_PANEL_OFF_LEVEL
#define LED_PANEL_OFF_LEVEL ACTUATOR_OFF_LEVEL
#endif

#ifndef LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT
#define LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT 1
#endif

#ifndef LED_PANEL_RED_CONNECTOR_PIN
#define LED_PANEL_RED_CONNECTOR_PIN 11
#endif

#ifndef LED_PANEL_WHITE_CONNECTOR_PIN
#define LED_PANEL_WHITE_CONNECTOR_PIN 12
#endif

namespace {
struct LedChannel {
  const char* name;
  const char* net_name;
  const char* driver_ref;
  int connector_pin;
  int pin;
  int brightness_percent;
};

LedChannel g_red{"red", "LED_RED", "U4", LED_PANEL_RED_CONNECTOR_PIN, PIN_LED_PANEL_RED_GATE, 0};
LedChannel g_white{"white", "LED_WHITE", "U7", LED_PANEL_WHITE_CONNECTOR_PIN, PIN_LED_PANEL_WHITE_GATE, 0};
String g_line_buffer;

int clamp_percent(int percent) {
  if (percent < 0) {
    return 0;
  }
  if (percent > 100) {
    return 100;
  }
  return percent;
}

int pwm_duty_for_percent(int percent) {
  const int bounded = clamp_percent(percent);
  int duty = (bounded * 255) / 100;
  if (LED_PANEL_ON_LEVEL == LOW && LED_PANEL_OFF_LEVEL == HIGH) {
    duty = 255 - duty;
  }
  return duty;
}

void apply_channel(LedChannel& channel, int brightness_percent) {
  channel.brightness_percent = clamp_percent(brightness_percent);
  analogWrite(channel.pin, pwm_duty_for_percent(channel.brightness_percent));
}

void drive_control_pins_off() {
  digitalWrite(g_red.pin, LED_PANEL_OFF_LEVEL);
  digitalWrite(g_white.pin, LED_PANEL_OFF_LEVEL);
  pinMode(g_red.pin, OUTPUT);
  pinMode(g_white.pin, OUTPUT);
  digitalWrite(g_red.pin, LED_PANEL_OFF_LEVEL);
  digitalWrite(g_white.pin, LED_PANEL_OFF_LEVEL);
  g_red.brightness_percent = 0;
  g_white.brightness_percent = 0;
}

void set_both(int brightness_percent) {
  apply_channel(g_red, brightness_percent);
  apply_channel(g_white, brightness_percent);
}

void print_status() {
  Serial.printf(
      "[status] red_ctrl=%d%% GPIO%d -> H1-%d/%s -> %s CTRL white_ctrl=%d%% GPIO%d -> H1-%d/%s -> %s CTRL\n",
      g_red.brightness_percent,
      g_red.pin,
      g_red.connector_pin,
      g_red.net_name,
      g_red.driver_ref,
      g_white.brightness_percent,
      g_white.pin,
      g_white.connector_pin,
      g_white.net_name,
      g_white.driver_ref);
}

void print_help() {
  Serial.println("Commands:");
  Serial.println("  red on | red off | red toggle     (red on forces white off)");
  Serial.println("  red <0-100>                       (red >0 forces white off)");
  Serial.println("  white on | white off | white toggle (white on forces red off)");
  Serial.println("  white <0-100>                       (white >0 forces red off)");
  Serial.println("  both on | both off | both toggle");
  Serial.println("  both <0-100>");
  Serial.println("  cycle [hold_ms] [brightness_percent]");
  Serial.println("  status");
  Serial.println("  help");
  Serial.printf("Default ON brightness: %d%%\n", LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT);
}

bool handle_channel_command(LedChannel& channel, LedChannel& other_channel, const String& action) {
  if (action == "on") {
    apply_channel(other_channel, 0);
    apply_channel(channel, LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT);
    Serial.printf("[%s] %d%%\n", channel.name, channel.brightness_percent);
    return true;
  }
  if (action == "off") {
    apply_channel(channel, 0);
    Serial.printf("[%s] 0%%\n", channel.name);
    return true;
  }
  if (action == "toggle") {
    const int next_percent = channel.brightness_percent > 0 ? 0 : LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT;
    if (next_percent > 0) {
      apply_channel(other_channel, 0);
    }
    apply_channel(channel, next_percent);
    Serial.printf("[%s] %d%%\n", channel.name, channel.brightness_percent);
    return true;
  }
  const int percent = action.toInt();
  if (String(percent) == action || action == "0") {
    if (percent > 0) {
      apply_channel(other_channel, 0);
    }
    apply_channel(channel, percent);
    Serial.printf("[%s] %d%%\n", channel.name, channel.brightness_percent);
    return true;
  }
  return false;
}

void run_cycle(unsigned long hold_ms, int brightness_percent) {
  const int bounded_percent = clamp_percent(brightness_percent);
  Serial.printf("[cycle] hold_ms=%lu brightness=%d%%\n", hold_ms, bounded_percent);
  set_both(0);
  delay(150);

  apply_channel(g_red, bounded_percent);
  apply_channel(g_white, 0);
  Serial.printf("[cycle] red %d%%, white 0%%\n", bounded_percent);
  delay(hold_ms);

  apply_channel(g_red, 0);
  apply_channel(g_white, bounded_percent);
  Serial.printf("[cycle] red 0%%, white %d%%\n", bounded_percent);
  delay(hold_ms);

  set_both(bounded_percent);
  Serial.printf("[cycle] red %d%%, white %d%%\n", bounded_percent, bounded_percent);
  delay(hold_ms);

  set_both(0);
  Serial.println("[cycle] red 0%, white 0%");
  print_status();
}

void handle_command(String line) {
  line.trim();
  line.toLowerCase();
  if (line.isEmpty()) {
    return;
  }

  if (line == "help") {
    print_help();
    return;
  }
  if (line == "status") {
    print_status();
    return;
  }
  if (line.startsWith("red ")) {
    handle_channel_command(g_red, g_white, line.substring(4));
    print_status();
    return;
  }
  if (line.startsWith("white ")) {
    handle_channel_command(g_white, g_red, line.substring(6));
    print_status();
    return;
  }
  if (line == "both on") {
    set_both(LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT);
    Serial.printf("[both] %d%%\n", LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT);
    print_status();
    return;
  }
  if (line == "both off") {
    set_both(0);
    Serial.println("[both] 0%");
    print_status();
    return;
  }
  if (line == "both toggle") {
    const int next_percent =
        (g_red.brightness_percent > 0 || g_white.brightness_percent > 0) ? 0 : LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT;
    set_both(next_percent);
    Serial.printf("[both] %d%%\n", next_percent);
    print_status();
    return;
  }
  if (line.startsWith("both ")) {
    const int percent = line.substring(5).toInt();
    set_both(percent);
    Serial.printf("[both] %d%%\n", clamp_percent(percent));
    print_status();
    return;
  }
  if (line == "cycle" || line.startsWith("cycle ")) {
    unsigned long hold_ms = 1000;
    int brightness_percent = LED_PANEL_DEFAULT_BRIGHTNESS_PERCENT;
    if (line.startsWith("cycle ")) {
      const String cycle_args = line.substring(6);
      const int separator = cycle_args.indexOf(' ');
      const String hold_text = separator >= 0 ? cycle_args.substring(0, separator) : cycle_args;
      const String brightness_text = separator >= 0 ? cycle_args.substring(separator + 1) : "";
      hold_ms = static_cast<unsigned long>(hold_text.toInt());
      if (brightness_text.length() > 0) {
        brightness_percent = brightness_text.toInt();
      }
      if (hold_ms < 100) {
        hold_ms = 100;
      }
      if (hold_ms > 10000) {
        hold_ms = 10000;
      }
    }
    run_cycle(hold_ms, brightness_percent);
    return;
  }

  Serial.printf("[error] unknown command: %s\n", line.c_str());
  print_help();
}
}  // namespace

void setup() {
  drive_control_pins_off();

  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab LED Panel Test Firmware ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("Red AL8860 CTRL: GPIO%d -> H1-%d/%s -> %s pin 4 CTRL\n",
                g_red.pin,
                g_red.connector_pin,
                g_red.net_name,
                g_red.driver_ref);
  Serial.printf("White AL8860 CTRL: GPIO%d -> H1-%d/%s -> %s pin 4 CTRL\n",
                g_white.pin,
                g_white.connector_pin,
                g_white.net_name,
                g_white.driver_ref);
  Serial.println("24V LED current path is through AL8860 VIN/SW/inductor/output, not through the GPIO pins.");

  set_both(0);
  Serial.println("[led-panel] initialized OFF");

  print_help();
  print_status();
}

void loop() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == '\r' || ch == '\n') {
      handle_command(g_line_buffer);
      g_line_buffer = "";
      continue;
    }

    g_line_buffer += ch;
    if (g_line_buffer.length() > 128) {
      g_line_buffer = "";
      Serial.println("[error] input too long, cleared");
    }
  }
}
