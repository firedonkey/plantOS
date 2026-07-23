#pragma once

#include <Arduino.h>

using OtaChunkCallback = bool (*)(const uint8_t* bytes, size_t length, void* context);

struct PlatformCommand {
  int id;
  String target;
  String action;
  String value;
  String command_id;
  String command_type;
  String target_node_role;
  String target_hardware_device_id;
  String target_camera_role;
  String ota_target_version;
  String ota_download_url;
  String ota_checksum_sha256;
  String ota_hardware_model;
  String ota_firmware_channel;
  String ota_release_id;
  String ambient_led_belt_payload_json;
  size_t ota_artifact_size_bytes = 0;
  bool contract_native = false;
  bool valid;
};

struct PlatformReading {
  String hardware_device_id;
  float temperature_c;
  float humidity_percent;
  float moisture_percent;
  float water_temperature_c;
  int water_level_raw = 0;
  bool temperature_valid;
  bool humidity_valid;
  bool moisture_valid;
  bool water_temperature_valid = false;
  bool water_level_valid = false;
  String water_level_state;
  bool light_on;
  int light_intensity_percent = -1;
  bool pump_on;
  String pump_status;
  String idempotency_key;
};

struct PlatformErrorCounters {
  uint32_t wifi_reconnects = 0;
  uint32_t upload_failures = 0;
  uint32_t ble_provisioning_failures = 0;
  uint32_t espnow_failures = 0;
};

struct PlatformDiagnostics {
  bool valid = false;
  bool has_uptime_seconds = false;
  uint32_t uptime_seconds = 0;
  bool has_wifi_rssi_dbm = false;
  int wifi_rssi_dbm = 0;
  String reboot_reason;
  String provisioning_state;
  bool has_last_sensor_reading_age_seconds = false;
  uint32_t last_sensor_reading_age_seconds = 0;
  bool has_last_camera_image_upload_age_seconds = false;
  uint32_t last_camera_image_upload_age_seconds = 0;
  bool has_last_command = false;
  int last_command_id = 0;
  String last_command_status;
  String last_command_code;
  String last_command_message;
  bool has_last_command_age_seconds = false;
  uint32_t last_command_age_seconds = 0;
  bool has_error_counters = false;
  PlatformErrorCounters error_counters;
  String last_error_code;
  String last_error_message;
};

struct PlatformAmbientLedBeltState {
  bool available = false;
  bool enabled = false;
  String mode;
  int brightness = 0;
  int max_brightness = 0;
  int color_r = 0;
  int color_g = 0;
  int color_b = 0;
  int logical_pixel_count = 0;
  int physical_led_count = 0;
  String color_order;
  int data_gpio = -1;
  bool diagnostic_active = false;
  String last_error;
};

struct PlatformWaterLevelPadState {
  String name;
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

struct PlatformWaterLevelState {
  bool available = false;
  bool calibrated = false;
  bool stable = false;
  String state;
  String instantaneous_state;
  String quality;
  String reason;
  int percent = 0;
  uint32_t representative_raw = 0;
  PlatformWaterLevelPadState pads[3]{};
};

struct PlatformStatus {
  String hardware_device_id;
  String node_role;
  String status;
  String hardware_model;
  String hardware_version;
  String camera_role;
  String ip_address;
  bool has_free_heap_bytes = false;
  uint32_t free_heap_bytes = 0;
  bool has_light_state = false;
  bool light_on = false;
  int light_intensity_percent = -1;
  bool pump_on = false;
  String message;
  String software_version;
  bool has_capture_interval_seconds = false;
  uint32_t capture_interval_seconds = 0;
  String ota_status;
  String provisioning_status;
  String camera_node_status;
  String last_command_contract_id;
  String last_command_status;
  String last_command_poll_at;
  String last_command_poll_status;
  String last_command_poll_error;
  bool has_last_command_poll_latency_ms = false;
  uint32_t last_command_poll_latency_ms = 0;
  bool has_command_poll_stale_seconds = false;
  uint32_t command_poll_stale_seconds = 0;
  bool has_ambient_led_belt_state = false;
  PlatformAmbientLedBeltState ambient_led_belt;
  bool has_water_level_state = false;
  PlatformWaterLevelState water_level;
  PlatformDiagnostics diagnostics;
};

class PlatformClient {
 public:
  PlatformClient(const char* base_url, int device_id, const char* device_token);

  bool configured() const;
  const String& base_url() const;
  int device_id() const;

  bool send_reading(const PlatformReading& reading, String* error = nullptr);
  bool send_hardware_reading(const PlatformReading& reading, String* error = nullptr);
  bool send_status(const PlatformStatus& status, String* error = nullptr);
  bool send_hardware_heartbeat(const PlatformStatus& status, String* error = nullptr);
  int poll_pending_commands(PlatformCommand* commands, size_t max_commands, String* error = nullptr);
  int poll_hardware_pending_commands(PlatformCommand* commands, size_t max_commands, String* error = nullptr);
  int poll_contract_commands(
      const char* hardware_device_id,
      const char* node_role,
      const char* firmware_version,
      const char* hardware_model,
      PlatformCommand* commands,
      size_t max_commands,
      String* error = nullptr);
  bool acknowledge_command(
      int command_id,
      const char* status,
      const char* message,
      bool light_on,
      bool pump_on,
      String* error = nullptr,
      int light_intensity_percent = -1);
  bool report_hardware_command_result(
      int command_id,
      const char* status,
      const char* message,
      bool light_on,
      bool pump_on,
      String* error = nullptr,
      int light_intensity_percent = -1);
  bool report_contract_command_result(
      const PlatformCommand& command,
      const char* hardware_device_id,
      const char* node_role,
      const char* status,
      const char* message,
      bool light_on,
      bool pump_on,
      String* error = nullptr,
      int light_intensity_percent = -1,
      const char* error_code = nullptr);
  bool upload_jpeg(
      const uint8_t* bytes,
      size_t length,
      const char* filename,
      const char* source_hardware_device_id = nullptr,
      const char* camera_role = nullptr,
      const char* idempotency_key = nullptr,
      int* http_status_code = nullptr,
      String* error = nullptr);
  bool register_device_node(
      const char* hardware_device_id,
      const char* node_role,
      const char* display_name,
      const char* hardware_model,
      const char* hardware_version,
      const char* software_version,
      const char* capabilities_json,
      const char* camera_role = nullptr,
      String* error = nullptr);
  bool fetch_ota_manifest(
      const char* hardware_device_id,
      const char* node_role,
      const char* current_version,
      String* response_body,
      String* error = nullptr);
  bool report_ota_status(
      const char* hardware_device_id,
      const char* status,
      const char* release_id,
      const char* target_version,
      const char* installed_version,
      int progress,
      const char* error_message,
      String* error = nullptr);
  bool report_contract_ota_status(
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
      String* error = nullptr);
  bool download_ota_artifact(
      const String& artifact_path,
      OtaChunkCallback callback,
      void* callback_context,
      String* error = nullptr);

 private:
  bool json_post(const String& path, const String& json_body, int* status_code, String* response_body);
  bool json_get(const String& path, int* status_code, String* response_body);
  bool json_get_with_timeout(
      const String& path,
      uint32_t timeout_ms,
      int* status_code,
      String* response_body);
  bool parse_url(String* host, uint16_t* port, String* path, bool* secure) const;
  String auth_header_value() const;
  String join_url(const String& path) const;
  String url_encode(const String& value) const;
  void set_error(String* error, const String& message) const;

  String base_url_;
  int device_id_;
  String device_token_;
};
