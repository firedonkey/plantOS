#pragma once

#include "actuators/mosfet_actuator.h"

class LightController {
 public:
  LightController(int pin, int on_level, int off_level, bool intensity_control_enabled = false);
  void begin();
  void set_on(bool on);
  bool set_intensity_percent(int percent);
  void toggle();
  bool is_on() const;
  int intensity_percent() const;
  bool supports_intensity_control() const;

 private:
  MosfetActuator actuator_;
  int pin_;
  int on_level_;
  int off_level_;
  bool intensity_control_enabled_;
  int intensity_percent_;
  int pwm_duty_for_percent(int percent) const;
};
