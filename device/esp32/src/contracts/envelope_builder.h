#pragma once

#include <Arduino.h>

namespace plantlab {
namespace contracts {

struct HeartbeatWaterLevelPadRuntime {
  const char* name = "";
  int gpio = -1;
  int touch_channel = -1;
  bool available = false;
  bool calibrated = false;
  bool wet = false;
  bool stable = false;
  uint32_t raw = 0;
  uint32_t filtered = 0;
  uint32_t threshold = 0;
  uint32_t hysteresis = 0;
  uint32_t dry_baseline = 0;
  uint32_t wet_reference = 0;
  int32_t margin = 0;
  uint16_t read_failures = 0;
};

struct HeartbeatWaterLevelRuntime {
  bool available = false;
  bool calibrated = false;
  bool stable = false;
  const char* state = "";
  const char* instantaneous_state = "";
  const char* quality = "";
  const char* reason = "";
  int percent = 0;
  uint32_t representative_raw = 0;
  HeartbeatWaterLevelPadRuntime pads[3]{};
};

bool buildHeartbeatEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* node_status,
    const char* firmware_version,
    const char* hardware_model,
    const char* hardware_version,
    const char* camera_role,
    uint32_t uptime_seconds,
    bool has_wifi_rssi_dbm,
    int wifi_rssi_dbm,
    const char* ip_address,
    bool has_free_heap_bytes,
    uint32_t free_heap_bytes,
    bool include_light_state,
    bool light_enabled,
    int light_brightness_percent,
    bool has_capture_interval_seconds,
    uint32_t capture_interval_seconds,
    const char* ota_status,
    const char* provisioning_status,
    const char* camera_node_status,
    const char* last_command_id,
    const char* last_command_status,
    const char* last_command_poll_at,
    const char* last_command_poll_status,
    const char* last_command_poll_error,
    bool has_last_command_poll_latency_ms,
    uint32_t last_command_poll_latency_ms,
    bool has_command_poll_stale_seconds,
    uint32_t command_poll_stale_seconds,
    bool include_ambient_led_belt_state,
    bool ambient_led_belt_available,
    bool ambient_led_belt_enabled,
    const char* ambient_led_belt_mode,
    int ambient_led_belt_brightness,
    int ambient_led_belt_max_brightness,
    int ambient_led_belt_color_r,
    int ambient_led_belt_color_g,
    int ambient_led_belt_color_b,
    int ambient_led_belt_logical_pixel_count,
    int ambient_led_belt_physical_led_count,
    const char* ambient_led_belt_color_order,
    int ambient_led_belt_data_gpio,
    bool ambient_led_belt_diagnostic_active,
    const char* ambient_led_belt_last_error,
    const HeartbeatWaterLevelRuntime* water_level_runtime,
    String* body);

bool buildCommandResultEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* command_id,
    const char* command_type,
    const char* status,
    const char* message,
    bool light_on,
    bool pump_on,
    int light_intensity_percent,
    const char* error_code,
    bool include_actuator_state,
    String* body);

bool buildOtaStatusEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* command_id,
    const char* status,
    const char* release_id,
    const char* target_version,
    const char* current_version,
    int progress,
    const char* firmware_channel,
    const char* phase,
    const char* failure_reason,
    const char* message,
    String* body);

}  // namespace contracts
}  // namespace plantlab
