#include "platform/platform_client.h"

#include <ArduinoJson.h>

#include <cassert>
#include <string>

#include "HTTPClient.h"

int main() {
  platform_client_host_test::reset_http_capture();

  PlatformClient client("https://api.example.test/base", 42, "device-token");
  PlatformStatus status;
  status.hardware_device_id = "master-01";
  status.node_role = "master";
  status.status = "online";
  status.light_on = true;
  status.light_intensity_percent = 45;
  status.pump_on = false;
  status.message = "heartbeat";
  status.software_version = "0.2.3";
  status.diagnostics.valid = true;
  status.diagnostics.has_uptime_seconds = true;
  status.diagnostics.uptime_seconds = 3661;
  status.diagnostics.has_wifi_rssi_dbm = true;
  status.diagnostics.wifi_rssi_dbm = -67;
  status.diagnostics.reboot_reason = "power_on";
  status.diagnostics.provisioning_state = "normal";
  status.diagnostics.has_last_sensor_reading_age_seconds = true;
  status.diagnostics.last_sensor_reading_age_seconds = 8;
  status.diagnostics.has_last_camera_image_upload_age_seconds = true;
  status.diagnostics.last_camera_image_upload_age_seconds = 120;
  status.diagnostics.has_last_command = true;
  status.diagnostics.last_command_id = 12;
  status.diagnostics.last_command_status = "completed";
  status.diagnostics.last_command_code = "ok";
  status.diagnostics.last_command_message = "capture completed";
  status.diagnostics.has_last_command_age_seconds = true;
  status.diagnostics.last_command_age_seconds = 4;
  status.diagnostics.has_error_counters = true;
  status.diagnostics.error_counters.wifi_reconnects = 1;
  status.diagnostics.error_counters.upload_failures = 2;
  status.diagnostics.error_counters.ble_provisioning_failures = 3;
  status.diagnostics.error_counters.espnow_failures = 4;
  status.diagnostics.last_error_code = "upload_failed";
  status.diagnostics.last_error_message = "sensor upload failed";

  String error;
  assert(client.send_hardware_heartbeat(status, &error));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/heartbeat");
  assert(platform_client_host_test::last_post_body.length() > 0);

  StaticJsonDocument<1024> doc;
  DeserializationError json_error = deserializeJson(doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(doc["hardware_device_id"] | "") == "master-01");
  assert(std::string(doc["node_role"] | "") == "master");
  assert(std::string(doc["status"] | "") == "online");
  assert(std::string(doc["message"] | "") == "heartbeat");
  assert(std::string(doc["software_version"] | "") == "0.2.3");
  assert((doc["light_on"] | false) == true);
  assert((doc["light_intensity_percent"] | 0) == 45);
  assert((doc["pump_on"] | true) == false);
  assert((doc["diagnostics"]["schema_version"] | 0) == 1);
  assert((doc["diagnostics"]["uptime_seconds"] | 0) == 3661);
  assert((doc["diagnostics"]["wifi_rssi_dbm"] | 0) == -67);
  assert(std::string(doc["diagnostics"]["reboot_reason"] | "") == "power_on");
  assert(std::string(doc["diagnostics"]["provisioning_state"] | "") == "normal");
  assert((doc["diagnostics"]["last_sensor_reading_age_seconds"] | 0) == 8);
  assert((doc["diagnostics"]["last_camera_image_upload_age_seconds"] | 0) == 120);
  assert((doc["diagnostics"]["last_command"]["id"] | 0) == 12);
  assert(std::string(doc["diagnostics"]["last_command"]["status"] | "") == "completed");
  assert(std::string(doc["diagnostics"]["last_command"]["code"] | "") == "ok");
  assert(std::string(doc["diagnostics"]["last_command"]["message"] | "") == "capture completed");
  assert((doc["diagnostics"]["last_command"]["age_seconds"] | 0) == 4);
  assert((doc["diagnostics"]["error_counters"]["wifi_reconnects"] | 0) == 1);
  assert((doc["diagnostics"]["error_counters"]["upload_failures"] | 0) == 2);
  assert((doc["diagnostics"]["error_counters"]["ble_provisioning_failures"] | 0) == 3);
  assert((doc["diagnostics"]["error_counters"]["espnow_failures"] | 0) == 4);
  assert(std::string(doc["diagnostics"]["last_error"]["code"] | "") == "upload_failed");
  assert(std::string(doc["diagnostics"]["last_error"]["message"] | "") == "sensor upload failed");

  platform_client_host_test::reset_http_capture();
  PlatformStatus legacy_status;
  legacy_status.hardware_device_id = "master-01";
  legacy_status.node_role = "master";
  legacy_status.status = "online";
  assert(client.send_hardware_heartbeat(legacy_status, &error));

  StaticJsonDocument<512> legacy_doc;
  json_error = deserializeJson(legacy_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(!legacy_doc.containsKey("software_version"));
  assert(!legacy_doc.containsKey("diagnostics"));
  assert(!legacy_doc.containsKey("light_intensity_percent"));

  platform_client_host_test::reset_http_capture();
  PlatformReading reading;
  reading.hardware_device_id = "master-01";
  reading.temperature_c = 22.5f;
  reading.humidity_percent = 51.0f;
  reading.moisture_percent = 38.5f;
  reading.water_temperature_c = 19.75f;
  reading.water_level_raw = 35120;
  reading.temperature_valid = true;
  reading.humidity_valid = true;
  reading.moisture_valid = true;
  reading.water_temperature_valid = true;
  reading.water_level_valid = true;
  reading.water_level_state = "ok";
  reading.light_on = true;
  reading.light_intensity_percent = 65;
  reading.pump_on = false;
  reading.pump_status = "idle";

  assert(client.send_hardware_reading(reading, &error));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/readings");

  StaticJsonDocument<768> reading_doc;
  json_error = deserializeJson(reading_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(reading_doc["hardware_device_id"] | "") == "master-01");
  assert((reading_doc["temperature"] | 0.0f) == 22.5f);
  assert((reading_doc["humidity"] | 0.0f) == 51.0f);
  assert((reading_doc["moisture"] | 0.0f) == 38.5f);
  assert((reading_doc["water_temperature_c"] | 0.0f) == 19.75f);
  assert((reading_doc["water_level_raw"] | 0) == 35120);
  assert(std::string(reading_doc["water_level_state"] | "") == "ok");
  assert((reading_doc["light_on"] | false) == true);
  assert((reading_doc["light_intensity_percent"] | 0) == 65);
  assert((reading_doc["pump_on"] | true) == false);
  assert(std::string(reading_doc["pump_status"] | "") == "idle");

  platform_client_host_test::reset_http_capture();
  assert(client.send_reading(reading, &error));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/data");

  StaticJsonDocument<768> legacy_reading_doc;
  json_error = deserializeJson(legacy_reading_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert((legacy_reading_doc["device_id"] | 0) == 42);
  assert(std::string(legacy_reading_doc["hardware_device_id"] | "") == "master-01");
  assert((legacy_reading_doc["water_temperature_c"] | 0.0f) == 19.75f);
  assert((legacy_reading_doc["water_level_raw"] | 0) == 35120);
  assert(std::string(legacy_reading_doc["water_level_state"] | "") == "ok");

  return 0;
}
