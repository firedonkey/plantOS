#pragma once

class MosfetActuator {
 public:
  MosfetActuator(int pin, int on_level, int off_level);
  void begin();
  void set_on(bool on);
  void toggle();
  bool is_on() const;

 private:
  int pin_;
  int on_level_;
  int off_level_;
  bool is_on_;
};
