#pragma once

#include "ambient_led_belt/ambient_led_belt_controller.h"

namespace plantlab {
namespace ambient_led_belt {

class FastAmbientLedBeltTransport : public AmbientLedBeltTransport {
 public:
  bool begin(const AmbientLedBeltConfig& config, String* error) override;
  bool show(
      const RgbColor* logical_pixels,
      uint16_t count,
      ColorOrder color_order,
      uint8_t brightness,
      String* error) override;
  void shutdown() override;

 private:
  bool initialized_ = false;
  uint16_t count_ = 0;
};

}  // namespace ambient_led_belt
}  // namespace plantlab
