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
  status.pump_on = false;
  status.message = "heartbeat";
  status.software_version = "0.2.3";

  String error;
  assert(client.send_hardware_heartbeat(status, &error));
  assert(platform_client_host_test::last_url == "https://api.example.test/base/api/hardware/heartbeat");
  assert(platform_client_host_test::last_post_body.length() > 0);

  StaticJsonDocument<512> doc;
  DeserializationError json_error = deserializeJson(doc, platform_client_host_test::last_post_body);
  assert(!json_error);
  assert(std::string(doc["hardware_device_id"] | "") == "master-01");
  assert(std::string(doc["node_role"] | "") == "master");
  assert(std::string(doc["status"] | "") == "online");
  assert(std::string(doc["message"] | "") == "heartbeat");
  assert(std::string(doc["software_version"] | "") == "0.2.3");
  assert((doc["light_on"] | false) == true);
  assert((doc["pump_on"] | true) == false);

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

  return 0;
}
