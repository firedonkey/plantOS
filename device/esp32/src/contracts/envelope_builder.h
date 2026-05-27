#pragma once

#include <Arduino.h>

namespace plantlab {
namespace contracts {

bool buildHeartbeatEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* node_status,
    const char* firmware_version,
    const char* hardware_model,
    const char* hardware_version,
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
