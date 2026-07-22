#pragma once

#include <Arduino.h>

#include <cstdint>
#include <vector>

#include "config.h"

namespace plantlab {
namespace ambient_led_belt {

enum class ColorOrder {
  kRgb,
  kRbg,
  kGrb,
  kGbr,
  kBrg,
  kBgr,
};

enum class Mode {
  kOff,
  kSolid,
  kBreathe,
  kPulse,
  kChase,
  kRainbow,
  kDiagnostic,
};

struct RgbColor {
  RgbColor() = default;
  constexpr RgbColor(uint8_t red, uint8_t green, uint8_t blue) : r(red), g(green), b(blue) {}

  uint8_t r = 0;
  uint8_t g = 0;
  uint8_t b = 0;
};

struct AmbientLedBeltConfig {
  int data_gpio = AMBIENT_LED_BELT_DATA_GPIO;
  uint16_t logical_pixel_count = AMBIENT_LED_BELT_LOGICAL_PIXEL_COUNT;
  uint16_t physical_led_count = AMBIENT_LED_BELT_PHYSICAL_LED_COUNT;
  ColorOrder color_order = ColorOrder::kRgb;
  uint8_t maximum_brightness = AMBIENT_LED_BELT_MAX_BRIGHTNESS;
  uint8_t default_brightness = AMBIENT_LED_BELT_DEFAULT_BRIGHTNESS;
  uint8_t diagnostic_max_brightness = AMBIENT_LED_BELT_DIAGNOSTIC_MAX_BRIGHTNESS;
  uint16_t maximum_frame_rate = AMBIENT_LED_BELT_MAX_FPS;
  bool enabled_at_startup = AMBIENT_LED_BELT_START_ENABLED != 0;
};

struct AmbientLedBeltState {
  bool initialized = false;
  bool available = false;
  bool enabled = false;
  Mode mode = Mode::kOff;
  RgbColor requested_color{};
  uint8_t requested_brightness = 0;
  uint8_t effective_brightness = 0;
  bool diagnostic_active = false;
  uint16_t logical_pixel_count = AMBIENT_LED_BELT_LOGICAL_PIXEL_COUNT;
  uint16_t physical_led_count = AMBIENT_LED_BELT_PHYSICAL_LED_COUNT;
  ColorOrder color_order = ColorOrder::kRgb;
  int data_gpio = AMBIENT_LED_BELT_DATA_GPIO;
  uint16_t effect_speed_ms = 1000;
  unsigned long last_update_ms = 0;
  String last_error;
};

struct AmbientLedBeltCommand {
  bool has_enabled = false;
  bool enabled = false;
  bool has_mode = false;
  Mode mode = Mode::kOff;
  bool has_color = false;
  RgbColor color{};
  bool has_brightness = false;
  int brightness = 0;
  bool has_speed_ms = false;
  int speed_ms = 0;
  bool has_logical_pixel_count = false;
  int logical_pixel_count = 0;
  bool has_color_order = false;
  ColorOrder color_order = ColorOrder::kRgb;
  bool has_maximum_brightness = false;
  int maximum_brightness = 0;
  bool has_default_brightness = false;
  int default_brightness = 0;
  bool save_config = false;
  bool cancel_diagnostic = false;
};

class AmbientLedBeltTransport {
 public:
  virtual ~AmbientLedBeltTransport() = default;
  virtual bool begin(const AmbientLedBeltConfig& config, String* error) = 0;
  virtual bool show(
      const RgbColor* logical_pixels,
      uint16_t count,
      ColorOrder color_order,
      uint8_t brightness,
      String* error) = 0;
  virtual void shutdown() = 0;
};

AmbientLedBeltConfig defaultConfig();
bool parseColorOrder(const String& value, ColorOrder* order);
const char* colorOrderName(ColorOrder order);
bool parseMode(const String& value, Mode* mode);
const char* modeName(Mode mode);
RgbColor transportColorForOrder(const RgbColor& color, ColorOrder order);
bool validateConfig(const AmbientLedBeltConfig& config, String* error);
bool parseCommandJson(const String& json, AmbientLedBeltCommand* command, String* error);

class AmbientLedBeltController {
 public:
  explicit AmbientLedBeltController(AmbientLedBeltTransport* transport);

  bool configure(const AmbientLedBeltConfig& config, String* error = nullptr);
  bool begin(String* error = nullptr);
  void markUnavailable(const String& error);
  void shutdown();
  void clear();
  bool setEnabled(bool enabled, String* error = nullptr);
  bool setBrightness(int brightness, String* error = nullptr);
  bool setSolidColor(RgbColor color, int brightness = -1, String* error = nullptr);
  bool setEffect(Mode mode, int speed_ms = -1, String* error = nullptr);
  bool runDiagnostic(int brightness_override = -1, String* error = nullptr);
  void cancelDiagnostic();
  bool applyCommand(const AmbientLedBeltCommand& command, String* message, String* error = nullptr);
  bool tick(unsigned long now);
  void suspendForCameraCapture(unsigned long now);
  void resumeAfterCameraCapture(unsigned long now);

  const AmbientLedBeltConfig& config() const;
  const AmbientLedBeltState& state() const;
  const RgbColor& logicalPixelAt(uint16_t index) const;
  uint32_t transmitted_frame_count() const;

 private:
  void setError(const String& error);
  void resizeBuffer();
  void setAll(RgbColor color);
  void setBlack();
  bool transmit(unsigned long now, bool force = false);
  bool markMode(Mode mode);
  bool updateEffect(unsigned long now);
  void updateBreathe(unsigned long now);
  void updatePulse(unsigned long now);
  void updateChase(unsigned long now);
  void updateRainbow(unsigned long now);
  bool updateDiagnostic(unsigned long now);
  uint8_t boundedBrightness(int brightness) const;
  uint16_t boundedSpeed(int speed_ms) const;
  bool sameCommandState(const AmbientLedBeltCommand& command) const;

  AmbientLedBeltTransport* transport_;
  AmbientLedBeltConfig config_;
  AmbientLedBeltState state_;
  std::vector<RgbColor> pixels_;
  bool dirty_ = false;
  bool frame_clear_sent_ = false;
  bool suspended_for_camera_ = false;
  bool suspended_was_enabled_ = false;
  Mode suspended_mode_ = Mode::kOff;
  RgbColor suspended_color_{};
  uint8_t suspended_brightness_ = 0;
  unsigned long last_frame_ms_ = 0;
  unsigned long effect_started_ms_ = 0;
  Mode pulse_return_mode_ = Mode::kOff;
  RgbColor pulse_return_color_{};
  uint8_t pulse_return_brightness_ = 0;
  bool pulse_return_enabled_ = false;
  uint8_t diagnostic_step_ = 0;
  uint16_t diagnostic_pixel_ = 0;
  unsigned long diagnostic_next_ms_ = 0;
  uint32_t transmitted_frame_count_ = 0;
};

}  // namespace ambient_led_belt
}  // namespace plantlab
