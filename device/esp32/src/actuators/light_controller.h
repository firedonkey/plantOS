#pragma once

#include "actuators/mosfet_actuator.h"

class LightController {
 public:
  LightController(int pin, int on_level, int off_level);
  void begin();
  void set_on(bool on);
  void toggle();
  bool is_on() const;

 private:
  MosfetActuator actuator_;
};
