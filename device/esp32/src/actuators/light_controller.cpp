#include "actuators/light_controller.h"

LightController::LightController(int pin, int on_level, int off_level)
    : actuator_(pin, on_level, off_level) {}

void LightController::begin() {
  actuator_.begin();
}

void LightController::set_on(bool on) {
  actuator_.set_on(on);
}

void LightController::toggle() {
  actuator_.toggle();
}

bool LightController::is_on() const {
  return actuator_.is_on();
}
