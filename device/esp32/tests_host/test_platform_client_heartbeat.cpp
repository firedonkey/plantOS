#include "platform/platform_client.h"

#include <ArduinoJson.h>

#include <cassert>
#include <string>

#include "HTTPClient.h"
#include "config.h"
#include "time/time_sync_manager.h"

int main() {
  plantlab::time_sync::resetForTesting();
  plantlab::time_sync::service(false, 1000);
  assert(plantlab::time_sync::status() == plantlab::time_sync::TimeSyncStatus::kUnsynchronized);
  assert(plantlab::time_sync::syncAttemptCount() == 0);
  plantlab::time_sync::service(true, 1000);
  assert(plantlab::time_sync::status() == plantlab::time_sync::TimeSyncStatus::kSynchronizing);
  assert(plantlab::time_sync::syncAttemptCount() == 1);
  plantlab::time_sync::service(true, 1000 + PLANTLAB_NTP_SYNC_TIMEOUT_MS);
  assert(plantlab::time_sync::status() == plantlab::time_sync::TimeSyncStatus::kSyncFailed);
  plantlab::time_sync::service(true, 1001 + PLANTLAB_NTP_SYNC_TIMEOUT_MS);
  assert(plantlab::time_sync::syncAttemptCount() == 1);
  plantlab::time_sync::service(true, 1000 + PLANTLAB_NTP_SYNC_TIMEOUT_MS + PLANTLAB_NTP_RETRY_INTERVAL_MS);
  assert(plantlab::time_sync::status() == plantlab::time_sync::TimeSyncStatus::kSynchronizing);
  assert(plantlab::time_sync::syncAttemptCount() == 2);
  plantlab::time_sync::resetForTesting();
  platform_client_host_test::reset_http_capture();

  PlatformClient client("https://api.example.test/base", 42, "device-token");
  PlatformStatus status;
  status.hardware_device_id = "master-01";
  status.node_role = "master";
  status.status = "online";
  status.hardware_model = "esp32_master";
  status.hardware_version = "ESP32-S3-DevKitC-1-N32R16V";
  status.ip_address = "192.168.1.20";
  status.has_free_heap_bytes = true;
  status.free_heap_bytes = 185000;
  status.has_light_state = true;
  status.light_on = true;
  status.light_intensity_percent = 45;
  status.has_ambient_led_belt_state = true;
  status.ambient_led_belt.available = true;
  status.ambient_led_belt.enabled = true;
  status.ambient_led_belt.mode = "solid";
  status.ambient_led_belt.brightness = 26;
  status.ambient_led_belt.max_brightness = 51;
  status.ambient_led_belt.color_r = 255;
  status.ambient_led_belt.color_g = 0;
  status.ambient_led_belt.color_b = 0;
  status.ambient_led_belt.logical_pixel_count = 14;
  status.ambient_led_belt.physical_led_count = 630;
  status.ambient_led_belt.color_order = "RGB";
  status.ambient_led_belt.data_gpio = 1;
  status.ambient_led_belt.diagnostic_active = false;
  status.has_water_level_state = true;
  status.water_level.available = true;
  status.water_level.calibrated = true;
  status.water_level.stable = true;
  status.water_level.state = "medium";
  status.water_level.instantaneous_state = "medium";
  status.water_level.quality = "valid";
  status.water_level.reason = "ok";
  status.water_level.percent = 67;
  status.water_level.representative_raw = 31000;
  status.water_level.pads[0].name = "top";
  status.water_level.pads[0].gpio = 4;
  status.water_level.pads[0].touch_channel = 4;
  status.water_level.pads[0].available = true;
  status.water_level.pads[0].calibrated = true;
  status.water_level.pads[0].wet = false;
  status.water_level.pads[0].stable = true;
  status.water_level.pads[0].raw = 41000;
  status.water_level.pads[0].filtered = 41000;
  status.water_level.pads[0].threshold = 30000;
  status.water_level.pads[0].hysteresis = 2000;
  status.water_level.pads[0].dry_baseline = 42000;
  status.water_level.pads[0].wet_reference = 18000;
  status.water_level.pads[0].margin = -11000;
  status.water_level.pads[1].name = "middle";
  status.water_level.pads[1].gpio = 5;
  status.water_level.pads[1].touch_channel = 5;
  status.water_level.pads[1].available = true;
  status.water_level.pads[1].calibrated = true;
  status.water_level.pads[1].wet = true;
  status.water_level.pads[1].stable = true;
  status.water_level.pads[1].raw = 19000;
  status.water_level.pads[1].filtered = 19000;
  status.water_level.pads[1].threshold = 30000;
  status.water_level.pads[1].hysteresis = 2000;
  status.water_level.pads[1].dry_baseline = 42000;
  status.water_level.pads[1].wet_reference = 18000;
  status.water_level.pads[1].margin = 11000;
  status.water_level.pads[2].name = "bottom";
  status.water_level.pads[2].gpio = 6;
  status.water_level.pads[2].touch_channel = 6;
  status.water_level.pads[2].available = true;
  status.water_level.pads[2].calibrated = true;
  status.water_level.pads[2].wet = true;
  status.water_level.pads[2].stable = true;
  status.water_level.pads[2].raw = 18500;
  status.water_level.pads[2].filtered = 18500;
  status.water_level.pads[2].threshold = 30000;
  status.water_level.pads[2].hysteresis = 2000;
  status.water_level.pads[2].dry_baseline = 42000;
  status.water_level.pads[2].wet_reference = 18000;
  status.water_level.pads[2].margin = 11500;
  status.pump_on = false;
  status.message = "heartbeat";
  status.software_version = "0.2.3";
  status.has_capture_interval_seconds = true;
  status.capture_interval_seconds = 3600;
  status.ota_status = "idle";
  status.provisioning_status = "normal";
  status.camera_node_status = "online";
  status.last_command_contract_id = "cmd_12";
  status.last_command_status = "completed";
  status.last_command_poll_at = "2026-01-01T00:00:01Z";
  status.last_command_poll_status = "ok";
  status.has_last_command_poll_latency_ms = true;
  status.last_command_poll_latency_ms = 112;
  status.has_command_poll_stale_seconds = true;
  status.command_poll_stale_seconds = 4;
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

  StaticJsonDocument<4096> doc;
  DeserializationError json_error = deserializeJson(doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(doc["schema_version"] | "") == "1.0");
  assert(std::string(doc["hardware_device_id"] | "") == "master-01");
  assert(std::string(doc["node_role"] | "") == "master");
  assert(std::string(doc["message_type"] | "") == "HEARTBEAT");
  assert(std::string(doc["sent_at"] | "") == "1970-01-01T00:00:00Z");
  assert((doc["device_id"] | 0) == 42);
  assert((doc["payload"]["uptime_seconds"] | 0) == 3661);
  assert((doc["payload"]["wifi_rssi_dbm"] | 0) == -67);
  assert(std::string(doc["payload"]["ip_address"] | "") == "192.168.1.20");
  assert((doc["payload"]["free_heap_bytes"] | 0) == 185000);
  assert(std::string(doc["payload"]["node_status"] | "") == "online");
  assert(std::string(doc["payload"]["firmware_version"] | "") == "0.2.3");
  assert(std::string(doc["payload"]["hardware_model"] | "") == "esp32_master");
  assert(std::string(doc["payload"]["hardware_version"] | "") == "ESP32-S3-DevKitC-1-N32R16V");
  assert((doc["payload"]["actuators"]["grow_light"]["enabled"] | false) == true);
  assert((doc["payload"]["actuators"]["grow_light"]["brightness_percent"] | 0) == 45);
  assert((doc["payload"]["runtime"]["capture_interval_seconds"] | 0) == 3600);
  assert(std::string(doc["payload"]["runtime"]["ota_status"] | "") == "idle");
  assert(std::string(doc["payload"]["runtime"]["provisioning_status"] | "") == "normal");
  assert(std::string(doc["payload"]["runtime"]["camera_node_status"] | "") == "online");
  assert(std::string(doc["payload"]["runtime"]["last_command_id"] | "") == "cmd_12");
  assert(std::string(doc["payload"]["runtime"]["last_command_status"] | "") == "completed");
  assert(std::string(doc["payload"]["runtime"]["last_command_poll_at"] | "") == "2026-01-01T00:00:01Z");
  assert(std::string(doc["payload"]["runtime"]["last_command_poll_status"] | "") == "ok");
  assert((doc["payload"]["runtime"]["last_command_poll_latency_ms"] | 0) == 112);
  assert((doc["payload"]["runtime"]["command_poll_stale_seconds"] | 0) == 4);
  assert(std::string(doc["payload"]["runtime"]["time_sync_status"] | "") == "unsynchronized");
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["available"] | false) == true);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["enabled"] | false) == true);
  assert(std::string(doc["payload"]["runtime"]["ambient_led_belt"]["mode"] | "") == "solid");
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["brightness"] | 0) == 26);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["max_brightness"] | 0) == 51);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["color"]["r"] | 0) == 255);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["color"]["g"] | -1) == 0);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["color"]["b"] | -1) == 0);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["logical_pixel_count"] | 0) == 14);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["physical_led_count"] | 0) == 630);
  assert(std::string(doc["payload"]["runtime"]["ambient_led_belt"]["color_order"] | "") == "RGB");
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["data_gpio"] | 0) == 1);
  assert((doc["payload"]["runtime"]["ambient_led_belt"]["diagnostic_active"] | true) == false);
  assert(!doc["payload"]["runtime"]["ambient_led_belt"].containsKey("last_error"));
  assert((doc["payload"]["runtime"]["water_level"]["available"] | false) == true);
  assert((doc["payload"]["runtime"]["water_level"]["calibrated"] | false) == true);
  assert((doc["payload"]["runtime"]["water_level"]["stable"] | false) == true);
  assert(std::string(doc["payload"]["runtime"]["water_level"]["state"] | "") == "medium");
  assert(std::string(doc["payload"]["runtime"]["water_level"]["instantaneous_state"] | "") == "medium");
  assert(std::string(doc["payload"]["runtime"]["water_level"]["quality"] | "") == "valid");
  assert((doc["payload"]["runtime"]["water_level"]["percent"] | 0) == 67);
  assert((doc["payload"]["runtime"]["water_level"]["representative_raw"] | 0) == 31000);
  assert((doc["payload"]["runtime"]["water_level"]["pads"][0]["gpio"] | 0) == 4);
  assert(std::string(doc["payload"]["runtime"]["water_level"]["pads"][1]["name"] | "") == "middle");
  assert((doc["payload"]["runtime"]["water_level"]["pads"][1]["wet"] | false) == true);
  assert((doc["payload"]["runtime"]["water_level"]["pads"][2]["touch_channel"] | 0) == 6);
  assert((doc["payload"]["runtime"]["water_level"]["pads"][2]["filtered"] | 0) == 18500);

  plantlab::time_sync::setSynchronizedTimeForTesting(1767225600);
  platform_client_host_test::reset_http_capture();
  assert(client.send_hardware_heartbeat(status, &error));
  StaticJsonDocument<4096> synced_doc;
  json_error = deserializeJson(synced_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(synced_doc["sent_at"] | "") == "2026-01-01T00:00:00Z");
  assert(std::string(synced_doc["payload"]["runtime"]["time_sync_status"] | "") == "synchronized");
  assert(std::string(synced_doc["payload"]["runtime"]["last_ntp_sync_at"] | "") == "2026-01-01T00:00:00Z");

  platform_client_host_test::reset_http_capture();
  platform_client_host_test::next_response_body = "{\"schema_version\":\"1.0\",\"commands\":[]}";
  PlatformCommand empty_commands[1]{};
  assert(client.poll_contract_commands("master-01", "master", "0.2.3", "esp32_master", empty_commands, 1, &error) == 0);
  assert(platform_client_host_test::last_timeout_ms == 5000);

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

  platform_client_host_test::reset_http_capture();
  platform_client_host_test::next_response_body = R"json({
    "schema_version": "1.0",
    "commands": [
      {
        "schema_version": "1.0",
        "message_id": "cmdmsg_88_1",
        "device_id": 42,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
          "command_id": "cmd_88",
          "command_type": "SET_GROW_LIGHT_BRIGHTNESS",
          "target": {
            "node_role": "master",
            "hardware_device_id": "master-01"
          },
          "params": {
            "brightness_percent": 55
          },
          "timeout_ms": 20000,
          "priority": "normal",
          "extra_future_field": true
        }
      }
    ]
  })json";

  PlatformCommand commands[2]{};
  assert(client.poll_contract_commands("master-01", "master", "0.2.3", "esp32_master", commands, 2, &error) == 1);
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/commands/poll?hardware_device_id=master-01&node_role=master&firmware_version=0.2.3&schema_version=1.0&limit=2&hardware_model=esp32_master");
  assert(commands[0].valid);
  assert(commands[0].contract_native);
  assert(commands[0].id == 88);
  assert(std::string(commands[0].command_id.c_str()) == "cmd_88");
  assert(std::string(commands[0].command_type.c_str()) == "SET_GROW_LIGHT_BRIGHTNESS");
  assert(std::string(commands[0].target.c_str()) == "grow_light");
  assert(std::string(commands[0].action.c_str()) == "set_intensity");
  assert(std::string(commands[0].value.c_str()) == "55");

  platform_client_host_test::reset_http_capture();
  platform_client_host_test::next_response_body = R"json({
    "schema_version": "1.0",
    "commands": [
      {
        "schema_version": "1.0",
        "message_id": "cmdmsg_89_1",
        "device_id": 42,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
          "command_id": "cmd_89",
          "command_type": "SET_GROW_LIGHT_BRIGHTNESS",
          "target": {
            "node_role": "master",
            "hardware_device_id": "master-01"
          },
          "params": {
            "channel": "white",
            "brightness_percent": 12
          },
          "timeout_ms": 20000,
          "priority": "normal"
        }
      }
    ]
  })json";

  PlatformCommand channel_commands[1]{};
  assert(client.poll_contract_commands("master-01", "master", "0.2.3", "esp32_master", channel_commands, 1, &error) == 1);
  assert(channel_commands[0].valid);
  assert(channel_commands[0].contract_native);
  assert(channel_commands[0].id == 89);
  assert(std::string(channel_commands[0].command_id.c_str()) == "cmd_89");
  assert(std::string(channel_commands[0].command_type.c_str()) == "SET_GROW_LIGHT_BRIGHTNESS");
  assert(std::string(channel_commands[0].target.c_str()) == "grow_light");
  assert(std::string(channel_commands[0].action.c_str()) == "set_channel_intensity");
  StaticJsonDocument<128> channel_doc;
  json_error = deserializeJson(channel_doc, channel_commands[0].value);
  assert(!json_error);
  assert(std::string(channel_doc["channel"] | "") == "white");
  assert((channel_doc["brightness_percent"] | 0) == 12);

  platform_client_host_test::reset_http_capture();
  assert(client.report_contract_command_result(
      commands[0],
      "master-01",
      "master",
      "acked",
      "command accepted",
      true,
      false,
      &error,
      55));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/commands/88/result");

  StaticJsonDocument<1024> result_doc;
  json_error = deserializeJson(result_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(result_doc["schema_version"] | "") == "1.0");
  assert(std::string(result_doc["message_type"] | "") == "COMMAND_RESULT");
  assert(std::string(result_doc["sent_at"] | "") == "2026-01-01T00:00:00Z");
  assert(std::string(result_doc["hardware_device_id"] | "") == "master-01");
  assert(std::string(result_doc["node_role"] | "") == "master");
  assert(std::string(result_doc["payload"]["command_id"] | "") == "cmd_88");
  assert(std::string(result_doc["payload"]["command_type"] | "") == "SET_GROW_LIGHT_BRIGHTNESS");
  assert(std::string(result_doc["payload"]["status"] | "") == "acked");
  assert((result_doc["payload"]["result"]["light_on"] | false) == true);
  assert((result_doc["payload"]["result"]["light_intensity_percent"] | 0) == 55);

  platform_client_host_test::reset_http_capture();
  assert(client.report_contract_ota_status(
      "master-01",
      "master",
      "ota_release-1",
      "downloading",
      "release-1",
      "0.2.4",
      "0.2.3",
      42,
      "beta",
      "download",
      nullptr,
      "Downloading firmware",
      &error));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/ota/status");

  StaticJsonDocument<1024> ota_doc;
  json_error = deserializeJson(ota_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(ota_doc["message_type"] | "") == "OTA_STATUS");
  assert(std::string(ota_doc["sent_at"] | "") == "2026-01-01T00:00:00Z");
  assert(std::string(ota_doc["payload"]["command_id"] | "") == "ota_release-1");
  assert(std::string(ota_doc["payload"]["status"] | "") == "downloading");
  assert((ota_doc["payload"]["progress_percent"] | 0) == 42);
  assert(std::string(ota_doc["payload"]["firmware_channel"] | "") == "beta");
  assert(std::string(ota_doc["payload"]["phase"] | "") == "download");

  platform_client_host_test::reset_http_capture();
  platform_client_host_test::next_response_body = R"json({
    "schema_version": "2.0",
    "commands": []
  })json";
  assert(client.poll_contract_commands("master-01", "master", "0.2.3", "esp32_master", commands, 2, &error) == -1);
  assert(std::string(error.c_str()) == "unsupported schema major version");

  platform_client_host_test::reset_http_capture();
  platform_client_host_test::next_response_body = R"json({
    "schema_version": "1.0",
    "commands": [
      {
        "schema_version": "1.0",
        "message_id": "cmdmsg_89_1",
        "device_id": 42,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
          "command_id": "cmd_89",
          "command_type": "START_OTA",
          "target": {
            "node_role": "master",
            "hardware_device_id": "master-01"
          },
          "params": {
            "target_version": "0.2.4",
            "firmware_channel": "beta",
            "download_url": "/api/hardware/ota/artifacts/release-89",
            "checksum_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "hardware_model": "esp32_master",
            "release_id": "release-89",
            "artifact_size_bytes": 123456
          },
          "timeout_ms": 1800000,
          "priority": "high"
        }
      }
    ]
  })json";

  PlatformCommand ota_commands[1]{};
  assert(client.poll_contract_commands("master-01", "master", "0.2.3", "esp32_master", ota_commands, 1, &error) == 1);
  assert(ota_commands[0].valid);
  assert(ota_commands[0].contract_native);
  assert(ota_commands[0].id == 89);
  assert(std::string(ota_commands[0].command_type.c_str()) == "START_OTA");
  assert(std::string(ota_commands[0].target.c_str()) == "ota");
  assert(std::string(ota_commands[0].action.c_str()) == "start");
  assert(std::string(ota_commands[0].ota_target_version.c_str()) == "0.2.4");
  assert(std::string(ota_commands[0].ota_download_url.c_str()) == "/api/hardware/ota/artifacts/release-89");
  assert(std::string(ota_commands[0].ota_firmware_channel.c_str()) == "beta");
  assert(std::string(ota_commands[0].ota_hardware_model.c_str()) == "esp32_master");
  assert(std::string(ota_commands[0].ota_release_id.c_str()) == "release-89");
  assert(ota_commands[0].ota_artifact_size_bytes == 123456);

  platform_client_host_test::reset_http_capture();
  assert(client.report_contract_command_result(
      ota_commands[0],
      "master-01",
      "master",
      "in_progress",
      "OTA update started",
      false,
      false,
      &error,
      -1));
  StaticJsonDocument<1024> ota_result_doc;
  json_error = deserializeJson(ota_result_doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(ota_result_doc["payload"]["command_type"] | "") == "START_OTA");
  assert(std::string(ota_result_doc["payload"]["status"] | "") == "in_progress");
  assert(!ota_result_doc["payload"]["result"].containsKey("light_on"));
  assert(!ota_result_doc["payload"]["result"].containsKey("pump_on"));

  return 0;
}
