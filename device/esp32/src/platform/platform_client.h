#pragma once

#include <Arduino.h>

using OtaChunkCallback = bool (*)(const uint8_t* bytes, size_t length, void* context);

struct PlatformCommand {
  int id;
  String target;
  String action;
  String value;
  bool valid;
};

struct PlatformReading {
  String hardware_device_id;
  float temperature_c;
  float humidity_percent;
  float moisture_percent;
  bool temperature_valid;
  bool humidity_valid;
  bool moisture_valid;
  bool light_on;
  bool pump_on;
  String pump_status;
  String idempotency_key;
};

struct PlatformStatus {
  String hardware_device_id;
  String node_role;
  String status;
  bool light_on;
  bool pump_on;
  String message;
  String software_version;
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
  bool acknowledge_command(
      int command_id,
      const char* status,
      const char* message,
      bool light_on,
      bool pump_on,
      String* error = nullptr);
  bool report_hardware_command_result(
      int command_id,
      const char* status,
      const char* message,
      bool light_on,
      bool pump_on,
      String* error = nullptr);
  bool upload_jpeg(
      const uint8_t* bytes,
      size_t length,
      const char* filename,
      const char* source_hardware_device_id = nullptr,
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
  bool download_ota_artifact(
      const String& artifact_path,
      OtaChunkCallback callback,
      void* callback_context,
      String* error = nullptr);

 private:
  bool json_post(const String& path, const String& json_body, int* status_code, String* response_body);
  bool json_get(const String& path, int* status_code, String* response_body);
  bool parse_url(String* host, uint16_t* port, String* path, bool* secure) const;
  String auth_header_value() const;
  String join_url(const String& path) const;
  String url_encode(const String& value) const;
  void set_error(String* error, const String& message) const;

  String base_url_;
  int device_id_;
  String device_token_;
};
