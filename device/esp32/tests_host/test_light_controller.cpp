#include <Arduino.h>

#include "actuators/light_controller.h"
#include "config.h"

#include <cassert>
#include <map>

namespace {
constexpr int kUnset = -1;

struct PinState {
  int mode = kUnset;
  int digital = kUnset;
  int pwm = kUnset;
};

std::map<int, PinState> g_pin_states;

PinState stateFor(int pin) {
  const auto found = g_pin_states.find(pin);
  return found == g_pin_states.end() ? PinState{} : found->second;
}

void resetPins() {
  g_pin_states.clear();
}

void assertBothPwm(int duty) {
  assert(stateFor(PIN_GROW_LIGHT_RED_CTRL).pwm == duty);
  assert(stateFor(PIN_GROW_LIGHT_WHITE_CTRL).pwm == duty);
}

void assertOnlyPrimaryPwm(int primary_pin, int secondary_pin, int duty) {
  assert(stateFor(primary_pin).pwm == duty);
  assert(stateFor(secondary_pin).pwm == kUnset);
}

}  // namespace

void pinMode(int pin, int mode) {
  g_pin_states[pin].mode = mode;
}

void digitalWrite(int pin, int level) {
  g_pin_states[pin].digital = level;
}

void analogWrite(int pin, int duty) {
  g_pin_states[pin].pwm = duty;
}

int main() {
  static_assert(PIN_GROW_LIGHT_RED_CTRL == 18, "red grow-light CTRL must be GPIO18");
  static_assert(PIN_GROW_LIGHT_WHITE_CTRL == 8, "white grow-light CTRL must be GPIO8");

  resetPins();
  LightController grow_light(
      PIN_GROW_LIGHT_RED_CTRL,
      PIN_GROW_LIGHT_WHITE_CTRL,
      ACTUATOR_ON_LEVEL,
      ACTUATOR_OFF_LEVEL,
      true);
  grow_light.begin();
  assert(grow_light.has_secondary_channel());
  assert(grow_light.primary_pin() == PIN_GROW_LIGHT_RED_CTRL);
  assert(grow_light.secondary_pin() == PIN_GROW_LIGHT_WHITE_CTRL);
  assert(stateFor(PIN_GROW_LIGHT_RED_CTRL).mode == OUTPUT);
  assert(stateFor(PIN_GROW_LIGHT_WHITE_CTRL).mode == OUTPUT);
  assertBothPwm(0);
  assert(!grow_light.is_on());

  grow_light.set_on(true);
  assert(grow_light.is_on());
  assert(grow_light.intensity_percent() == 100);
  assert(grow_light.primary_intensity_percent() == 100);
  assert(grow_light.secondary_intensity_percent() == 100);
  assertBothPwm(255);

  assert(grow_light.set_intensity_percent(5));
  assert(grow_light.is_on());
  assert(grow_light.intensity_percent() == 5);
  assert(grow_light.primary_intensity_percent() == 5);
  assert(grow_light.secondary_intensity_percent() == 5);
  assertBothPwm(12);

  assert(grow_light.set_primary_intensity_percent(20));
  assert(grow_light.is_on());
  assert(grow_light.intensity_percent() == 20);
  assert(grow_light.primary_intensity_percent() == 20);
  assert(grow_light.secondary_intensity_percent() == 5);
  assert(stateFor(PIN_GROW_LIGHT_RED_CTRL).pwm == 51);
  assert(stateFor(PIN_GROW_LIGHT_WHITE_CTRL).pwm == 12);

  assert(grow_light.set_secondary_intensity_percent(0));
  assert(grow_light.is_on());
  assert(grow_light.intensity_percent() == 20);
  assert(grow_light.primary_intensity_percent() == 20);
  assert(grow_light.secondary_intensity_percent() == 0);
  assert(stateFor(PIN_GROW_LIGHT_RED_CTRL).pwm == 51);
  assert(stateFor(PIN_GROW_LIGHT_WHITE_CTRL).pwm == 0);

  assert(grow_light.set_intensity_percent(0));
  assert(!grow_light.is_on());
  assert(grow_light.intensity_percent() == 0);
  assert(grow_light.primary_intensity_percent() == 0);
  assert(grow_light.secondary_intensity_percent() == 0);
  assertBothPwm(0);

  grow_light.toggle();
  assert(grow_light.is_on());
  assert(grow_light.intensity_percent() == 100);
  assertBothPwm(255);

  resetPins();
  LightController legacy_single_channel(15, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL, true);
  legacy_single_channel.begin();
  legacy_single_channel.set_on(true);
  assert(!legacy_single_channel.has_secondary_channel());
  assertOnlyPrimaryPwm(15, PIN_GROW_LIGHT_WHITE_CTRL, 255);

  return 0;
}
