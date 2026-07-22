#include "ambient_led_belt/ambient_led_belt_fastled_transport.h"

#include <Arduino.h>
#include <FastLED.h>

namespace plantlab {
namespace ambient_led_belt {
namespace {

CRGB g_led_pixels[AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS];

}  // namespace

bool FastAmbientLedBeltTransport::begin(const AmbientLedBeltConfig& config, String* error) {
  if (config.data_gpio != AMBIENT_LED_BELT_DATA_GPIO) {
    if (error != nullptr) {
      *error = "FastLED transport data GPIO does not match compiled AMBIENT_LED_BELT_DATA_GPIO";
    }
    pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
    digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);
    return false;
  }
  if (config.logical_pixel_count == 0 || config.logical_pixel_count > AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS) {
    if (error != nullptr) {
      *error = "FastLED transport logical pixel count is invalid";
    }
    pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
    digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);
    return false;
  }

  count_ = AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS;
  pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
  digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);
  FastLED.addLeds<WS2811, AMBIENT_LED_BELT_DATA_GPIO, RGB>(g_led_pixels, count_);
  FastLED.setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(0);
  for (uint16_t index = 0; index < count_; ++index) {
    g_led_pixels[index] = CRGB::Black;
  }
  FastLED.show();
  initialized_ = true;
  return true;
}

bool FastAmbientLedBeltTransport::show(
    const RgbColor* logical_pixels,
    uint16_t count,
    ColorOrder color_order,
    uint8_t brightness,
    String* error) {
  if (!initialized_) {
    if (error != nullptr) {
      *error = "FastLED transport is not initialized";
    }
    return false;
  }
  if (count > count_ || count > AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS) {
    if (error != nullptr) {
      *error = "FastLED transport frame exceeds configured logical pixel limit";
    }
    return false;
  }
  for (uint16_t index = 0; index < count_; ++index) {
    const RgbColor logical = (logical_pixels != nullptr && index < count) ? logical_pixels[index] : RgbColor{};
    const RgbColor mapped = transportColorForOrder(logical, color_order);
    g_led_pixels[index] = CRGB(mapped.r, mapped.g, mapped.b);
  }
  FastLED.setBrightness(brightness);
  FastLED.show();
  return true;
}

void FastAmbientLedBeltTransport::shutdown() {
  if (!initialized_) {
    return;
  }
  FastLED.setBrightness(0);
  for (uint16_t index = 0; index < count_; ++index) {
    g_led_pixels[index] = CRGB::Black;
  }
  FastLED.show();
  initialized_ = false;
  count_ = 0;
  pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
  digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);
}

}  // namespace ambient_led_belt
}  // namespace plantlab
