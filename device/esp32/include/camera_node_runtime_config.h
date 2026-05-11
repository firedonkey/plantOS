#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "espnow_test_protocol.h"

struct CameraNodeRuntimeConfig {
  bool provisioned;
  uint16_t config_version;
  uint16_t camera_node_index;
  uint32_t platform_device_id;
  char wifi_ssid[ESPNOW_TEST_WIFI_SSID_MAX_LEN + 1];
  char wifi_password[ESPNOW_TEST_WIFI_PASSWORD_MAX_LEN + 1];
  char platform_url[ESPNOW_TEST_PLATFORM_URL_MAX_LEN + 1];
  char device_token[ESPNOW_TEST_DEVICE_TOKEN_MAX_LEN + 1];
};

inline void camera_node_clear_runtime_config(CameraNodeRuntimeConfig* config) {
  if (config == nullptr) {
    return;
  }
  memset(config, 0, sizeof(*config));
}

inline bool camera_node_runtime_config_complete(const CameraNodeRuntimeConfig& config) {
  return config.provisioned && config.config_version > 0 && config.camera_node_index > 0 &&
         config.platform_device_id > 0 && config.wifi_ssid[0] != '\0' &&
         config.platform_url[0] != '\0' && config.device_token[0] != '\0';
}

inline bool camera_node_runtime_config_equal(
    const CameraNodeRuntimeConfig& left,
    const CameraNodeRuntimeConfig& right) {
  return left.provisioned == right.provisioned && left.config_version == right.config_version &&
         left.camera_node_index == right.camera_node_index &&
         left.platform_device_id == right.platform_device_id &&
         memcmp(left.wifi_ssid, right.wifi_ssid, sizeof(left.wifi_ssid)) == 0 &&
         memcmp(left.wifi_password, right.wifi_password, sizeof(left.wifi_password)) == 0 &&
         memcmp(left.platform_url, right.platform_url, sizeof(left.platform_url)) == 0 &&
         memcmp(left.device_token, right.device_token, sizeof(left.device_token)) == 0;
}

inline bool camera_node_apply_provisioning_payload(
    CameraNodeRuntimeConfig* config,
    const CameraProvisioningPayload& payload) {
  if (config == nullptr || !espnow_validate_provisioning_payload(payload)) {
    return false;
  }
  memset(config, 0, sizeof(*config));
  config->provisioned = true;
  config->config_version = payload.config_version;
  config->camera_node_index = payload.camera_node_index;
  config->platform_device_id = payload.platform_device_id;
  memcpy(config->wifi_ssid, payload.wifi_ssid, sizeof(config->wifi_ssid));
  memcpy(config->wifi_password, payload.wifi_password, sizeof(config->wifi_password));
  memcpy(config->platform_url, payload.platform_url, sizeof(config->platform_url));
  memcpy(config->device_token, payload.device_token, sizeof(config->device_token));
  return true;
}
