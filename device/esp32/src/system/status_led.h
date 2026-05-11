#pragma once

#include <stdint.h>

enum class StatusLedMode {
  kBooting = 0,
  kOff,
  kNormal,
  kProvisioning,
  kSleepPending,
};

class StatusLed {
 public:
  StatusLed(int pin, int on_level, int off_level);

  void begin();
  void set_mode(StatusLedMode mode);
  void signal_user_feedback(uint32_t now_ms);
  void update(uint32_t now_ms);

 private:
  void apply(bool on);

  int pin_;
  int on_level_;
  int off_level_;
  StatusLedMode mode_;
  bool is_on_;
  uint32_t feedback_until_ms_;
};
