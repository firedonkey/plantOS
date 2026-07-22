#include "ambient_led_belt/ambient_led_belt_controller.h"

#include <ArduinoJson.h>

#include <algorithm>

namespace plantlab {
namespace ambient_led_belt {
namespace {

constexpr uint8_t kBlack = 0;
constexpr uint16_t kDefaultEffectSpeedMs = 1000;
constexpr uint16_t kMinimumEffectSpeedMs = 50;
constexpr uint16_t kMaximumEffectSpeedMs = 60000;
constexpr uint8_t kDiagnosticClearStep = 0;
constexpr uint8_t kDiagnosticRedStep = 1;
constexpr uint8_t kDiagnosticGreenStep = 2;
constexpr uint8_t kDiagnosticBlueStep = 3;
constexpr uint8_t kDiagnosticWhiteStep = 4;
constexpr uint8_t kDiagnosticWalkStep = 5;
constexpr uint8_t kDiagnosticAlternatingStep = 6;
constexpr uint8_t kDiagnosticFinalClearStep = 7;

String normalizedToken(const String& value) {
  String normalized = value;
  normalized.trim();
  normalized.toLowerCase();
  return normalized;
}

bool isSupportedMode(Mode mode) {
  return mode == Mode::kOff || mode == Mode::kSolid || mode == Mode::kBreathe ||
         mode == Mode::kPulse || mode == Mode::kChase || mode == Mode::kRainbow ||
         mode == Mode::kDiagnostic;
}

uint8_t triangleWaveBrightness(unsigned long elapsed, uint16_t period_ms, uint8_t ceiling) {
  if (period_ms == 0 || ceiling == 0) {
    return 0;
  }
  const uint16_t phase = static_cast<uint16_t>(elapsed % period_ms);
  const uint32_t half = std::max<uint16_t>(1, period_ms / 2);
  const uint32_t scaled = phase < half ? phase : period_ms - phase;
  return static_cast<uint8_t>((static_cast<uint32_t>(ceiling) * scaled) / half);
}

RgbColor wheel(uint8_t position) {
  const uint8_t inverse = 255 - position;
  if (inverse < 85) {
    return RgbColor{
        static_cast<uint8_t>(255 - inverse * 3),
        0,
        static_cast<uint8_t>(inverse * 3)};
  }
  if (inverse < 170) {
    const uint8_t shifted = inverse - 85;
    return RgbColor{
        0,
        static_cast<uint8_t>(shifted * 3),
        static_cast<uint8_t>(255 - shifted * 3)};
  }
  const uint8_t shifted = inverse - 170;
  return RgbColor{
      static_cast<uint8_t>(shifted * 3),
      static_cast<uint8_t>(255 - shifted * 3),
      0};
}

bool colorsEqual(const RgbColor& lhs, const RgbColor& rhs) {
  return lhs.r == rhs.r && lhs.g == rhs.g && lhs.b == rhs.b;
}

bool parseColorChannel(JsonObjectConst color, const char* key, uint8_t* value, String* error) {
  if (value == nullptr) {
    return false;
  }
  JsonVariantConst channel = color[key];
  if (channel.isNull()) {
    *value = 0;
    return true;
  }
  if (!channel.is<int>()) {
    if (error != nullptr) {
      *error = "ambient LED belt color channel must be an integer";
    }
    return false;
  }
  const int parsed = channel.as<int>();
  if (parsed < 0 || parsed > 255) {
    if (error != nullptr) {
      *error = "ambient LED belt color channel must be 0-255";
    }
    return false;
  }
  *value = static_cast<uint8_t>(parsed);
  return true;
}

bool validateCommandFields(const AmbientLedBeltCommand& command, const AmbientLedBeltConfig& config, String* error) {
  if (command.has_brightness && (command.brightness < 0 || command.brightness > 255)) {
    if (error != nullptr) {
      *error = "ambient LED belt brightness must be 0-255";
    }
    return false;
  }
  if (command.has_speed_ms &&
      (command.speed_ms < kMinimumEffectSpeedMs || command.speed_ms > kMaximumEffectSpeedMs)) {
    if (error != nullptr) {
      *error = "ambient LED belt speed_ms is invalid";
    }
    return false;
  }
  if (command.has_logical_pixel_count &&
      (command.logical_pixel_count <= 0 || command.logical_pixel_count > AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS)) {
    if (error != nullptr) {
      *error = "ambient LED belt logical pixel count is invalid";
    }
    return false;
  }
  if (command.has_maximum_brightness &&
      (command.maximum_brightness <= 0 || command.maximum_brightness > 255)) {
    if (error != nullptr) {
      *error = "ambient LED belt maximum brightness is invalid";
    }
    return false;
  }
  if (command.has_default_brightness && (command.default_brightness < 0 || command.default_brightness > 255)) {
    if (error != nullptr) {
      *error = "ambient LED belt default brightness is invalid";
    }
    return false;
  }
  if (command.has_default_brightness && !command.has_maximum_brightness &&
      command.default_brightness > config.maximum_brightness) {
    if (error != nullptr) {
      *error = "ambient LED belt default brightness exceeds maximum brightness";
    }
    return false;
  }
  if (command.has_default_brightness && command.has_maximum_brightness &&
      command.default_brightness > command.maximum_brightness) {
    if (error != nullptr) {
      *error = "ambient LED belt default brightness exceeds maximum brightness";
    }
    return false;
  }
  return true;
}

}  // namespace

AmbientLedBeltConfig defaultConfig() {
  AmbientLedBeltConfig config{};
  ColorOrder parsed_order = ColorOrder::kRgb;
  if (parseColorOrder(String(AMBIENT_LED_BELT_COLOR_ORDER), &parsed_order)) {
    config.color_order = parsed_order;
  }
  return config;
}

bool parseColorOrder(const String& value, ColorOrder* order) {
  const String normalized = normalizedToken(value);
  ColorOrder parsed = ColorOrder::kRgb;
  if (normalized == "rgb") {
    parsed = ColorOrder::kRgb;
  } else if (normalized == "rbg") {
    parsed = ColorOrder::kRbg;
  } else if (normalized == "grb") {
    parsed = ColorOrder::kGrb;
  } else if (normalized == "gbr") {
    parsed = ColorOrder::kGbr;
  } else if (normalized == "brg") {
    parsed = ColorOrder::kBrg;
  } else if (normalized == "bgr") {
    parsed = ColorOrder::kBgr;
  } else {
    return false;
  }
  if (order != nullptr) {
    *order = parsed;
  }
  return true;
}

const char* colorOrderName(ColorOrder order) {
  switch (order) {
    case ColorOrder::kRgb:
      return "RGB";
    case ColorOrder::kRbg:
      return "RBG";
    case ColorOrder::kGrb:
      return "GRB";
    case ColorOrder::kGbr:
      return "GBR";
    case ColorOrder::kBrg:
      return "BRG";
    case ColorOrder::kBgr:
      return "BGR";
  }
  return "RGB";
}

bool parseMode(const String& value, Mode* mode) {
  const String normalized = normalizedToken(value);
  Mode parsed = Mode::kOff;
  if (normalized == "off") {
    parsed = Mode::kOff;
  } else if (normalized == "solid") {
    parsed = Mode::kSolid;
  } else if (normalized == "breathe") {
    parsed = Mode::kBreathe;
  } else if (normalized == "pulse") {
    parsed = Mode::kPulse;
  } else if (normalized == "chase") {
    parsed = Mode::kChase;
  } else if (normalized == "rainbow") {
    parsed = Mode::kRainbow;
  } else if (normalized == "diagnostic") {
    parsed = Mode::kDiagnostic;
  } else {
    return false;
  }
  if (mode != nullptr) {
    *mode = parsed;
  }
  return true;
}

const char* modeName(Mode mode) {
  switch (mode) {
    case Mode::kOff:
      return "off";
    case Mode::kSolid:
      return "solid";
    case Mode::kBreathe:
      return "breathe";
    case Mode::kPulse:
      return "pulse";
    case Mode::kChase:
      return "chase";
    case Mode::kRainbow:
      return "rainbow";
    case Mode::kDiagnostic:
      return "diagnostic";
  }
  return "off";
}

RgbColor transportColorForOrder(const RgbColor& color, ColorOrder order) {
  switch (order) {
    case ColorOrder::kRgb:
      return color;
    case ColorOrder::kRbg:
      return RgbColor{color.r, color.b, color.g};
    case ColorOrder::kGrb:
      return RgbColor{color.g, color.r, color.b};
    case ColorOrder::kGbr:
      return RgbColor{color.g, color.b, color.r};
    case ColorOrder::kBrg:
      return RgbColor{color.b, color.r, color.g};
    case ColorOrder::kBgr:
      return RgbColor{color.b, color.g, color.r};
  }
  return color;
}

bool validateConfig(const AmbientLedBeltConfig& config, String* error) {
  if (config.data_gpio < 0 || config.data_gpio > 48) {
    if (error != nullptr) {
      *error = "ambient LED belt data GPIO is invalid";
    }
    return false;
  }
  if (config.logical_pixel_count == 0 || config.logical_pixel_count > AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS) {
    if (error != nullptr) {
      *error = "ambient LED belt logical pixel count is invalid";
    }
    return false;
  }
  if (config.physical_led_count == 0) {
    if (error != nullptr) {
      *error = "ambient LED belt physical LED count is invalid";
    }
    return false;
  }
  if (config.maximum_brightness == 0) {
    if (error != nullptr) {
      *error = "ambient LED belt maximum brightness must be greater than zero";
    }
    return false;
  }
  if (config.default_brightness > config.maximum_brightness) {
    if (error != nullptr) {
      *error = "ambient LED belt default brightness exceeds maximum brightness";
    }
    return false;
  }
  if (config.diagnostic_max_brightness > config.maximum_brightness) {
    if (error != nullptr) {
      *error = "ambient LED belt diagnostic brightness exceeds maximum brightness";
    }
    return false;
  }
  if (config.maximum_frame_rate == 0 || config.maximum_frame_rate > 120) {
    if (error != nullptr) {
      *error = "ambient LED belt maximum frame rate is invalid";
    }
    return false;
  }
  return true;
}

bool parseCommandJson(const String& json, AmbientLedBeltCommand* command, String* error) {
  if (command == nullptr) {
    return false;
  }
  StaticJsonDocument<768> doc;
  const DeserializationError json_error = deserializeJson(doc, json);
  if (json_error) {
    if (error != nullptr) {
      *error = "ambient LED belt command JSON parse failed";
    }
    return false;
  }

  AmbientLedBeltCommand parsed{};
  if (doc["enabled"].is<bool>()) {
    parsed.has_enabled = true;
    parsed.enabled = doc["enabled"].as<bool>();
  }
  if (doc["mode"].is<const char*>()) {
    parsed.has_mode = true;
    if (!parseMode(String(doc["mode"].as<const char*>()), &parsed.mode)) {
      if (error != nullptr) {
        *error = "ambient LED belt mode is invalid";
      }
      return false;
    }
  }
  if (!doc["color"].isNull()) {
    if (!doc["color"].is<JsonObjectConst>()) {
      if (error != nullptr) {
        *error = "ambient LED belt color must be an object";
      }
      return false;
    }
    JsonObjectConst color = doc["color"].as<JsonObjectConst>();
    uint8_t red = 0;
    uint8_t green = 0;
    uint8_t blue = 0;
    if (!parseColorChannel(color, "r", &red, error) ||
        !parseColorChannel(color, "g", &green, error) ||
        !parseColorChannel(color, "b", &blue, error)) {
      return false;
    }
    parsed.has_color = true;
    parsed.color = RgbColor{red, green, blue};
  }
  if (doc["brightness"].is<int>()) {
    parsed.has_brightness = true;
    parsed.brightness = doc["brightness"].as<int>();
  }
  if (doc["speed_ms"].is<int>()) {
    parsed.has_speed_ms = true;
    parsed.speed_ms = doc["speed_ms"].as<int>();
  }
  if (doc["logical_pixel_count"].is<int>()) {
    parsed.has_logical_pixel_count = true;
    parsed.logical_pixel_count = doc["logical_pixel_count"].as<int>();
  }
  if (doc["color_order"].is<const char*>()) {
    parsed.has_color_order = true;
    if (!parseColorOrder(String(doc["color_order"].as<const char*>()), &parsed.color_order)) {
      if (error != nullptr) {
        *error = "ambient LED belt color order is invalid";
      }
      return false;
    }
  }
  if (doc["maximum_brightness"].is<int>()) {
    parsed.has_maximum_brightness = true;
    parsed.maximum_brightness = doc["maximum_brightness"].as<int>();
  }
  if (doc["default_brightness"].is<int>()) {
    parsed.has_default_brightness = true;
    parsed.default_brightness = doc["default_brightness"].as<int>();
  }
  parsed.save_config = doc["save_config"] | false;
  parsed.cancel_diagnostic = doc["cancel_diagnostic"] | false;

  *command = parsed;
  return true;
}

AmbientLedBeltController::AmbientLedBeltController(AmbientLedBeltTransport* transport)
    : transport_(transport), config_(defaultConfig()) {
  state_.logical_pixel_count = config_.logical_pixel_count;
  state_.physical_led_count = config_.physical_led_count;
  state_.color_order = config_.color_order;
  state_.data_gpio = config_.data_gpio;
  state_.requested_color = RgbColor{255, 255, 255};
  state_.requested_brightness = 0;
  state_.effective_brightness = 0;
}

bool AmbientLedBeltController::configure(const AmbientLedBeltConfig& config, String* error) {
  if (state_.initialized) {
    if (error != nullptr) {
      *error = "ambient LED belt cannot be reconfigured after initialization";
    }
    return false;
  }
  if (!validateConfig(config, error)) {
    return false;
  }
  config_ = config;
  state_.logical_pixel_count = config_.logical_pixel_count;
  state_.physical_led_count = config_.physical_led_count;
  state_.color_order = config_.color_order;
  state_.data_gpio = config_.data_gpio;
  resizeBuffer();
  setBlack();
  return true;
}

bool AmbientLedBeltController::begin(String* error) {
  if (transport_ == nullptr) {
    setError("ambient LED belt transport missing");
    if (error != nullptr) {
      *error = state_.last_error;
    }
    return false;
  }
  if (!validateConfig(config_, error)) {
    setError(error == nullptr ? String("ambient LED belt config invalid") : *error);
    return false;
  }
  resizeBuffer();
  setBlack();
  state_.initialized = true;
  state_.available = transport_->begin(config_, error);
  if (!state_.available) {
    setError(error == nullptr ? String("ambient LED belt transport initialization failed") : *error);
    state_.enabled = false;
    state_.mode = Mode::kOff;
    return false;
  }
  state_.enabled = config_.enabled_at_startup;
  state_.mode = config_.enabled_at_startup ? Mode::kSolid : Mode::kOff;
  state_.requested_brightness = config_.enabled_at_startup ? config_.default_brightness : 0;
  state_.effective_brightness = state_.requested_brightness;
  dirty_ = true;
  const bool shown = transmit(0, true);
  frame_clear_sent_ = true;
  return shown;
}

void AmbientLedBeltController::markUnavailable(const String& error) {
  setError(error);
  state_.available = false;
  state_.initialized = false;
  state_.enabled = false;
  state_.mode = Mode::kOff;
  state_.effective_brightness = 0;
  setBlack();
}

void AmbientLedBeltController::shutdown() {
  clear();
  if (transport_ != nullptr) {
    transport_->shutdown();
  }
  state_.available = false;
  state_.initialized = false;
}

void AmbientLedBeltController::clear() {
  state_.enabled = false;
  state_.mode = Mode::kOff;
  state_.diagnostic_active = false;
  state_.requested_brightness = 0;
  state_.effective_brightness = 0;
  setBlack();
  dirty_ = true;
  if (!state_.available) {
    return;
  }
  transmit(state_.last_update_ms, true);
}

bool AmbientLedBeltController::setEnabled(bool enabled, String* error) {
  if (!state_.available) {
    if (error != nullptr) {
      *error = state_.last_error.length() > 0 ? state_.last_error : "ambient LED belt is unavailable";
    }
    return false;
  }
  if (!enabled) {
    clear();
    return true;
  }
  state_.enabled = true;
  if (state_.requested_brightness == 0) {
    state_.requested_brightness = config_.default_brightness;
  }
  if (state_.mode == Mode::kOff || state_.mode == Mode::kDiagnostic) {
    state_.mode = Mode::kSolid;
  }
  setAll(state_.requested_color);
  state_.effective_brightness = state_.requested_brightness;
  dirty_ = true;
  return true;
}

bool AmbientLedBeltController::setBrightness(int brightness, String* error) {
  if (brightness < 0 || brightness > 255) {
    if (error != nullptr) {
      *error = "ambient LED belt brightness must be 0-255";
    }
    return false;
  }
  const uint8_t bounded = boundedBrightness(brightness);
  if (state_.requested_brightness == bounded) {
    return true;
  }
  state_.requested_brightness = bounded;
  state_.effective_brightness = bounded;
  state_.enabled = bounded > 0 && state_.mode != Mode::kOff;
  dirty_ = true;
  return true;
}

bool AmbientLedBeltController::setSolidColor(RgbColor color, int brightness, String* error) {
  if (!state_.available) {
    if (error != nullptr) {
      *error = state_.last_error.length() > 0 ? state_.last_error : "ambient LED belt is unavailable";
    }
    return false;
  }
  state_.diagnostic_active = false;
  state_.enabled = true;
  state_.mode = Mode::kSolid;
  state_.requested_color = color;
  if (brightness >= 0) {
    if (!setBrightness(brightness, error)) {
      return false;
    }
  } else if (state_.requested_brightness == 0) {
    state_.requested_brightness = config_.default_brightness;
  }
  state_.effective_brightness = state_.requested_brightness;
  setAll(color);
  dirty_ = true;
  return true;
}

bool AmbientLedBeltController::setEffect(Mode mode, int speed_ms, String* error) {
  if (!isSupportedMode(mode) || mode == Mode::kDiagnostic) {
    if (error != nullptr) {
      *error = "ambient LED belt effect mode is invalid";
    }
    return false;
  }
  if (!state_.available) {
    if (error != nullptr) {
      *error = state_.last_error.length() > 0 ? state_.last_error : "ambient LED belt is unavailable";
    }
    return false;
  }
  if (mode == Mode::kOff) {
    clear();
    return true;
  }
  if (speed_ms >= 0) {
    state_.effect_speed_ms = boundedSpeed(speed_ms);
  }
  pulse_return_mode_ = state_.mode;
  pulse_return_color_ = state_.requested_color;
  pulse_return_brightness_ = state_.requested_brightness;
  pulse_return_enabled_ = state_.enabled;
  state_.diagnostic_active = false;
  state_.enabled = true;
  if (state_.requested_brightness == 0) {
    state_.requested_brightness = config_.default_brightness;
  }
  state_.effective_brightness = state_.requested_brightness;
  markMode(mode);
  return true;
}

bool AmbientLedBeltController::runDiagnostic(int brightness_override, String* error) {
  if (!state_.available) {
    if (error != nullptr) {
      *error = state_.last_error.length() > 0 ? state_.last_error : "ambient LED belt is unavailable";
    }
    return false;
  }
  uint8_t diagnostic_brightness = config_.diagnostic_max_brightness;
  if (brightness_override >= 0) {
    if (brightness_override > config_.maximum_brightness) {
      diagnostic_brightness = config_.diagnostic_max_brightness;
    } else {
      diagnostic_brightness = static_cast<uint8_t>(brightness_override);
    }
  }
  diagnostic_brightness = std::min<uint8_t>(diagnostic_brightness, config_.diagnostic_max_brightness);

  state_.diagnostic_active = true;
  state_.enabled = true;
  state_.mode = Mode::kDiagnostic;
  state_.requested_brightness = diagnostic_brightness;
  state_.effective_brightness = diagnostic_brightness;
  diagnostic_step_ = kDiagnosticClearStep;
  diagnostic_pixel_ = 0;
  diagnostic_next_ms_ = 0;
  effect_started_ms_ = state_.last_update_ms;
  setBlack();
  dirty_ = true;
  Serial.printf(
      "[ambient-led-belt] diagnostic started brightness=%u logical_pixels=%u color_order=%s\n",
      static_cast<unsigned int>(diagnostic_brightness),
      static_cast<unsigned int>(config_.logical_pixel_count),
      colorOrderName(config_.color_order));
  return true;
}

void AmbientLedBeltController::cancelDiagnostic() {
  if (!state_.diagnostic_active) {
    return;
  }
  Serial.println("[ambient-led-belt] diagnostic cancelled");
  clear();
}

bool AmbientLedBeltController::applyCommand(const AmbientLedBeltCommand& command, String* message, String* error) {
  if (command.cancel_diagnostic) {
    cancelDiagnostic();
    if (message != nullptr) {
      *message = "ambient LED belt diagnostic cancelled";
    }
    return true;
  }

  if (!validateCommandFields(command, config_, error)) {
    return false;
  }

  if (sameCommandState(command)) {
    if (message != nullptr) {
      *message = "ambient LED belt command unchanged";
    }
    return true;
  }

  bool config_changed = false;
  if (command.has_logical_pixel_count || command.has_color_order ||
      command.has_maximum_brightness || command.has_default_brightness) {
    AmbientLedBeltConfig candidate = config_;
    if (command.has_logical_pixel_count) {
      candidate.logical_pixel_count = static_cast<uint16_t>(command.logical_pixel_count);
    }
    if (command.has_color_order) {
      candidate.color_order = command.color_order;
    }
    if (command.has_maximum_brightness) {
      candidate.maximum_brightness = static_cast<uint8_t>(command.maximum_brightness);
      candidate.diagnostic_max_brightness =
          std::min<uint8_t>(candidate.diagnostic_max_brightness, candidate.maximum_brightness);
    }
    if (command.has_default_brightness) {
      candidate.default_brightness = static_cast<uint8_t>(command.default_brightness);
    }
    if (!validateConfig(candidate, error)) {
      return false;
    }
    config_ = candidate;
    config_changed = true;
    state_.logical_pixel_count = config_.logical_pixel_count;
    state_.physical_led_count = config_.physical_led_count;
    state_.color_order = config_.color_order;
    state_.data_gpio = config_.data_gpio;
    state_.requested_brightness = boundedBrightness(state_.requested_brightness);
    state_.effective_brightness = boundedBrightness(state_.effective_brightness);
    resizeBuffer();
    if (!state_.enabled || state_.mode == Mode::kOff) {
      setBlack();
    } else if (state_.mode == Mode::kSolid) {
      setAll(state_.requested_color);
    }
  }

  if (command.has_color) {
    state_.requested_color = command.color;
  }
  if (command.has_speed_ms) {
    if (command.speed_ms < kMinimumEffectSpeedMs || command.speed_ms > kMaximumEffectSpeedMs) {
      if (error != nullptr) {
        *error = "ambient LED belt speed_ms is invalid";
      }
      return false;
    }
    state_.effect_speed_ms = static_cast<uint16_t>(command.speed_ms);
  }
  if (command.has_brightness && !setBrightness(command.brightness, error)) {
    return false;
  }
  if (command.has_mode) {
    if (command.mode == Mode::kDiagnostic) {
      if (!runDiagnostic(command.has_brightness ? command.brightness : -1, error)) {
        return false;
      }
    } else if (command.mode == Mode::kSolid) {
      if (!setSolidColor(
              state_.requested_color,
              command.has_brightness ? state_.requested_brightness : -1,
              error)) {
        return false;
      }
    } else if (!setEffect(command.mode, command.has_speed_ms ? command.speed_ms : -1, error)) {
      return false;
    }
  }
  if (command.has_enabled && !setEnabled(command.enabled, error)) {
    return false;
  }
  if (!command.has_mode && command.has_color) {
    if (!setSolidColor(
            state_.requested_color,
            command.has_brightness ? state_.requested_brightness : -1,
            error)) {
      return false;
    }
  }
  if (config_changed) {
    dirty_ = true;
  }
  if (message != nullptr) {
    *message = "ambient LED belt command applied";
    if (config_changed) {
      *message += command.save_config ? " and config save requested" : " with temporary config";
    }
  }
  return true;
}

bool AmbientLedBeltController::tick(unsigned long now) {
  state_.last_update_ms = now;
  if (!state_.available) {
    return false;
  }
  if (!frame_clear_sent_) {
    setBlack();
    dirty_ = true;
    frame_clear_sent_ = transmit(now, true);
    return frame_clear_sent_;
  }
  const bool advanced = updateEffect(now);
  if (advanced) {
    dirty_ = true;
  }
  return transmit(now);
}

void AmbientLedBeltController::suspendForCameraCapture(unsigned long now) {
  if (suspended_for_camera_) {
    return;
  }
  suspended_for_camera_ = true;
  suspended_was_enabled_ = state_.enabled;
  suspended_mode_ = state_.mode;
  suspended_color_ = state_.requested_color;
  suspended_brightness_ = state_.requested_brightness;
  clear();
  state_.last_update_ms = now;
  Serial.println("[ambient-led-belt] suspended for camera capture");
}

void AmbientLedBeltController::resumeAfterCameraCapture(unsigned long now) {
  if (!suspended_for_camera_) {
    return;
  }
  suspended_for_camera_ = false;
  state_.last_update_ms = now;
  if (!suspended_was_enabled_) {
    clear();
    Serial.println("[ambient-led-belt] camera capture complete, remaining off");
    return;
  }
  state_.enabled = true;
  state_.mode = suspended_mode_;
  state_.requested_color = suspended_color_;
  state_.requested_brightness = suspended_brightness_;
  state_.effective_brightness = suspended_brightness_;
  markMode(state_.mode);
  Serial.println("[ambient-led-belt] resumed after camera capture");
}

const AmbientLedBeltConfig& AmbientLedBeltController::config() const {
  return config_;
}

const AmbientLedBeltState& AmbientLedBeltController::state() const {
  return state_;
}

const RgbColor& AmbientLedBeltController::logicalPixelAt(uint16_t index) const {
  static const RgbColor empty{};
  if (index >= pixels_.size()) {
    return empty;
  }
  return pixels_[index];
}

uint32_t AmbientLedBeltController::transmitted_frame_count() const {
  return transmitted_frame_count_;
}

void AmbientLedBeltController::setError(const String& error) {
  state_.last_error = error;
}

void AmbientLedBeltController::resizeBuffer() {
  pixels_.assign(config_.logical_pixel_count, RgbColor{});
}

void AmbientLedBeltController::setAll(RgbColor color) {
  for (RgbColor& pixel : pixels_) {
    pixel = color;
  }
}

void AmbientLedBeltController::setBlack() {
  setAll(RgbColor{kBlack, kBlack, kBlack});
}

bool AmbientLedBeltController::transmit(unsigned long now, bool force) {
  if (!dirty_ && !force) {
    return false;
  }
  const uint16_t fps = config_.maximum_frame_rate == 0 ? 1 : config_.maximum_frame_rate;
  const unsigned long min_frame_interval_ms = 1000UL / fps;
  if (!force && last_frame_ms_ > 0 && now - last_frame_ms_ < min_frame_interval_ms) {
    return false;
  }
  String error;
  if (!transport_->show(
          pixels_.empty() ? nullptr : pixels_.data(),
          static_cast<uint16_t>(pixels_.size()),
          config_.color_order,
          state_.effective_brightness,
          &error)) {
    setError(error.length() > 0 ? error : String("ambient LED belt frame transmit failed"));
    state_.available = false;
    Serial.printf("[ambient-led-belt] transmit failed: %s\n", state_.last_error.c_str());
    return false;
  }
  dirty_ = false;
  last_frame_ms_ = now;
  ++transmitted_frame_count_;
  return true;
}

bool AmbientLedBeltController::markMode(Mode mode) {
  if (!isSupportedMode(mode)) {
    return false;
  }
  state_.mode = mode;
  effect_started_ms_ = state_.last_update_ms;
  dirty_ = true;
  return true;
}

bool AmbientLedBeltController::updateEffect(unsigned long now) {
  if (!state_.enabled || state_.mode == Mode::kOff) {
    if (state_.effective_brightness != 0) {
      state_.effective_brightness = 0;
      setBlack();
      return true;
    }
    return false;
  }
  switch (state_.mode) {
    case Mode::kSolid:
      if (state_.effective_brightness != state_.requested_brightness) {
        state_.effective_brightness = state_.requested_brightness;
        return true;
      }
      return false;
    case Mode::kBreathe:
      updateBreathe(now);
      return true;
    case Mode::kPulse:
      updatePulse(now);
      return true;
    case Mode::kChase:
      updateChase(now);
      return true;
    case Mode::kRainbow:
      updateRainbow(now);
      return true;
    case Mode::kDiagnostic:
      return updateDiagnostic(now);
    case Mode::kOff:
      break;
  }
  return false;
}

void AmbientLedBeltController::updateBreathe(unsigned long now) {
  setAll(state_.requested_color);
  state_.effective_brightness =
      triangleWaveBrightness(now - effect_started_ms_, state_.effect_speed_ms, state_.requested_brightness);
}

void AmbientLedBeltController::updatePulse(unsigned long now) {
  const unsigned long elapsed = now - effect_started_ms_;
  const uint16_t duration = std::max<uint16_t>(state_.effect_speed_ms, kMinimumEffectSpeedMs);
  if (elapsed >= duration) {
    state_.enabled = pulse_return_enabled_;
    state_.mode = pulse_return_enabled_ ? pulse_return_mode_ : Mode::kOff;
    state_.requested_color = pulse_return_color_;
    state_.requested_brightness = pulse_return_brightness_;
    state_.effective_brightness = state_.requested_brightness;
    if (state_.mode == Mode::kOff || !state_.enabled) {
      setBlack();
    } else {
      setAll(state_.requested_color);
    }
    return;
  }
  setAll(state_.requested_color);
  state_.effective_brightness = triangleWaveBrightness(elapsed, duration, state_.requested_brightness);
}

void AmbientLedBeltController::updateChase(unsigned long now) {
  setBlack();
  if (pixels_.empty()) {
    state_.effective_brightness = 0;
    return;
  }
  const uint16_t period = std::max<uint16_t>(state_.effect_speed_ms, kMinimumEffectSpeedMs);
  const uint16_t index = static_cast<uint16_t>(((now - effect_started_ms_) / period) % pixels_.size());
  pixels_[index] = state_.requested_color;
  state_.effective_brightness = state_.requested_brightness;
}

void AmbientLedBeltController::updateRainbow(unsigned long now) {
  if (pixels_.empty()) {
    state_.effective_brightness = 0;
    return;
  }
  const uint16_t period = std::max<uint16_t>(state_.effect_speed_ms, kMinimumEffectSpeedMs);
  const uint8_t base = static_cast<uint8_t>(((now - effect_started_ms_) / period) & 0xFF);
  for (uint16_t index = 0; index < pixels_.size(); ++index) {
    pixels_[index] = wheel(static_cast<uint8_t>(base + (index * 256U / pixels_.size())));
  }
  state_.effective_brightness = state_.requested_brightness;
}

bool AmbientLedBeltController::updateDiagnostic(unsigned long now) {
  if (!state_.diagnostic_active) {
    clear();
    return false;
  }
  if (diagnostic_next_ms_ > now) {
    return false;
  }
  const uint16_t hold_ms = std::max<uint16_t>(state_.effect_speed_ms, kDefaultEffectSpeedMs);
  switch (diagnostic_step_) {
    case kDiagnosticClearStep:
      setBlack();
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticRedStep;
      return true;
    case kDiagnosticRedStep:
      setAll(RgbColor{255, 0, 0});
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticGreenStep;
      return true;
    case kDiagnosticGreenStep:
      setAll(RgbColor{0, 255, 0});
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticBlueStep;
      return true;
    case kDiagnosticBlueStep:
      setAll(RgbColor{0, 0, 255});
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticWhiteStep;
      return true;
    case kDiagnosticWhiteStep:
      setAll(RgbColor{255, 255, 255});
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticWalkStep;
      diagnostic_pixel_ = 0;
      return true;
    case kDiagnosticWalkStep:
      setBlack();
      if (diagnostic_pixel_ < pixels_.size()) {
        pixels_[diagnostic_pixel_] = RgbColor{255, 255, 255};
        ++diagnostic_pixel_;
        diagnostic_next_ms_ = now + std::max<uint16_t>(100, hold_ms / 4);
        return true;
      }
      diagnostic_step_ = kDiagnosticAlternatingStep;
      diagnostic_next_ms_ = now;
      return true;
    case kDiagnosticAlternatingStep:
      for (uint16_t index = 0; index < pixels_.size(); ++index) {
        pixels_[index] = (index % 2 == 0) ? RgbColor{255, 255, 255} : RgbColor{0, 0, 0};
      }
      diagnostic_next_ms_ = now + hold_ms;
      diagnostic_step_ = kDiagnosticFinalClearStep;
      return true;
    case kDiagnosticFinalClearStep:
    default:
      setBlack();
      state_.diagnostic_active = false;
      state_.enabled = false;
      state_.mode = Mode::kOff;
      state_.requested_brightness = 0;
      state_.effective_brightness = 0;
      diagnostic_step_ = 0;
      Serial.println("[ambient-led-belt] diagnostic finished");
      return true;
  }
}

uint8_t AmbientLedBeltController::boundedBrightness(int brightness) const {
  if (brightness <= 0) {
    return 0;
  }
  return static_cast<uint8_t>(std::min(brightness, static_cast<int>(config_.maximum_brightness)));
}

uint16_t AmbientLedBeltController::boundedSpeed(int speed_ms) const {
  if (speed_ms < kMinimumEffectSpeedMs) {
    return kMinimumEffectSpeedMs;
  }
  if (speed_ms > kMaximumEffectSpeedMs) {
    return kMaximumEffectSpeedMs;
  }
  return static_cast<uint16_t>(speed_ms);
}

bool AmbientLedBeltController::sameCommandState(const AmbientLedBeltCommand& command) const {
  if (command.has_enabled && command.enabled != state_.enabled) {
    return false;
  }
  if (command.has_mode && command.mode != state_.mode) {
    return false;
  }
  if (command.has_color && !colorsEqual(command.color, state_.requested_color)) {
    return false;
  }
  if (command.has_brightness && boundedBrightness(command.brightness) != state_.requested_brightness) {
    return false;
  }
  if (command.has_speed_ms && boundedSpeed(command.speed_ms) != state_.effect_speed_ms) {
    return false;
  }
  if (command.has_logical_pixel_count &&
      command.logical_pixel_count != static_cast<int>(config_.logical_pixel_count)) {
    return false;
  }
  if (command.has_color_order && command.color_order != config_.color_order) {
    return false;
  }
  if (command.has_maximum_brightness && command.maximum_brightness != config_.maximum_brightness) {
    return false;
  }
  if (command.has_default_brightness && command.default_brightness != config_.default_brightness) {
    return false;
  }
  return command.has_enabled || command.has_mode || command.has_color || command.has_brightness ||
         command.has_speed_ms || command.has_logical_pixel_count || command.has_color_order ||
         command.has_maximum_brightness || command.has_default_brightness;
}

}  // namespace ambient_led_belt
}  // namespace plantlab
