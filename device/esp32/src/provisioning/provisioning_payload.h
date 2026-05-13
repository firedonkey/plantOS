#pragma once

#include <stddef.h>

#include <string>

namespace plantlab {

constexpr size_t kProvisioningMaxJsonLength = 768;
constexpr size_t kProvisioningMaxSsidLength = 32;
constexpr size_t kProvisioningMaxPasswordLength = 63;
constexpr size_t kProvisioningMaxTokenLength = 256;
constexpr size_t kProvisioningMaxUrlLength = 256;

enum class ProvisioningState {
  NORMAL = 0,
  PROVISIONING_BLE,
  WIFI_CONNECTING,
  PROVISIONING_FAILED,
  PROVISIONING_SUCCESS,
};

enum class ProvisioningParseError {
  kNone = 0,
  kEmptyPayload,
  kPayloadTooLarge,
  kInvalidJson,
  kMalformedPayload,
  kMissingSsid,
  kMissingPassword,
  kMissingToken,
  kMissingPlatformUrl,
  kSsidTooLong,
  kPasswordTooLong,
  kTokenTooLong,
  kUrlTooLong,
  kDirectDeviceTokenUnsupported,
};

struct BleProvisioningPayload {
  std::string ssid;
  std::string password;
  std::string plantlab_token;
  std::string backend_url;
  std::string platform_url;
};

struct ProvisioningParseResult {
  bool ok = false;
  ProvisioningParseError error = ProvisioningParseError::kNone;
  BleProvisioningPayload payload;
};

const char* provisioningStateName(ProvisioningState state);
const char* provisioningParseErrorCode(ProvisioningParseError error);

ProvisioningParseResult parseBleProvisioningPayload(
    const char* json,
    size_t length,
    const char* fallback_platform_url = nullptr);

std::string maskSecretForLog(const std::string& value);
ProvisioningState provisioningStateAfterValidPayload();
ProvisioningState provisioningStateAfterInvalidPayload();
ProvisioningState provisioningStateAfterTimeout(bool has_previous_runtime_config);

}  // namespace plantlab
