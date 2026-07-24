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
      CameraRoleCode::kSide,
      30,
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
  assert(config.camera_role == static_cast<uint8_t>(CameraRoleCode::kSide));
  assert(config.capture_phase_seconds == 30);
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
  payload.camera_role = static_cast<uint8_t>(CameraRoleCode::kTop);
  strcpy(payload.wifi_ssid, "ssid");

  CameraNodeRuntimeConfig config{};
  camera_node_clear_runtime_config(&config);
  assert(!camera_node_apply_provisioning_payload(&config, payload));
  assert(!camera_node_runtime_config_complete(config));
}

void test_runtime_config_rejects_side_to_top_reprovisioning() {
  CameraNodeRuntimeConfig current{};
  CameraProvisioningPayload side_payload{};
  assert(espnow_build_provisioning_payload(
      &side_payload,
      1,
      2,
      34,
      CameraRoleCode::kSide,
      30,
      "PlantLabWiFi",
      "camera-pass",
      "https://api.example.test",
      "shared-device-token"));
  assert(camera_node_apply_provisioning_payload(&current, side_payload));

  CameraNodeRuntimeConfig next{};
  CameraProvisioningPayload top_payload = side_payload;
  top_payload.camera_node_index = 1;
  top_payload.camera_role = static_cast<uint8_t>(CameraRoleCode::kTop);
  top_payload.capture_phase_seconds = 0;
  assert(camera_node_apply_provisioning_payload(&next, top_payload));

  assert(!camera_node_should_accept_provisioning_config(current, next));
}

void test_runtime_config_allows_top_to_side_recovery() {
  CameraNodeRuntimeConfig current{};
  CameraProvisioningPayload top_payload{};
  assert(espnow_build_provisioning_payload(
      &top_payload,
      1,
      1,
      34,
      CameraRoleCode::kTop,
      0,
      "PlantLabWiFi",
      "camera-pass",
      "https://api.example.test",
      "shared-device-token"));
  assert(camera_node_apply_provisioning_payload(&current, top_payload));

  CameraNodeRuntimeConfig next{};
  CameraProvisioningPayload side_payload = top_payload;
  side_payload.camera_node_index = 2;
  side_payload.camera_role = static_cast<uint8_t>(CameraRoleCode::kSide);
  side_payload.capture_phase_seconds = 30;
  assert(camera_node_apply_provisioning_payload(&next, side_payload));

  assert(camera_node_should_accept_provisioning_config(current, next));
}
}  // namespace

int main() {
  test_runtime_config_accepts_valid_payload();
  test_runtime_config_rejects_incomplete_payload();
  test_runtime_config_rejects_side_to_top_reprovisioning();
  test_runtime_config_allows_top_to_side_recovery();
  return 0;
}
