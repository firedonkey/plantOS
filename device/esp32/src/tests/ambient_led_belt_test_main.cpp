#include <Arduino.h>
#include <FastLED.h>

#include "config.h"

#ifndef AMBIENT_LED_BELT_TEST_DEFAULT_BRIGHTNESS
#define AMBIENT_LED_BELT_TEST_DEFAULT_BRIGHTNESS 3
#endif

namespace {

constexpr uint8_t kMaxBrightness = AMBIENT_LED_BELT_MAX_BRIGHTNESS;
constexpr uint16_t kPixelCount = AMBIENT_LED_BELT_LOGICAL_PIXEL_COUNT;
constexpr uint16_t kMaxPixels = AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS;
constexpr unsigned long kAnimationFrameMs = 80;

CRGB g_leds[kMaxPixels];
String g_line_buffer;
uint8_t g_brightness = AMBIENT_LED_BELT_TEST_DEFAULT_BRIGHTNESS;
String g_color_order = AMBIENT_LED_BELT_COLOR_ORDER;
String g_mode = "off";
unsigned long g_last_animation_ms = 0;
uint16_t g_chase_index = 0;
uint8_t g_rainbow_hue = 0;
CRGB g_solid_color = CRGB::Black;

uint8_t clampBrightness(int value) {
  if (value < 0) {
    return 0;
  }
  if (value > kMaxBrightness) {
    return kMaxBrightness;
  }
  return static_cast<uint8_t>(value);
}

String normalized(String value) {
  value.trim();
  value.toLowerCase();
  return value;
}

bool isNumeric(const String& value) {
  if (value.isEmpty()) {
    return false;
  }
  for (size_t index = 0; index < value.length(); ++index) {
    if (!isDigit(value.charAt(index))) {
      return false;
    }
  }
  return true;
}

String tokenAt(const String& line, int token_index) {
  int current_token = 0;
  int start = -1;
  for (int index = 0; index <= static_cast<int>(line.length()); ++index) {
    const bool at_end = index == static_cast<int>(line.length());
    const bool at_space = !at_end && isSpace(line.charAt(index));
    if (!at_end && !at_space && start < 0) {
      start = index;
    }
    if ((at_end || at_space) && start >= 0) {
      if (current_token == token_index) {
        return line.substring(start, index);
      }
      ++current_token;
      start = -1;
    }
  }
  return "";
}

CRGB applyColorOrder(const CRGB& logical) {
  const String order = normalized(g_color_order);
  if (order == "rgb") {
    return logical;
  }
  if (order == "rbg") {
    return CRGB(logical.r, logical.b, logical.g);
  }
  if (order == "grb") {
    return CRGB(logical.g, logical.r, logical.b);
  }
  if (order == "gbr") {
    return CRGB(logical.g, logical.b, logical.r);
  }
  if (order == "brg") {
    return CRGB(logical.b, logical.r, logical.g);
  }
  if (order == "bgr") {
    return CRGB(logical.b, logical.g, logical.r);
  }
  return logical;
}

void showLogical(const CRGB* logical_pixels, uint16_t count, uint8_t brightness) {
  for (uint16_t index = 0; index < kPixelCount; ++index) {
    const CRGB logical = (logical_pixels != nullptr && index < count) ? logical_pixels[index] : CRGB::Black;
    g_leds[index] = applyColorOrder(logical);
  }
  for (uint16_t index = kPixelCount; index < kMaxPixels; ++index) {
    g_leds[index] = CRGB::Black;
  }
  FastLED.setBrightness(clampBrightness(brightness));
  FastLED.show();
}

void showSolid(const CRGB& color, int brightness = -1) {
  if (brightness >= 0) {
    g_brightness = clampBrightness(brightness);
  }
  CRGB logical[kPixelCount];
  for (CRGB& pixel : logical) {
    pixel = color;
  }
  g_solid_color = color;
  g_mode = color == CRGB::Black || g_brightness == 0 ? "off" : "solid";
  showLogical(logical, kPixelCount, g_brightness);
}

void showOff() {
  g_mode = "off";
  g_solid_color = CRGB::Black;
  showLogical(nullptr, 0, 0);
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  red [brightness]      dim red, stays on until off");
  Serial.println("  green [brightness]    dim green, stays on until off");
  Serial.println("  blue [brightness]     dim blue, stays on until off");
  Serial.println("  white [brightness]    dim white, stays on until off");
  Serial.println("  solid R G B [brightness]");
  Serial.println("  pixel INDEX R G B [brightness]");
  Serial.println("  chase [brightness]");
  Serial.println("  rainbow [brightness]");
  Serial.println("  walk [brightness]     one pass across logical WS2811 pixels");
  Serial.println("  brightness 0-51");
  Serial.println("  order RGB|RBG|GRB|GBR|BRG|BGR");
  Serial.println("  off");
  Serial.println("  status");
  Serial.println("  help");
}

void printStatus() {
  Serial.printf(
      "[status] mode=%s brightness=%u max=%u din_gpio=%d logical_pixels=%u color_order=%s\n",
      g_mode.c_str(),
      static_cast<unsigned int>(g_brightness),
      static_cast<unsigned int>(kMaxBrightness),
      AMBIENT_LED_BELT_DATA_GPIO,
      static_cast<unsigned int>(kPixelCount),
      g_color_order.c_str());
}

void setColorOrder(const String& order) {
  const String normalized_order = normalized(order);
  if (normalized_order != "rgb" && normalized_order != "rbg" && normalized_order != "grb" &&
      normalized_order != "gbr" && normalized_order != "brg" && normalized_order != "bgr") {
    Serial.println("[error] color order must be RGB, RBG, GRB, GBR, BRG, or BGR");
    return;
  }
  g_color_order = normalized_order;
  g_color_order.toUpperCase();
  if (g_mode == "solid") {
    showSolid(g_solid_color);
  }
  Serial.printf("[ambient-led-belt-test] color_order=%s\n", g_color_order.c_str());
}

bool parseBrightnessToken(const String& token, uint8_t* brightness) {
  if (token.isEmpty()) {
    return false;
  }
  if (!isNumeric(token)) {
    Serial.println("[error] brightness must be a number");
    return false;
  }
  *brightness = clampBrightness(token.toInt());
  return true;
}

void runWalk(uint8_t brightness) {
  g_mode = "walk";
  Serial.printf("[ambient-led-belt-test] walking %u logical pixels at brightness=%u\n",
                static_cast<unsigned int>(kPixelCount),
                static_cast<unsigned int>(brightness));
  CRGB logical[kPixelCount];
  for (uint16_t active = 0; active < kPixelCount; ++active) {
    for (uint16_t index = 0; index < kPixelCount; ++index) {
      logical[index] = index == active ? CRGB::White : CRGB::Black;
    }
    showLogical(logical, kPixelCount, brightness);
    delay(250);
  }
  showOff();
  Serial.println("[ambient-led-belt-test] walk done; off");
}

void tickAnimation() {
  const unsigned long now = millis();
  if (now - g_last_animation_ms < kAnimationFrameMs) {
    return;
  }
  g_last_animation_ms = now;

  CRGB logical[kPixelCount];
  if (g_mode == "chase") {
    for (uint16_t index = 0; index < kPixelCount; ++index) {
      logical[index] = index == g_chase_index ? CRGB::White : CRGB::Black;
    }
    g_chase_index = static_cast<uint16_t>((g_chase_index + 1) % kPixelCount);
    showLogical(logical, kPixelCount, g_brightness);
    return;
  }

  if (g_mode == "rainbow") {
    for (uint16_t index = 0; index < kPixelCount; ++index) {
      logical[index] = CHSV(static_cast<uint8_t>(g_rainbow_hue + index * 12), 255, 255);
    }
    ++g_rainbow_hue;
    showLogical(logical, kPixelCount, g_brightness);
  }
}

void handleCommand(String line) {
  line.trim();
  if (line.isEmpty()) {
    return;
  }

  const String command = normalized(tokenAt(line, 0));
  if (command == "help" || command == "?") {
    printHelp();
    return;
  }
  if (command == "status") {
    printStatus();
    return;
  }
  if (command == "off" || command == "clear") {
    showOff();
    Serial.println("[ambient-led-belt-test] off");
    printStatus();
    return;
  }
  if (command == "brightness") {
    uint8_t brightness = g_brightness;
    if (parseBrightnessToken(tokenAt(line, 1), &brightness)) {
      g_brightness = brightness;
      if (g_mode == "solid") {
        showSolid(g_solid_color);
      }
      Serial.printf("[ambient-led-belt-test] brightness=%u\n", static_cast<unsigned int>(g_brightness));
    }
    return;
  }
  if (command == "order") {
    setColorOrder(tokenAt(line, 1));
    return;
  }

  uint8_t brightness = g_brightness;
  const String brightness_token = tokenAt(line, 1);
  if ((command == "red" || command == "green" || command == "blue" || command == "white" ||
       command == "chase" || command == "rainbow" || command == "walk") &&
      !brightness_token.isEmpty()) {
    parseBrightnessToken(brightness_token, &brightness);
  }

  if (command == "red") {
    showSolid(CRGB::Red, brightness);
  } else if (command == "green") {
    showSolid(CRGB::Green, brightness);
  } else if (command == "blue") {
    showSolid(CRGB::Blue, brightness);
  } else if (command == "white") {
    showSolid(CRGB::White, brightness);
  } else if (command == "chase") {
    g_brightness = brightness;
    g_chase_index = 0;
    g_mode = "chase";
  } else if (command == "rainbow") {
    g_brightness = brightness;
    g_rainbow_hue = 0;
    g_mode = "rainbow";
  } else if (command == "walk") {
    runWalk(brightness);
    return;
  } else if (command == "solid") {
    const String r = tokenAt(line, 1);
    const String g = tokenAt(line, 2);
    const String b = tokenAt(line, 3);
    if (!isNumeric(r) || !isNumeric(g) || !isNumeric(b)) {
      Serial.println("[error] usage: solid R G B [brightness]");
      return;
    }
    const String optional_brightness = tokenAt(line, 4);
    if (!optional_brightness.isEmpty()) {
      parseBrightnessToken(optional_brightness, &brightness);
    }
    showSolid(
        CRGB(
            static_cast<uint8_t>(constrain(r.toInt(), 0, 255)),
            static_cast<uint8_t>(constrain(g.toInt(), 0, 255)),
            static_cast<uint8_t>(constrain(b.toInt(), 0, 255))),
        brightness);
  } else if (command == "pixel") {
    const String index_token = tokenAt(line, 1);
    const String r = tokenAt(line, 2);
    const String g = tokenAt(line, 3);
    const String b = tokenAt(line, 4);
    if (!isNumeric(index_token) || !isNumeric(r) || !isNumeric(g) || !isNumeric(b)) {
      Serial.println("[error] usage: pixel INDEX R G B [brightness]");
      return;
    }
    const String optional_brightness = tokenAt(line, 5);
    if (!optional_brightness.isEmpty()) {
      parseBrightnessToken(optional_brightness, &brightness);
    }
    const uint16_t pixel_index = static_cast<uint16_t>(index_token.toInt());
    if (pixel_index >= kPixelCount) {
      Serial.printf("[error] pixel index must be 0-%u\n", static_cast<unsigned int>(kPixelCount - 1));
      return;
    }
    CRGB logical[kPixelCount];
    for (CRGB& pixel : logical) {
      pixel = CRGB::Black;
    }
    logical[pixel_index] = CRGB(
        static_cast<uint8_t>(constrain(r.toInt(), 0, 255)),
        static_cast<uint8_t>(constrain(g.toInt(), 0, 255)),
        static_cast<uint8_t>(constrain(b.toInt(), 0, 255)));
    g_mode = "pixel";
    g_brightness = brightness;
    showLogical(logical, kPixelCount, g_brightness);
  } else {
    Serial.printf("[error] unknown command: %s\n", line.c_str());
    printHelp();
    return;
  }

  Serial.printf("[ambient-led-belt-test] %s brightness=%u\n",
                g_mode.c_str(),
                static_cast<unsigned int>(g_brightness));
  printStatus();
}

}  // namespace

void setup() {
  pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
  digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);

  Serial.begin(115200);
  delay(500);

  FastLED.addLeds<WS2811, AMBIENT_LED_BELT_DATA_GPIO, RGB>(g_leds, kMaxPixels);
  FastLED.setCorrection(TypicalLEDStrip);
  showOff();

  Serial.println();
  Serial.println("=== PlantLab Ambient LED Belt Test Firmware ===");
  Serial.printf("Bottom ambient LED belt: WS2811 DIN on GPIO%d\n", AMBIENT_LED_BELT_DATA_GPIO);
  Serial.printf("Logical pixels: %u  Max brightness: %u  Default brightness: %u  Color order: %s\n",
                static_cast<unsigned int>(kPixelCount),
                static_cast<unsigned int>(kMaxBrightness),
                static_cast<unsigned int>(g_brightness),
                g_color_order.c_str());
  Serial.println("[ambient-led-belt-test] initialized OFF");
  printHelp();
  printStatus();
  Serial.print("> ");
}

void loop() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      handleCommand(g_line_buffer);
      g_line_buffer = "";
      Serial.print("> ");
    } else if (g_line_buffer.length() < 200) {
      g_line_buffer += c;
    }
  }

  tickAnimation();
}
