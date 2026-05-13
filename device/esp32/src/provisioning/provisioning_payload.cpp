#include "provisioning/provisioning_payload.h"

#include <ArduinoJson.h>

#include <algorithm>

namespace plantlab {
namespace {

std::string trim_copy(const char* value) {
  if (value == nullptr) {
    return "";
  }
  std::string result(value);
  const auto first = std::find_if_not(result.begin(), result.end(), [](unsigned char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
  });
  const auto last = std::find_if_not(result.rbegin(), result.rend(), [](unsigned char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
  }).base();
  if (first >= last) {
    return "";
  }
  return std::string(first, last);
}

std::string first_string(JsonObjectConst object, const char* primary, const char* alias = nullptr) {
  const char* value = object[primary].as<const char*>();
  if ((value == nullptr || value[0] == '\0') && alias != nullptr) {
    value = object[alias].as<const char*>();
  }
  return trim_copy(value);
}

bool has_key(JsonObjectConst object, const char* key) {
  return !object[key].isNull();
}

ProvisioningParseResult fail(ProvisioningParseError error) {
  ProvisioningParseResult result;
  result.ok = false;
  result.error = error;
  return result;
}

}  // namespace

const char* provisioningStateName(ProvisioningState state) {
  switch (state) {
    case ProvisioningState::NORMAL:
      return "NORMAL";
    case ProvisioningState::PROVISIONING_BLE:
      return "PROVISIONING_BLE";
    case ProvisioningState::WIFI_CONNECTING:
      return "WIFI_CONNECTING";
    case ProvisioningState::PROVISIONING_FAILED:
      return "PROVISIONING_FAILED";
    case ProvisioningState::PROVISIONING_SUCCESS:
      return "PROVISIONING_SUCCESS";
    default:
      return "PROVISIONING_FAILED";
  }
}

const char* provisioningParseErrorCode(ProvisioningParseError error) {
  switch (error) {
    case ProvisioningParseError::kNone:
      return "none";
    case ProvisioningParseError::kEmptyPayload:
      return "empty_payload";
    case ProvisioningParseError::kPayloadTooLarge:
      return "payload_too_large";
    case ProvisioningParseError::kInvalidJson:
      return "invalid_json";
    case ProvisioningParseError::kMalformedPayload:
      return "malformed_payload";
    case ProvisioningParseError::kMissingSsid:
      return "missing_ssid";
    case ProvisioningParseError::kMissingPassword:
      return "missing_password";
    case ProvisioningParseError::kMissingToken:
      return "missing_token";
    case ProvisioningParseError::kMissingPlatformUrl:
      return "missing_platform_url";
    case ProvisioningParseError::kSsidTooLong:
      return "ssid_too_long";
    case ProvisioningParseError::kPasswordTooLong:
      return "password_too_long";
    case ProvisioningParseError::kTokenTooLong:
      return "token_too_long";
    case ProvisioningParseError::kUrlTooLong:
      return "url_too_long";
    case ProvisioningParseError::kDirectDeviceTokenUnsupported:
      return "direct_device_token_unsupported";
    default:
      return "malformed_payload";
  }
}

ProvisioningParseResult parseBleProvisioningPayload(
    const char* json,
    size_t length,
    const char* fallback_platform_url) {
  if (json == nullptr || length == 0) {
    return fail(ProvisioningParseError::kEmptyPayload);
  }
  if (length > kProvisioningMaxJsonLength) {
    return fail(ProvisioningParseError::kPayloadTooLarge);
  }

  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, json, length);
  if (error) {
    return fail(ProvisioningParseError::kInvalidJson);
  }
  if (!doc.is<JsonObjectConst>()) {
    return fail(ProvisioningParseError::kMalformedPayload);
  }

  JsonObjectConst object = doc.as<JsonObjectConst>();
  if (has_key(object, "device_access_token") || has_key(object, "device_token")) {
    return fail(ProvisioningParseError::kDirectDeviceTokenUnsupported);
  }

  BleProvisioningPayload payload;
  payload.ssid = first_string(object, "ssid", "wifi_ssid");
  payload.password = first_string(object, "password", "wifi_password");
  payload.plantlab_token = first_string(object, "plantlab_token", "setup_code");
  if (payload.plantlab_token.empty()) {
    payload.plantlab_token = first_string(object, "claim_token");
  }
  payload.backend_url = first_string(object, "backend_url");
  payload.platform_url = first_string(object, "platform_url");
  if (payload.platform_url.empty()) {
    payload.platform_url = trim_copy(fallback_platform_url);
  }

  if (payload.ssid.empty()) {
    return fail(ProvisioningParseError::kMissingSsid);
  }
  if (payload.password.empty()) {
    return fail(ProvisioningParseError::kMissingPassword);
  }
  if (payload.plantlab_token.empty()) {
    return fail(ProvisioningParseError::kMissingToken);
  }
  if (payload.platform_url.empty()) {
    return fail(ProvisioningParseError::kMissingPlatformUrl);
  }
  if (payload.ssid.length() > kProvisioningMaxSsidLength) {
    return fail(ProvisioningParseError::kSsidTooLong);
  }
  if (payload.password.length() > kProvisioningMaxPasswordLength) {
    return fail(ProvisioningParseError::kPasswordTooLong);
  }
  if (payload.plantlab_token.length() > kProvisioningMaxTokenLength) {
    return fail(ProvisioningParseError::kTokenTooLong);
  }
  if (payload.backend_url.length() > kProvisioningMaxUrlLength ||
      payload.platform_url.length() > kProvisioningMaxUrlLength) {
    return fail(ProvisioningParseError::kUrlTooLong);
  }

  ProvisioningParseResult result;
  result.ok = true;
  result.error = ProvisioningParseError::kNone;
  result.payload = payload;
  return result;
}

std::string maskSecretForLog(const std::string& value) {
  if (value.empty()) {
    return "<empty>";
  }
  if (value.length() <= 8) {
    return std::string(value.length(), '*');
  }
  return value.substr(0, 4) + "..." + value.substr(value.length() - 4);
}

ProvisioningState provisioningStateAfterValidPayload() {
  return ProvisioningState::PROVISIONING_SUCCESS;
}

ProvisioningState provisioningStateAfterInvalidPayload() {
  return ProvisioningState::PROVISIONING_BLE;
}

ProvisioningState provisioningStateAfterTimeout(bool has_previous_runtime_config) {
  return has_previous_runtime_config ? ProvisioningState::WIFI_CONNECTING
                                     : ProvisioningState::PROVISIONING_FAILED;
}

}  // namespace plantlab
