#include <assert.h>
#include <stdint.h>

#include "camera_capture_schedule.h"

namespace {
void test_disabled_schedule_never_requests() {
  MasterCaptureScheduleState state{};
  capture_schedule_init(&state, false, 15000UL);
  assert(!capture_schedule_should_request(state, 0, true));
  assert(!capture_schedule_should_request(state, 20000UL, true));
}

void test_schedule_waits_for_runtime_ready() {
  MasterCaptureScheduleState state{};
  capture_schedule_init(&state, true, 15000UL);
  assert(!capture_schedule_should_request(state, 0, false));
  assert(capture_schedule_should_request(state, 0, true));
}

void test_schedule_respects_interval_after_first_request() {
  MasterCaptureScheduleState state{};
  capture_schedule_init(&state, true, 15000UL);
  assert(capture_schedule_should_request(state, 1000UL, true));
  capture_schedule_mark_requested(&state, 1000UL);
  assert(!capture_schedule_should_request(state, 12000UL, true));
  assert(capture_schedule_should_request(state, 16001UL, true));
}
}  // namespace

int main() {
  test_disabled_schedule_never_requests();
  test_schedule_waits_for_runtime_ready();
  test_schedule_respects_interval_after_first_request();
  return 0;
}
