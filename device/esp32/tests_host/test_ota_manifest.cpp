#include <cassert>
#include <cstring>

#include "ota/firmware_manifest.h"

using plantlab::FirmwareManifest;
using plantlab::parseFirmwareManifest;

namespace {

constexpr const char* kValidSha =
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

String validManifestJson(const char* overrides = "") {
  String json =
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"master\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":2000,"
      "\"artifact_url\":\"/api/hardware/ota/artifacts/master-0.2.0\","
      "\"artifact_size_bytes\":1024,"
      "\"sha256\":\"";
  json += kValidSha;
  json += "\"";
  json += overrides;
  json += "}";
  return json;
}

void expectInvalid(const String& json, const char* expected_error) {
  FirmwareManifest manifest;
  String error;
  assert(!parseFirmwareManifest(json, "master", "esp32-s3-devkitc-1", 1000, &manifest, &error));
  assert(std::strstr(error.c_str(), expected_error) != nullptr);
}

}  // namespace

int main() {
  FirmwareManifest manifest;
  String error;

  assert(parseFirmwareManifest(
      validManifestJson(),
      "master",
      "esp32-s3-devkitc-1",
      1000,
      &manifest,
      &error));
  assert(manifest.update_available);
  assert(manifest.release_id == "master-0.2.0");
  assert(manifest.artifact_url == "/api/hardware/ota/artifacts/master-0.2.0");
  assert(manifest.artifact_size_bytes == 1024);
  assert(manifest.sha256 == kValidSha);

  FirmwareManifest no_update_manifest;
  assert(parseFirmwareManifest(
      "{\"update_available\":false}",
      "master",
      "esp32-s3-devkitc-1",
      1000,
      &no_update_manifest,
      &error));
  assert(!no_update_manifest.update_available);

  expectInvalid(
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"camera\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":2000,"
      "\"artifact_url\":\"/api/hardware/ota/artifacts/master-0.2.0\","
      "\"artifact_size_bytes\":1024,"
      "\"sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\""
      "}",
      "node role");
  expectInvalid(
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"master\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":1000,"
      "\"artifact_url\":\"/api/hardware/ota/artifacts/master-0.2.0\","
      "\"artifact_size_bytes\":1024,"
      "\"sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\""
      "}",
      "not newer");
  expectInvalid(
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"master\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":2000,"
      "\"artifact_url\":\"https://example.com/master.bin\","
      "\"artifact_size_bytes\":1024,"
      "\"sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\""
      "}",
      "backend-owned");
  expectInvalid(
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"master\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":2000,"
      "\"artifact_url\":\"/api/hardware/ota/artifacts/master-0.2.0\","
      "\"artifact_size_bytes\":1024,"
      "\"sha256\":\"not-a-sha\""
      "}",
      "SHA-256");
  expectInvalid(
      "{"
      "\"update_available\":true,"
      "\"release_id\":\"master-0.2.0\","
      "\"node_role\":\"master\","
      "\"hardware_model\":\"esp32-s3-devkitc-1\","
      "\"version\":\"0.2.0\","
      "\"version_code\":2000,"
      "\"artifact_url\":\"/api/hardware/ota/artifacts/master-0.2.0\","
      "\"artifact_size_bytes\":7340032,"
      "\"sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\""
      "}",
      "size");

  return 0;
}
