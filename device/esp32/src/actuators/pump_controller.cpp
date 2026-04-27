#include "actuators/pump_controller.h"

#include <Arduino.h>

PumpController::PumpController(int pin, int on_level, int off_level)
    : actuator_(pin, on_level, off_level),
      timed_run_active_(false),
      stop_at_ms_(0) {}

void PumpController::begin() {
  actuator_.begin();
  timed_run_active_ = false;
  stop_at_ms_ = 0;
}

void PumpController::set_on(bool on) {
  actuator_.set_on(on);
  if (!on) {
    timed_run_active_ = false;
    stop_at_ms_ = 0;
  }
}

void PumpController::start_for_ms(unsigned long duration_ms) {
  actuator_.set_on(true);
  timed_run_active_ = true;
  stop_at_ms_ = millis() + duration_ms;
}

void PumpController::stop() {
  set_on(false);
}

void PumpController::update() {
  if (!timed_run_active_) {
    return;
  }
  if (static_cast<long>(millis() - stop_at_ms_) >= 0) {
    stop();
  }
}

bool PumpController::is_on() const {
  return actuator_.is_on();
}

bool PumpController::is_timed_run_active() const {
  return timed_run_active_;
}
