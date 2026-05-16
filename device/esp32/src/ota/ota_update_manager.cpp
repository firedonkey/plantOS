#include "ota/ota_update_manager.h"

#include <ArduinoJson.h>
#include <ESP.h>
#include <Update.h>
#include <esp_ota_ops.h>
#include <mbedtls/sha256.h>

namespace plantlab {
namespace {
constexpr char kOtaPreferencesNamespace[] = "plantlab_ota";
constexpr char kPendingVersionKey[] = "pending_ver";
constexpr char kPendingReleaseKey[] = "pending_rel";
constexpr unsigned long kInitialOtaDelayMs = 60000UL;
constexpr unsigned long kOtaCheckIntervalMs = 6UL * 60UL * 60UL * 1000UL;
mbedtls_sha256_context g_sha_context;

}  // namespace

OtaUpdateManager::OtaUpdateManager(
    PlatformClient* client,
    const char* hardware_device_id,
    const char* hardware_model,
    const char* current_version,
    int current_version_code)
    : client_(client),
      hardware_device_id_(hardware_device_id == nullptr ? "" : hardware_device_id),
      hardware_model_(hardware_model == nullptr ? "" : hardware_model),
      current_version_(current_version == nullptr ? "" : current_version),
      current_version_code_(current_version_code) {}

void OtaUpdateManager::begin() {
  esp_ota_mark_app_valid_cancel_rollback();
}

void OtaUpdateManager::service(unsigned long now) {
  if (client_ == nullptr || !client_->configured() || hardware_device_id_.length() == 0) {
    return;
  }
  if (!checked_this_boot_ && now < kInitialOtaDelayMs) {
    return;
  }
  if (checked_this_boot_ && now - last_check_ms_ < kOtaCheckIntervalMs) {
    return;
  }
  checked_this_boot_ = true;
  last_check_ms_ = now;
  reportPendingSuccess();

  String response;
  String error;
  if (!client_->fetch_ota_manifest(
          hardware_device_id_.c_str(),
          "master",
          current_version_.c_str(),
          &response,
          &error)) {
    Serial.printf("[ota] manifest fetch failed: %s\n", error.c_str());
    return;
  }

  FirmwareManifest manifest;
  if (!parseFirmwareManifest(
          response,
          "master",
          hardware_model_.c_str(),
          current_version_code_,
          &manifest,
          &error)) {
    Serial.printf("[ota] manifest rejected: %s\n", error.c_str());
    return;
  }
  if (!manifest.update_available) {
    return;
  }

  reportStatus("available", &manifest, 0);
  if (!installManifest(manifest)) {
    return;
  }
}

bool OtaUpdateManager::installManifest(const FirmwareManifest& manifest) {
  Serial.printf("[ota] installing release=%s version=%s\n", manifest.release_id.c_str(), manifest.version.c_str());
  reportStatus("downloading", &manifest, 0);

  if (!Update.begin(manifest.artifact_size_bytes, U_FLASH)) {
    String error = Update.errorString();
    reportStatus("failed", &manifest, 0, error.c_str());
    return false;
  }

  mbedtls_sha256_init(&g_sha_context);
  mbedtls_sha256_starts(&g_sha_context, 0);

  DownloadContext context{this, 0, ""};
  String error;
  const bool downloaded = client_->download_ota_artifact(
      manifest.artifact_url,
      &OtaUpdateManager::writeChunk,
      &context,
      &error);
  if (!downloaded) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    reportStatus("failed", &manifest, 0, error.c_str());
    return false;
  }
  if (context.error.length() > 0) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    reportStatus("failed", &manifest, 0, context.error.c_str());
    return false;
  }
  if (context.bytes_written != manifest.artifact_size_bytes) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    reportStatus("failed", &manifest, 0, "artifact length mismatch");
    return false;
  }

  String actual_sha;
  if (!finalizeSha(&actual_sha) || actual_sha != manifest.sha256) {
    Update.abort();
    reportStatus("failed", &manifest, 0, "artifact SHA-256 mismatch");
    return false;
  }

  if (!Update.end(true)) {
    String update_error = Update.errorString();
    reportStatus("failed", &manifest, 0, update_error.c_str());
    return false;
  }

  if (preferences_.begin(kOtaPreferencesNamespace, false)) {
    preferences_.putString(kPendingVersionKey, manifest.version);
    preferences_.putString(kPendingReleaseKey, manifest.release_id);
    preferences_.end();
  }
  reportStatus("installing", &manifest, 100);
  delay(250);
  ESP.restart();
  return true;
}

bool OtaUpdateManager::writeChunk(const uint8_t* bytes, size_t length, void* context) {
  DownloadContext* download = static_cast<DownloadContext*>(context);
  if (download == nullptr || download->manager == nullptr || bytes == nullptr || length == 0) {
    return false;
  }
  const size_t written = Update.write(const_cast<uint8_t*>(bytes), length);
  if (written != length) {
    download->error = Update.errorString();
    return false;
  }
  mbedtls_sha256_update(&g_sha_context, bytes, length);
  download->bytes_written += written;
  return true;
}

bool OtaUpdateManager::finalizeSha(String* actual_sha) {
  uint8_t digest[32] = {0};
  mbedtls_sha256_finish(&g_sha_context, digest);
  mbedtls_sha256_free(&g_sha_context);
  if (actual_sha != nullptr) {
    *actual_sha = digestHex(digest, sizeof(digest));
  }
  return true;
}

String OtaUpdateManager::digestHex(const uint8_t* digest, size_t length) const {
  static constexpr char kHex[] = "0123456789abcdef";
  String output;
  output.reserve(length * 2);
  for (size_t i = 0; i < length; ++i) {
    output += kHex[(digest[i] >> 4) & 0x0F];
    output += kHex[digest[i] & 0x0F];
  }
  return output;
}

void OtaUpdateManager::reportStatus(
    const char* status,
    const FirmwareManifest* manifest,
    int progress,
    const char* error) {
  if (client_ == nullptr || !client_->configured()) {
    return;
  }
  String report_error;
  client_->report_ota_status(
      hardware_device_id_.c_str(),
      status,
      manifest == nullptr ? nullptr : manifest->release_id.c_str(),
      manifest == nullptr ? nullptr : manifest->version.c_str(),
      current_version_.c_str(),
      progress,
      error,
      &report_error);
}

void OtaUpdateManager::reportPendingSuccess() {
  if (!preferences_.begin(kOtaPreferencesNamespace, false)) {
    return;
  }
  const String pending_version = preferences_.getString(kPendingVersionKey, "");
  const String pending_release = preferences_.getString(kPendingReleaseKey, "");
  if (pending_version.length() > 0 && pending_version == current_version_ && client_ != nullptr && client_->configured()) {
    String error;
    const bool reported = client_->report_ota_status(
        hardware_device_id_.c_str(),
        "success",
        pending_release.c_str(),
        pending_version.c_str(),
        current_version_.c_str(),
        100,
        nullptr,
        &error);
    if (reported) {
      preferences_.remove(kPendingVersionKey);
      preferences_.remove(kPendingReleaseKey);
    }
  }
  preferences_.end();
}

}  // namespace plantlab
