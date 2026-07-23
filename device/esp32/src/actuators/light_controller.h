#pragma once

class LightController {
 public:
  LightController(int pin, int on_level, int off_level, bool intensity_control_enabled = false);
  LightController(
      int primary_pin,
      int secondary_pin,
      int on_level,
      int off_level,
      bool intensity_control_enabled = false);
  void begin();
  void set_on(bool on);
  bool set_intensity_percent(int percent);
  void toggle();
  bool is_on() const;
  int intensity_percent() const;
  bool supports_intensity_control() const;
  bool has_secondary_channel() const;
  int primary_pin() const;
  int secondary_pin() const;

 private:
  int primary_pin_;
  int secondary_pin_;
  int on_level_;
  int off_level_;
  bool intensity_control_enabled_;
  int intensity_percent_;
  bool is_on_;
  int pwm_duty_for_percent(int percent) const;
  void write_digital_all(int level);
  void write_pwm_all(int duty);
};
