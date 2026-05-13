#include <assert.h>
#include <string.h>

#include <string>

#include "provisioning/provisioning_payload.h"

namespace {

void test_valid_payload() {
  const char json[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\","
      "\"plantlab_token\":\"claim-token-123456\","
      "\"platform_url\":\"https://platform.example\","
      "\"backend_url\":\"https://provisioning.example\"}";
  const plantlab::ProvisioningParseResult result =
      plantlab::parseBleProvisioningPayload(json, strlen(json));
  assert(result.ok);
  assert(result.payload.ssid == "HomeWiFi");
  assert(result.payload.password == "wifi-password");
  assert(result.payload.plantlab_token == "claim-token-123456");
  assert(result.payload.platform_url == "https://platform.example");
  assert(result.payload.backend_url == "https://provisioning.example");
}

void test_alias_payload() {
  const char json[] =
      "{\"wifi_ssid\":\"PlantLabWiFi\",\"wifi_password\":\"secret-pass\","
      "\"setup_code\":\"setup-token\"}";
  const plantlab::ProvisioningParseResult result =
      plantlab::parseBleProvisioningPayload(json, strlen(json), "https://platform.example");
  assert(result.ok);
  assert(result.payload.ssid == "PlantLabWiFi");
  assert(result.payload.password == "secret-pass");
  assert(result.payload.plantlab_token == "setup-token");
  assert(result.payload.platform_url == "https://platform.example");
}

void test_primary_fields_take_precedence_over_aliases() {
  const char json[] =
      "{\"ssid\":\"PrimaryWiFi\",\"wifi_ssid\":\"AliasWiFi\","
      "\"password\":\"primary-pass\",\"wifi_password\":\"alias-pass\","
      "\"plantlab_token\":\"primary-token\",\"setup_code\":\"alias-token\","
      "\"platform_url\":\"https://platform.example\"}";
  const plantlab::ProvisioningParseResult result =
      plantlab::parseBleProvisioningPayload(json, strlen(json));
  assert(result.ok);
  assert(result.payload.ssid == "PrimaryWiFi");
  assert(result.payload.password == "primary-pass");
  assert(result.payload.plantlab_token == "primary-token");
}

void test_claim_token_alias_payload() {
  const char json[] =
      "{\"ssid\":\"PlantLabWiFi\",\"password\":\"secret-pass\","
      "\"claim_token\":\"claim-token\",\"platform_url\":\"https://platform.example\"}";
  const plantlab::ProvisioningParseResult result =
      plantlab::parseBleProvisioningPayload(json, strlen(json));
  assert(result.ok);
  assert(result.payload.plantlab_token == "claim-token");
}

void test_missing_fields() {
  const char missing_ssid[] =
      "{\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(missing_ssid, strlen(missing_ssid)).error ==
         plantlab::ProvisioningParseError::kMissingSsid);

  const char missing_password[] =
      "{\"ssid\":\"HomeWiFi\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(missing_password, strlen(missing_password)).error ==
         plantlab::ProvisioningParseError::kMissingPassword);

  const char missing_token[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(missing_token, strlen(missing_token)).error ==
         plantlab::ProvisioningParseError::kMissingToken);

  const char blank_ssid[] =
      "{\"ssid\":\"   \",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(blank_ssid, strlen(blank_ssid)).error ==
         plantlab::ProvisioningParseError::kMissingSsid);

  const char blank_password[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"   \",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(blank_password, strlen(blank_password)).error ==
         plantlab::ProvisioningParseError::kMissingPassword);

  const char blank_token[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"   \","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(blank_token, strlen(blank_token)).error ==
         plantlab::ProvisioningParseError::kMissingToken);

  const char missing_platform_url[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\"}";
  assert(plantlab::parseBleProvisioningPayload(missing_platform_url, strlen(missing_platform_url)).error ==
         plantlab::ProvisioningParseError::kMissingPlatformUrl);
}

void test_platform_url_fallback() {
  const char json[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\"}";
  const plantlab::ProvisioningParseResult result =
      plantlab::parseBleProvisioningPayload(json, strlen(json), "  https://fallback.example  ");
  assert(result.ok);
  assert(result.payload.platform_url == "https://fallback.example");

  assert(plantlab::parseBleProvisioningPayload(json, strlen(json), "   ").error ==
         plantlab::ProvisioningParseError::kMissingPlatformUrl);
}

void test_invalid_json_and_malformed_payload() {
  assert(plantlab::parseBleProvisioningPayload(nullptr, 0).error ==
         plantlab::ProvisioningParseError::kEmptyPayload);

  const char invalid_json[] = "{\"ssid\":\"HomeWiFi\"";
  assert(plantlab::parseBleProvisioningPayload(invalid_json, strlen(invalid_json)).error ==
         plantlab::ProvisioningParseError::kInvalidJson);

  const char malformed_json[] = "[\"not\", \"an\", \"object\"]";
  assert(plantlab::parseBleProvisioningPayload(malformed_json, strlen(malformed_json)).error ==
         plantlab::ProvisioningParseError::kMalformedPayload);
}

void test_direct_token_rejected() {
  const char json[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\","
      "\"device_access_token\":\"long-term-token\","
      "\"platform_device_id\":17,\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(json, strlen(json)).error ==
         plantlab::ProvisioningParseError::kDirectDeviceTokenUnsupported);

  const char device_token_json[] =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\","
      "\"device_token\":\"long-term-token\",\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(device_token_json, strlen(device_token_json)).error ==
         plantlab::ProvisioningParseError::kDirectDeviceTokenUnsupported);
}

void test_length_limits() {
  const std::string long_ssid(33, 'a');
  const std::string ssid_json =
      "{\"ssid\":\"" + long_ssid +
      "\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(ssid_json.c_str(), ssid_json.length()).error ==
         plantlab::ProvisioningParseError::kSsidTooLong);

  const std::string long_password(64, 'p');
  const std::string password_json =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"" + long_password +
      "\",\"plantlab_token\":\"token\",\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(password_json.c_str(), password_json.length()).error ==
         plantlab::ProvisioningParseError::kPasswordTooLong);

  const std::string long_token(257, 't');
  const std::string token_json =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"" +
      long_token + "\",\"platform_url\":\"https://platform.example\"}";
  assert(plantlab::parseBleProvisioningPayload(token_json.c_str(), token_json.length()).error ==
         plantlab::ProvisioningParseError::kTokenTooLong);

  const std::string long_url = "https://" + std::string(257, 'u') + ".example";
  const std::string url_json =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"" + long_url + "\"}";
  assert(plantlab::parseBleProvisioningPayload(url_json.c_str(), url_json.length()).error ==
         plantlab::ProvisioningParseError::kUrlTooLong);

  const std::string backend_url_json =
      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
      "\"platform_url\":\"https://platform.example\",\"backend_url\":\"" + long_url + "\"}";
  assert(plantlab::parseBleProvisioningPayload(
             backend_url_json.c_str(),
             backend_url_json.length())
             .error == plantlab::ProvisioningParseError::kUrlTooLong);

  const std::string oversized_payload(plantlab::kProvisioningMaxJsonLength + 1, ' ');
  assert(plantlab::parseBleProvisioningPayload(
             oversized_payload.c_str(),
             oversized_payload.length())
             .error == plantlab::ProvisioningParseError::kPayloadTooLarge);
}

void test_secret_masking() {
  assert(plantlab::maskSecretForLog("") == "<empty>");
  assert(plantlab::maskSecretForLog("short") == "*****");
  assert(plantlab::maskSecretForLog("claim-token-123456") == "clai...3456");
  assert(plantlab::maskSecretForLog("12345678") == "********");
  assert(plantlab::maskSecretForLog("123456789") == "1234...6789");
}

void test_state_helpers() {
  assert(strcmp(plantlab::provisioningStateName(plantlab::ProvisioningState::NORMAL), "NORMAL") == 0);
  assert(strcmp(
             plantlab::provisioningStateName(plantlab::ProvisioningState::PROVISIONING_BLE),
             "PROVISIONING_BLE") == 0);
  assert(strcmp(
             plantlab::provisioningStateName(plantlab::ProvisioningState::WIFI_CONNECTING),
             "WIFI_CONNECTING") == 0);
  assert(strcmp(
             plantlab::provisioningStateName(plantlab::ProvisioningState::PROVISIONING_FAILED),
             "PROVISIONING_FAILED") == 0);
  assert(strcmp(
             plantlab::provisioningStateName(plantlab::ProvisioningState::PROVISIONING_SUCCESS),
             "PROVISIONING_SUCCESS") == 0);
  assert(plantlab::provisioningStateAfterValidPayload() ==
         plantlab::ProvisioningState::PROVISIONING_SUCCESS);
  assert(plantlab::provisioningStateAfterInvalidPayload() ==
         plantlab::ProvisioningState::PROVISIONING_BLE);
  assert(plantlab::provisioningStateAfterTimeout(true) ==
         plantlab::ProvisioningState::WIFI_CONNECTING);
  assert(plantlab::provisioningStateAfterTimeout(false) ==
         plantlab::ProvisioningState::PROVISIONING_FAILED);
}

void test_error_codes() {
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kNone),
             "none") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kEmptyPayload),
             "empty_payload") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kPayloadTooLarge),
             "payload_too_large") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kMissingSsid),
             "missing_ssid") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kMissingPassword),
             "missing_password") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kMissingToken),
             "missing_token") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kInvalidJson),
             "invalid_json") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kMalformedPayload),
             "malformed_payload") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kMissingPlatformUrl),
             "missing_platform_url") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kSsidTooLong),
             "ssid_too_long") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kPasswordTooLong),
             "password_too_long") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kTokenTooLong),
             "token_too_long") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(plantlab::ProvisioningParseError::kUrlTooLong),
             "url_too_long") == 0);
  assert(strcmp(
             plantlab::provisioningParseErrorCode(
                 plantlab::ProvisioningParseError::kDirectDeviceTokenUnsupported),
             "direct_device_token_unsupported") == 0);
}

}  // namespace

int main() {
  test_valid_payload();
  test_alias_payload();
  test_primary_fields_take_precedence_over_aliases();
  test_claim_token_alias_payload();
  test_missing_fields();
  test_platform_url_fallback();
  test_invalid_json_and_malformed_payload();
  test_direct_token_rejected();
  test_length_limits();
  test_secret_masking();
  test_state_helpers();
  test_error_codes();
  return 0;
}
