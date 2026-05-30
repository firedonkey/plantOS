#include "ota/ota_update_manager.h"

#include <ArduinoJson.h>
#include <ESP.h>
#include <Update.h>
#include <esp_ota_ops.h>
#include <mbedtls/sha256.h>

#include "contracts/ota_status_reporter.h"
#include "contracts/plantlab_contracts.h"

namespace plantlab {
namespace {
constexpr char kOtaPreferencesNamespace[] = "plantlab_ota";
constexpr char kPendingVersionKey[] = "pending_ver";
constexpr char kPendingReleaseKey[] = "pending_rel";
constexpr char kPendingCommandIdKey[] = "pending_cmd";
constexpr char kPendingCommandTypeKey[] = "pending_cmd_type";
constexpr char kPendingLegacyCommandIdKey[] = "pending_cmd_num";
constexpr unsigned long kInitialOtaDelayMs = 60000UL;
constexpr unsigned long kOtaCheckIntervalMs = 6UL * 60UL * 60UL * 1000UL;
constexpr size_t kOtaProgressLogIntervalBytes = 128UL * 1024UL;
#ifdef UPDATE_SIZE_UNKNOWN
constexpr size_t kUpdateSizeUnknown = UPDATE_SIZE_UNKNOWN;
#else
constexpr size_t kUpdateSizeUnknown = 0xFFFFFFFFUL;
#endif
mbedtls_sha256_context g_sha_context;

bool isSha256Hex(const String& value) {
  if (value.length() != 64) {
    return false;
  }
  for (size_t index = 0; index < value.length(); ++index) {
    const char c = value.charAt(index);
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) {
      return false;
    }
  }
  return true;
}

}  // namespace

OtaUpdateManager::OtaUpdateManager(
    PlatformClient* client,
    const char* hardware_device_id,
    const char* node_role,
    const char* hardware_model,
    const char* current_version,
    int current_version_code)
    : client_(client),
      hardware_device_id_(hardware_device_id == nullptr ? "" : hardware_device_id),
      node_role_(node_role == nullptr ? "" : node_role),
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
  if (update_in_progress_) {
    return;
  }
  if (node_role_.length() == 0) {
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
          node_role_.c_str(),
          current_version_.c_str(),
          &response,
          &error)) {
    Serial.printf("[ota] manifest fetch failed: %s\n", error.c_str());
    return;
  }

  FirmwareManifest manifest;
  if (!parseFirmwareManifest(
          response,
          node_role_.c_str(),
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

  reportStatus(PLANTLAB_OTA_STATUS_AVAILABLE, &manifest, 0);
  if (!installManifest(manifest)) {
    return;
  }
}

bool OtaUpdateManager::update_in_progress() const {
  return update_in_progress_;
}

const String& OtaUpdateManager::current_status() const {
  return current_status_;
}

bool OtaUpdateManager::startContractUpdate(const OtaStartRequest& request, String* error) {
  if (client_ == nullptr || !client_->configured()) {
    if (error != nullptr) {
      *error = "OTA client is not configured";
    }
    return false;
  }
  if (update_in_progress_) {
    if (error != nullptr) {
      *error = "OTA update already in progress";
    }
    return false;
  }
  if (!validateContractRequest(request, error)) {
    return false;
  }

  String artifact_path;
  if (!normalizeContractArtifactUrl(request.download_url, &artifact_path, error)) {
    return false;
  }

  FirmwareManifest manifest;
  manifest.update_available = true;
  manifest.release_id = request.release_id.length() > 0 ? request.release_id : request.command_id;
  if (manifest.release_id.length() == 0) {
    manifest.release_id = "contract-" + request.target_version;
  }
  manifest.node_role = node_role_;
  manifest.hardware_model = hardware_model_;
  manifest.version = request.target_version;
  manifest.version_code = current_version_code_ + 1;
  manifest.artifact_url = artifact_path;
  manifest.artifact_size_bytes = request.artifact_size_bytes;
  manifest.sha256 = request.checksum_sha256;
  manifest.sha256.toLowerCase();
  manifest.firmware_channel = request.firmware_channel.length() > 0 ? request.firmware_channel : PLANTLAB_OTA_CHANNEL_STABLE;

  active_command_id_ = request.command_id;
  active_command_type_ = request.command_type.length() > 0 ? request.command_type : PLANTLAB_COMMAND_START_OTA;
  active_legacy_command_id_ = request.legacy_command_id;
  update_in_progress_ = true;

  reportContractCommandStatus(PLANTLAB_COMMAND_STATUS_IN_PROGRESS, "OTA update started");
  const bool installed = installManifest(manifest);
  if (!installed) {
    update_in_progress_ = false;
    active_command_id_ = "";
    active_command_type_ = "";
    active_legacy_command_id_ = 0;
    if (error != nullptr && error->length() == 0) {
      *error = "OTA install failed";
    }
  }
  return installed;
}

bool OtaUpdateManager::validateContractRequest(const OtaStartRequest& request, String* error) const {
  if (request.target_version.length() == 0) {
    if (error != nullptr) {
      *error = "START_OTA missing target_version";
    }
    return false;
  }
  if (request.download_url.length() == 0) {
    if (error != nullptr) {
      *error = "START_OTA missing download_url";
    }
    return false;
  }
  if (request.hardware_model.length() > 0 && request.hardware_model != hardware_model_) {
    if (error != nullptr) {
      *error = "START_OTA hardware_model is not supported";
    }
    return false;
  }
  if (request.checksum_sha256.length() > 0 && !isSha256Hex(request.checksum_sha256)) {
    if (error != nullptr) {
      *error = "START_OTA checksum_sha256 is invalid";
    }
    return false;
  }
  return true;
}

bool OtaUpdateManager::normalizeContractArtifactUrl(const String& download_url, String* artifact_path, String* error) const {
  String normalized = download_url;
  normalized.trim();
  if (client_ != nullptr && normalized.startsWith(client_->base_url())) {
    normalized.remove(0, client_->base_url().length());
  }
  if (!normalized.startsWith("/api/hardware/ota/artifacts/")) {
    if (error != nullptr) {
      *error = "START_OTA download_url must be backend-owned";
    }
    return false;
  }
  if (artifact_path != nullptr) {
    *artifact_path = normalized;
  }
  return true;
}

bool OtaUpdateManager::reportContractCommandStatus(const char* status, const char* message, const char* error_code) {
  if (active_legacy_command_id_ <= 0 || active_command_id_.length() == 0 || client_ == nullptr || !client_->configured()) {
    return false;
  }
  PlatformCommand command;
  command.id = active_legacy_command_id_;
  command.target = "ota";
  command.action = "start";
  command.valid = true;
  command.contract_native = true;
  command.command_id = active_command_id_;
  command.command_type = active_command_type_.length() > 0 ? active_command_type_ : PLANTLAB_COMMAND_START_OTA;
  String report_error;
  return client_->report_contract_command_result(
      command,
      hardware_device_id_.c_str(),
      node_role_.c_str(),
      status,
      message,
      false,
      false,
      &report_error,
      -1,
      error_code);
}

bool OtaUpdateManager::installManifest(const FirmwareManifest& manifest) {
  Serial.printf("[ota] installing release=%s version=%s\n", manifest.release_id.c_str(), manifest.version.c_str());
  reportStatus(PLANTLAB_OTA_STATUS_PREPARING, &manifest, 0);
  reportStatus(PLANTLAB_OTA_STATUS_DOWNLOADING, &manifest, 0);

  const size_t expected_artifact_size = manifest.artifact_size_bytes;
  const size_t update_size = expected_artifact_size > 0 ? expected_artifact_size : kUpdateSizeUnknown;
  Serial.printf(
      "[ota] Update.begin release=%s expected_bytes=%lu update_size=%lu free_heap=%lu\n",
      manifest.release_id.c_str(),
      static_cast<unsigned long>(expected_artifact_size),
      static_cast<unsigned long>(update_size),
      static_cast<unsigned long>(ESP.getFreeHeap()));
  const bool update_begin_ok = Update.begin(update_size, U_FLASH);
  Serial.printf(
      "[ota] Update.begin result=%s error=%u message=%s free_heap=%lu\n",
      update_begin_ok ? "ok" : "failed",
      static_cast<unsigned int>(Update.getError()),
      Update.errorString(),
      static_cast<unsigned long>(ESP.getFreeHeap()));
  if (!update_begin_ok) {
    String error = Update.errorString();
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        error.c_str(),
        PLANTLAB_OTA_FAILURE_INSTALL_FAILED);
    return false;
  }

  mbedtls_sha256_init(&g_sha_context);
  mbedtls_sha256_starts(&g_sha_context, 0);

  DownloadContext context{this, 0, "", kOtaProgressLogIntervalBytes, 0};
  String error;
  const bool downloaded = client_->download_ota_artifact(
      manifest.artifact_url,
      &OtaUpdateManager::writeChunk,
      &context,
      &error);
  if (!downloaded) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    const String failure = context.error.length() > 0 ? context.error : error;
    Serial.printf(
        "[ota] download failed release=%s bytes_written=%lu error=%s free_heap=%lu\n",
        manifest.release_id.c_str(),
        static_cast<unsigned long>(context.bytes_written),
        failure.c_str(),
        static_cast<unsigned long>(ESP.getFreeHeap()));
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        failure.c_str(),
        PLANTLAB_OTA_FAILURE_DOWNLOAD_FAILED);
    return false;
  }
  if (context.error.length() > 0) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        context.error.c_str(),
        PLANTLAB_OTA_FAILURE_DOWNLOAD_FAILED);
    return false;
  }
  if (expected_artifact_size > 0 && context.bytes_written != expected_artifact_size) {
    Update.abort();
    mbedtls_sha256_free(&g_sha_context);
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        "artifact length mismatch",
        PLANTLAB_OTA_FAILURE_VALIDATION_FAILED);
    return false;
  }

  reportStatus(PLANTLAB_OTA_STATUS_VALIDATING, &manifest, 95);
  String actual_sha;
  if (!finalizeSha(&actual_sha) || (manifest.sha256.length() > 0 && actual_sha != manifest.sha256)) {
    Update.abort();
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        "artifact SHA-256 mismatch",
        PLANTLAB_OTA_FAILURE_CHECKSUM_MISMATCH);
    return false;
  }

  if (!Update.end(true)) {
    String update_error = Update.errorString();
    Serial.printf(
        "[ota] Update.end failed release=%s error=%u message=%s free_heap=%lu\n",
        manifest.release_id.c_str(),
        static_cast<unsigned int>(Update.getError()),
        update_error.c_str(),
        static_cast<unsigned long>(ESP.getFreeHeap()));
    reportStatus(
        PLANTLAB_OTA_STATUS_FAILED,
        &manifest,
        0,
        update_error.c_str(),
        PLANTLAB_OTA_FAILURE_INSTALL_FAILED);
    return false;
  }
  Serial.printf(
      "[ota] Update.end ok release=%s bytes=%lu free_heap=%lu\n",
      manifest.release_id.c_str(),
      static_cast<unsigned long>(context.bytes_written),
      static_cast<unsigned long>(ESP.getFreeHeap()));

  if (preferences_.begin(kOtaPreferencesNamespace, false)) {
    preferences_.putString(kPendingVersionKey, manifest.version);
    preferences_.putString(kPendingReleaseKey, manifest.release_id);
    if (active_command_id_.length() > 0) {
      preferences_.putString(kPendingCommandIdKey, active_command_id_);
      preferences_.putString(kPendingCommandTypeKey, active_command_type_);
      preferences_.putUInt(kPendingLegacyCommandIdKey, static_cast<uint32_t>(active_legacy_command_id_));
    }
    preferences_.end();
  }
  reportStatus(PLANTLAB_OTA_STATUS_INSTALLING, &manifest, 100);
  reportStatus(PLANTLAB_OTA_STATUS_REBOOTING, &manifest, 100);
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
    download->error =
        "Update.write failed requested=" + String(static_cast<unsigned long>(length)) +
        " written=" + String(static_cast<unsigned long>(written)) +
        " total=" + String(static_cast<unsigned long>(download->bytes_written)) +
        " error=" + String(static_cast<unsigned int>(Update.getError())) +
        " message=" + Update.errorString() +
        " free_heap=" + String(static_cast<unsigned long>(ESP.getFreeHeap()));
    Serial.printf("[ota] %s\n", download->error.c_str());
    return false;
  }
  mbedtls_sha256_update(&g_sha_context, bytes, length);
  download->bytes_written += written;
  ++download->chunks_written;
  if (download->chunks_written == 1 ||
      download->bytes_written >= download->next_progress_log_bytes) {
    Serial.printf(
        "[ota] write progress bytes=%lu chunk=%lu last_write=%lu free_heap=%lu\n",
        static_cast<unsigned long>(download->bytes_written),
        static_cast<unsigned long>(download->chunks_written),
        static_cast<unsigned long>(written),
        static_cast<unsigned long>(ESP.getFreeHeap()));
    while (download->bytes_written >= download->next_progress_log_bytes) {
      download->next_progress_log_bytes += kOtaProgressLogIntervalBytes;
    }
  }
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
    const char* error,
    const char* failure_reason,
    const char* phase) {
  if (status != nullptr && String(status).length() > 0) {
    current_status_ = status;
  }
  if (client_ == nullptr || !client_->configured()) {
    return;
  }
  String report_error;
  const String command_id = active_command_id_.length() > 0
                                ? active_command_id_
                                : contracts::otaCommandIdForRelease(
                                      manifest == nullptr ? nullptr : manifest->release_id.c_str());
  const char* resolved_phase = phase != nullptr ? phase : contracts::otaPhaseForStatus(status);
  const char* resolved_failure_reason =
      failure_reason != nullptr ? failure_reason : contracts::otaFailureReasonForMessage(error);
  String status_message;
  if (error != nullptr && String(error).length() > 0) {
    status_message = error;
  } else {
    status_message = "OTA ";
    status_message += status == nullptr ? "status" : status;
  }
  const bool contract_reported = client_->report_contract_ota_status(
      hardware_device_id_.c_str(),
      node_role_.c_str(),
      command_id.c_str(),
      status,
      manifest == nullptr ? nullptr : manifest->release_id.c_str(),
      manifest == nullptr ? nullptr : manifest->version.c_str(),
      current_version_.c_str(),
      progress,
      manifest == nullptr ? nullptr : manifest->firmware_channel.c_str(),
      resolved_phase,
      resolved_failure_reason,
      status_message.c_str(),
      &report_error);
  if (String(status == nullptr ? "" : status) == PLANTLAB_OTA_STATUS_FAILED) {
    reportContractCommandStatus(
        PLANTLAB_COMMAND_STATUS_FAILED,
        error == nullptr ? "OTA update failed" : error,
        resolved_failure_reason == nullptr ? PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR : PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR);
  }
  if (contract_reported) {
    return;
  }
  report_error = "";
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
  const String pending_command_id = preferences_.getString(kPendingCommandIdKey, "");
  const String pending_command_type = preferences_.getString(kPendingCommandTypeKey, "");
  const int pending_legacy_command_id = static_cast<int>(preferences_.getUInt(kPendingLegacyCommandIdKey, 0));
  if (pending_version.length() > 0 && pending_version == current_version_ && client_ != nullptr && client_->configured()) {
    String error;
    const String command_id = pending_command_id.length() > 0
                                  ? pending_command_id
                                  : contracts::otaCommandIdForRelease(pending_release.c_str());
    bool reported = client_->report_contract_ota_status(
        hardware_device_id_.c_str(),
        node_role_.c_str(),
        command_id.c_str(),
        PLANTLAB_OTA_STATUS_SUCCESS,
        pending_release.c_str(),
        pending_version.c_str(),
        current_version_.c_str(),
        100,
        nullptr,
        PLANTLAB_OTA_PHASE_COMPLETED,
        nullptr,
        "OTA completed successfully",
        &error);
    if (!reported) {
      error = "";
      reported = client_->report_ota_status(
        hardware_device_id_.c_str(),
        PLANTLAB_OTA_STATUS_SUCCESS,
        pending_release.c_str(),
        pending_version.c_str(),
        current_version_.c_str(),
        100,
        nullptr,
        &error);
    }
    bool command_reported = true;
    if (reported && pending_command_id.length() > 0 && pending_legacy_command_id > 0) {
      PlatformCommand command;
      command.id = pending_legacy_command_id;
      command.target = "ota";
      command.action = "start";
      command.valid = true;
      command.contract_native = true;
      command.command_id = pending_command_id;
      command.command_type = pending_command_type.length() > 0 ? pending_command_type : PLANTLAB_COMMAND_START_OTA;
      String command_error;
      command_reported = client_->report_contract_command_result(
          command,
          hardware_device_id_.c_str(),
          node_role_.c_str(),
          PLANTLAB_COMMAND_STATUS_COMPLETED,
          "OTA completed successfully",
          false,
          false,
          &command_error,
          -1,
          nullptr);
    }
    if (reported && command_reported) {
      preferences_.remove(kPendingVersionKey);
      preferences_.remove(kPendingReleaseKey);
      preferences_.remove(kPendingCommandIdKey);
      preferences_.remove(kPendingCommandTypeKey);
      preferences_.remove(kPendingLegacyCommandIdKey);
    }
  }
  preferences_.end();
}

}  // namespace plantlab
