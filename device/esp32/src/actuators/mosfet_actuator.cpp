#include "actuators/mosfet_actuator.h"

#include <Arduino.h>

MosfetActuator::MosfetActuator(int pin, int on_level, int off_level)
    : pin_(pin), on_level_(on_level), off_level_(off_level), is_on_(false) {}

void MosfetActuator::begin() {
  pinMode(pin_, OUTPUT);
  set_on(false);
}

void MosfetActuator::set_on(bool on) {
  is_on_ = on;
  digitalWrite(pin_, is_on_ ? on_level_ : off_level_);
}

void MosfetActuator::toggle() {
  set_on(!is_on_);
}

bool MosfetActuator::is_on() const {
  return is_on_;
}
