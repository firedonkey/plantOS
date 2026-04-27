#pragma once

#include "actuators/mosfet_actuator.h"

class PumpController {
 public:
  PumpController(int pin, int on_level, int off_level);
  void begin();
  void set_on(bool on);
  void start_for_ms(unsigned long duration_ms);
  void stop();
  void update();
  bool is_on() const;
  bool is_timed_run_active() const;

 private:
  MosfetActuator actuator_;
  bool timed_run_active_;
  unsigned long stop_at_ms_;
};
