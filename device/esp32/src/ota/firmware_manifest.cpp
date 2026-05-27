#include "ota/firmware_manifest.h"

#include <ArduinoJson.h>

namespace plantlab {
namespace {
constexpr size_t kMaxFirmwareArtifactBytes = 5UL * 1024UL * 1024UL;

bool isSha256Hex(const String& value) {
  if (value.length() != 64) {
    return false;
  }
  for (size_t i = 0; i < value.length(); ++i) {
    const char c = value.charAt(i);
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) {
      return false;
    }
  }
  return true;
}

void setError(String* error, const char* message) {
  if (error != nullptr) {
    *error = message;
  }
}
}  // namespace

bool parseFirmwareManifest(
    const String& json,
    const char* expected_node_role,
    const char* expected_hardware_model,
    int current_version_code,
    FirmwareManifest* manifest,
    String* error) {
  if (manifest == nullptr) {
    setError(error, "manifest output missing");
    return false;
  }
  *manifest = FirmwareManifest{};

  JsonDocument doc;
  DeserializationError parse_error = deserializeJson(doc, json);
  if (parse_error) {
    setError(error, "manifest JSON parse failed");
    return false;
  }

  manifest->update_available = doc["update_available"] | false;
  if (!manifest->update_available) {
    return true;
  }

  manifest->release_id = String(doc["release_id"] | "");
  manifest->node_role = String(doc["node_role"] | "");
  manifest->hardware_model = String(doc["hardware_model"] | "");
  manifest->version = String(doc["version"] | "");
  manifest->version_code = doc["version_code"] | 0;
  manifest->artifact_url = String(doc["artifact_url"] | "");
  manifest->artifact_size_bytes = static_cast<size_t>(doc["artifact_size_bytes"] | 0);
  manifest->sha256 = String(doc["sha256"] | "");
  manifest->signature = String(doc["signature"] | "");
  manifest->firmware_channel = String(doc["firmware_channel"] | "");
  manifest->sha256.toLowerCase();

  if (manifest->release_id.length() == 0 || manifest->version.length() == 0) {
    setError(error, "manifest missing release identity");
    return false;
  }
  if (manifest->node_role != String(expected_node_role == nullptr ? "" : expected_node_role)) {
    setError(error, "manifest node role mismatch");
    return false;
  }
  if (manifest->hardware_model.length() > 0 &&
      manifest->hardware_model != String(expected_hardware_model == nullptr ? "" : expected_hardware_model)) {
    setError(error, "manifest hardware model mismatch");
    return false;
  }
  if (manifest->version_code <= current_version_code) {
    setError(error, "manifest version is not newer");
    return false;
  }
  if (!manifest->artifact_url.startsWith("/api/hardware/ota/artifacts/")) {
    setError(error, "manifest artifact URL is not backend-owned");
    return false;
  }
  if (manifest->artifact_size_bytes == 0 || manifest->artifact_size_bytes > kMaxFirmwareArtifactBytes) {
    setError(error, "manifest artifact size is invalid");
    return false;
  }
  if (!isSha256Hex(manifest->sha256)) {
    setError(error, "manifest SHA-256 is invalid");
    return false;
  }
  return true;
}

}  // namespace plantlab
