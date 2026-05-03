#include <assert.h>
#include <string.h>

#include "camera_node_runtime_config.h"

namespace {
void test_runtime_config_accepts_valid_payload() {
  CameraProvisioningPayload payload{};
  assert(espnow_build_provisioning_payload(
      &payload,
      2,
      1,
      15,
      "PlantLabWiFi",
      "camera-pass",
      "http://192.168.0.55:8000",
      "shared-device-token"));

  CameraNodeRuntimeConfig config{};
  assert(camera_node_apply_provisioning_payload(&config, payload));
  assert(camera_node_runtime_config_complete(config));
  assert(config.provisioned);
  assert(config.config_version == 2);
  assert(config.camera_node_index == 1);
  assert(config.platform_device_id == 15);
  assert(strcmp(config.wifi_ssid, "PlantLabWiFi") == 0);
  assert(strcmp(config.wifi_password, "camera-pass") == 0);
  assert(strcmp(config.platform_url, "http://192.168.0.55:8000") == 0);
  assert(strcmp(config.device_token, "shared-device-token") == 0);
}

void test_runtime_config_rejects_incomplete_payload() {
  CameraProvisioningPayload payload{};
  payload.config_version = 1;
  payload.camera_node_index = 1;
  payload.platform_device_id = 12;
  strcpy(payload.wifi_ssid, "ssid");

  CameraNodeRuntimeConfig config{};
  camera_node_clear_runtime_config(&config);
  assert(!camera_node_apply_provisioning_payload(&config, payload));
  assert(!camera_node_runtime_config_complete(config));
}
}  // namespace

int main() {
  test_runtime_config_accepts_valid_payload();
  test_runtime_config_rejects_incomplete_payload();
  return 0;
}
