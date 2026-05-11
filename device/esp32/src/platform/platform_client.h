#pragma once

#include <Arduino.h>

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
};

struct PlatformStatus {
  bool light_on;
  bool pump_on;
  String message;
};

class PlatformClient {
 public:
  PlatformClient(const char* base_url, int device_id, const char* device_token);

  bool configured() const;
  const String& base_url() const;
  int device_id() const;

  bool send_reading(const PlatformReading& reading, String* error = nullptr);
  bool send_status(const PlatformStatus& status, String* error = nullptr);
  int poll_pending_commands(PlatformCommand* commands, size_t max_commands, String* error = nullptr);
  bool acknowledge_command(
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
      String* error = nullptr);

 private:
  bool json_post(const String& path, const String& json_body, int* status_code, String* response_body);
  bool json_get(const String& path, int* status_code, String* response_body);
  bool parse_url(String* host, uint16_t* port, String* path, bool* secure) const;
  String auth_header_value() const;
  String join_url(const String& path) const;
  void set_error(String* error, const String& message) const;

  String base_url_;
  int device_id_;
  String device_token_;
};
