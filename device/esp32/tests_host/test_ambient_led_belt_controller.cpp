#include "ambient_led_belt/ambient_led_belt_controller.h"

#include <cassert>
#include <string>
#include <vector>

using plantlab::ambient_led_belt::ColorOrder;
using plantlab::ambient_led_belt::AmbientLedBeltCommand;
using plantlab::ambient_led_belt::AmbientLedBeltConfig;
using plantlab::ambient_led_belt::AmbientLedBeltController;
using plantlab::ambient_led_belt::AmbientLedBeltTransport;
using plantlab::ambient_led_belt::Mode;
using plantlab::ambient_led_belt::RgbColor;

namespace {

struct CapturedFrame {
  std::vector<RgbColor> pixels;
  uint16_t count = 0;
  ColorOrder color_order = ColorOrder::kRgb;
  uint8_t brightness = 0;
};

class FakeTransport : public AmbientLedBeltTransport {
 public:
  bool begin(const AmbientLedBeltConfig& config, String* error) override {
    if (!begin_ok) {
      if (error != nullptr) {
        *error = "transport unavailable";
      }
      return false;
    }
    initialized = true;
    begin_config = config;
    return true;
  }

  bool show(
      const RgbColor* logical_pixels,
      uint16_t count,
      ColorOrder color_order,
      uint8_t brightness,
      String* error) override {
    if (!initialized) {
      if (error != nullptr) {
        *error = "transport not initialized";
      }
      return false;
    }
    if (fail_next_show) {
      fail_next_show = false;
      if (error != nullptr) {
        *error = "show failed";
      }
      return false;
    }
    CapturedFrame frame;
    frame.count = count;
    frame.color_order = color_order;
    frame.brightness = brightness;
    frame.pixels.reserve(count);
    for (uint16_t index = 0; index < count; ++index) {
      frame.pixels.push_back(logical_pixels == nullptr ? RgbColor{} : logical_pixels[index]);
    }
    frames.push_back(frame);
    return true;
  }

  void shutdown() override {
    initialized = false;
    shutdown_called = true;
  }

  bool begin_ok = true;
  bool fail_next_show = false;
  bool initialized = false;
  bool shutdown_called = false;
  AmbientLedBeltConfig begin_config;
  std::vector<CapturedFrame> frames;
};

void assertColor(const RgbColor& color, uint8_t r, uint8_t g, uint8_t b) {
  assert(color.r == r);
  assert(color.g == g);
  assert(color.b == b);
}

void assertFrameBlack(const CapturedFrame& frame) {
  for (const RgbColor& pixel : frame.pixels) {
    assertColor(pixel, 0, 0, 0);
  }
}

void assertFrameSolid(const CapturedFrame& frame, uint8_t r, uint8_t g, uint8_t b) {
  for (const RgbColor& pixel : frame.pixels) {
    assertColor(pixel, r, g, b);
  }
}

AmbientLedBeltCommand parseCommand(const char* json) {
  AmbientLedBeltCommand command;
  String error;
  assert(plantlab::ambient_led_belt::parseCommandJson(String(json), &command, &error));
  return command;
}

bool applyJson(AmbientLedBeltController& controller, const char* json, String* message, String* error) {
  AmbientLedBeltCommand command = parseCommand(json);
  return controller.applyCommand(command, message, error);
}

}  // namespace

int main() {
  AmbientLedBeltConfig config = plantlab::ambient_led_belt::defaultConfig();
  assert(config.data_gpio == 1);
  assert(config.logical_pixel_count == 14);
  assert(config.physical_led_count == 630);
  assert(config.color_order == ColorOrder::kRgb);
  assert(config.maximum_brightness == 51);
  assert(config.default_brightness == 26);
  assert(!config.enabled_at_startup);

  FakeTransport transport;
  AmbientLedBeltController controller(&transport);
  String message;
  String error;

  assert(controller.configure(config, &error));
  assert(controller.begin(&error));
  assert(transport.begin_config.logical_pixel_count == 14);
  assert(transport.frames.size() == 1);
  assert(transport.frames.back().count == 14);
  assert(transport.frames.back().brightness == 0);
  assertFrameBlack(transport.frames.back());
  assert(!controller.state().enabled);
  assert(controller.state().mode == Mode::kOff);

  assert(applyJson(
      controller,
      R"json({"enabled":true,"mode":"solid","color":{"r":255,"g":0,"b":0},"brightness":26})json",
      &message,
      &error));
  assert(controller.tick(40));
  assert(transport.frames.size() == 2);
  assert(transport.frames.back().brightness == 26);
  assertFrameSolid(transport.frames.back(), 255, 0, 0);

  assert(applyJson(controller, R"json({"mode":"off"})json", &message, &error));
  assert(applyJson(controller, R"json({"enabled":true})json", &message, &error));
  assert(controller.tick(80));
  assert(transport.frames.back().brightness == 26);
  assertFrameSolid(transport.frames.back(), 255, 0, 0);

  AmbientLedBeltCommand invalid_color;
  assert(!plantlab::ambient_led_belt::parseCommandJson(
      String(R"json({"color":{"r":300,"g":0,"b":0}})json"),
      &invalid_color,
      &error));
  assert(std::string(error.c_str()) == "ambient LED belt color channel must be 0-255");

  const RgbColor mapped_red = plantlab::ambient_led_belt::transportColorForOrder(RgbColor{255, 0, 0}, ColorOrder::kBrg);
  assertColor(mapped_red, 0, 255, 0);

  assert(applyJson(
      controller,
      R"json({"enabled":true,"mode":"solid","color":{"r":255,"g":0,"b":0},"brightness":26})json",
      &message,
      &error));
  assert(std::string(message.c_str()) == "ambient LED belt command unchanged");
  assert(!controller.tick(120));

  assert(applyJson(
      controller,
      R"json({"mode":"solid","color":{"r":0,"g":255,"b":0},"brightness":200})json",
      &message,
      &error));
  assert(controller.state().requested_brightness == 51);
  assert(controller.tick(160));
  assert(transport.frames.back().brightness == 51);
  assertFrameSolid(transport.frames.back(), 0, 255, 0);

  assert(applyJson(
      controller,
      R"json({"logical_pixel_count":20,"color_order":"RGB","maximum_brightness":40,"default_brightness":20,"save_config":true,"mode":"solid","color":{"r":0,"g":0,"b":255},"brightness":40})json",
      &message,
      &error));
  assert(controller.config().logical_pixel_count == 20);
  assert(controller.config().color_order == ColorOrder::kRgb);
  assert(controller.config().maximum_brightness == 40);
  assert(controller.config().default_brightness == 20);
  assert(controller.tick(200));
  assert(transport.frames.back().count == 20);
  assert(transport.frames.back().brightness == 40);
  assertFrameSolid(transport.frames.back(), 0, 0, 255);

  assert(applyJson(
      controller,
      R"json({"mode":"chase","color":{"r":255,"g":255,"b":255},"brightness":10,"speed_ms":50})json",
      &message,
      &error));
  assert(controller.tick(260));
  assert(controller.logicalPixelAt(0).r == 255 || controller.logicalPixelAt(1).r == 255);
  assert(transport.frames.back().brightness == 10);

  AmbientLedBeltCommand invalid_speed = parseCommand(R"json({"mode":"chase","speed_ms":10})json");
  assert(!controller.applyCommand(invalid_speed, &message, &error));
  assert(std::string(error.c_str()) == "ambient LED belt speed_ms is invalid");

  assert(applyJson(
      controller,
      R"json({"mode":"breathe","color":{"r":0,"g":0,"b":255},"brightness":20,"speed_ms":1000})json",
      &message,
      &error));
  assert(controller.tick(320));
  const uint8_t breathe_start = controller.state().effective_brightness;
  assert(controller.tick(570));
  assert(controller.state().effective_brightness > breathe_start);
  assert(controller.state().effective_brightness <= 20);

  assert(applyJson(
      controller,
      R"json({"mode":"diagnostic","brightness":100})json",
      &message,
      &error));
  assert(controller.state().diagnostic_active);
  assert(controller.state().requested_brightness <= 26);
  assert(controller.tick(1000));
  assertFrameBlack(transport.frames.back());
  assert(transport.frames.back().brightness <= 26);
  assert(!controller.tick(1500));
  assert(controller.tick(2000));
  assertFrameSolid(transport.frames.back(), 255, 0, 0);
  assert(controller.tick(3000));
  assertFrameSolid(transport.frames.back(), 0, 255, 0);
  assert(controller.tick(4000));
  assertFrameSolid(transport.frames.back(), 0, 0, 255);
  assert(controller.tick(5000));
  assertFrameSolid(transport.frames.back(), 255, 255, 255);

  assert(applyJson(controller, R"json({"cancel_diagnostic":true})json", &message, &error));
  assert(!controller.state().diagnostic_active);
  assert(controller.state().mode == Mode::kOff);
  assertFrameBlack(transport.frames.back());

  assert(applyJson(controller, R"json({"mode":"off"})json", &message, &error));
  assert(controller.state().mode == Mode::kOff);
  assert(!controller.state().enabled);
  assertFrameBlack(transport.frames.back());

  FakeTransport failing_transport;
  failing_transport.begin_ok = false;
  AmbientLedBeltController unavailable_controller(&failing_transport);
  assert(!unavailable_controller.begin(&error));
  assert(!unavailable_controller.state().available);
  assert(!applyJson(unavailable_controller, R"json({"mode":"solid","brightness":10})json", &message, &error));

  return 0;
}
