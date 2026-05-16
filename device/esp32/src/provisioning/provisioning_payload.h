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
  PROVISIONING_COMMITTING,
  WIFI_CONNECTING,
  BACKEND_REGISTERING,
  PROVISIONING_FAILED,
  PROVISIONING_SUCCESS,
  FALLBACK_SOFTAP,
  FACTORY_RESET_PENDING,
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
  kBusy,
  kSaveFailed,
  kTimeout,
  kBleInitFailed,
  kAlreadyCommitted,
  kWifiNetworkNotFound,
  kWifiConnectFailed,
  kWifiConnectTimeout,
};

struct BleProvisioningPayload {
  std::string ssid;
  std::string password;
  std::string plantlab_token;
  std::string backend_url;
  std::string platform_url;
  int attach_to_platform_device_id = 0;
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
ProvisioningParseError provisioningWriteRejectionError(
    ProvisioningState state,
    bool has_pending_result,
    bool accepting_writes);
bool provisioningShouldStopAcceptingWritesOnTake(
    bool has_pending_result,
    bool result_ok,
    bool accepting_writes);

}  // namespace plantlab
