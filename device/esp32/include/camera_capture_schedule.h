#pragma once

#include <stdint.h>

struct MasterCaptureScheduleState {
  bool enabled = false;
  uint32_t interval_ms = 0;
  uint32_t last_capture_requested_ms = 0;
  bool has_sent_initial_request = false;
};

inline void capture_schedule_init(
    MasterCaptureScheduleState* state,
    bool enabled,
    uint32_t interval_ms) {
  if (state == nullptr) {
    return;
  }
  state->enabled = enabled;
  state->interval_ms = interval_ms;
  state->last_capture_requested_ms = 0;
  state->has_sent_initial_request = false;
}

inline bool capture_schedule_should_request(
    const MasterCaptureScheduleState& state,
    uint32_t now_ms,
    bool runtime_ready) {
  if (!runtime_ready || !state.enabled || state.interval_ms == 0) {
    return false;
  }
  if (!state.has_sent_initial_request) {
    return true;
  }
  return now_ms - state.last_capture_requested_ms >= state.interval_ms;
}

inline void capture_schedule_mark_requested(MasterCaptureScheduleState* state, uint32_t now_ms) {
  if (state == nullptr) {
    return;
  }
  state->has_sent_initial_request = true;
  state->last_capture_requested_ms = now_ms;
}
