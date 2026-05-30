#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include "ota/firmware_manifest.h"
#include "platform/platform_client.h"

namespace plantlab {

struct OtaStartRequest {
  int legacy_command_id = 0;
  String command_id;
  String command_type;
  String target_version;
  String download_url;
  String checksum_sha256;
  String hardware_model;
  String firmware_channel;
  String release_id;
  size_t artifact_size_bytes = 0;
};

class OtaUpdateManager {
 public:
  OtaUpdateManager(
      PlatformClient* client,
      const char* hardware_device_id,
      const char* node_role,
      const char* hardware_model,
      const char* current_version,
      int current_version_code);

  void begin();
  void service(unsigned long now);
  bool startContractUpdate(const OtaStartRequest& request, String* error = nullptr);
  bool update_in_progress() const;
  const String& current_status() const;

 private:
  struct DownloadContext {
    OtaUpdateManager* manager;
    size_t bytes_written;
    String error;
    size_t next_progress_log_bytes;
    uint32_t chunks_written;
  };

  static bool writeChunk(const uint8_t* bytes, size_t length, void* context);

  bool installManifest(const FirmwareManifest& manifest);
  bool normalizeContractArtifactUrl(const String& download_url, String* artifact_path, String* error) const;
  bool validateContractRequest(const OtaStartRequest& request, String* error) const;
  bool reportContractCommandStatus(const char* status, const char* message, const char* error_code = nullptr);
  void reportStatus(
      const char* status,
      const FirmwareManifest* manifest,
      int progress,
      const char* error = nullptr,
      const char* failure_reason = nullptr,
      const char* phase = nullptr);
  void reportPendingSuccess();
  bool finalizeSha(String* actual_sha);
  String digestHex(const uint8_t* digest, size_t length) const;

  PlatformClient* client_;
  String hardware_device_id_;
  String node_role_;
  String hardware_model_;
  String current_version_;
  int current_version_code_;
  bool update_in_progress_ = false;
  String current_status_ = "idle";
  String active_command_id_;
  String active_command_type_;
  int active_legacy_command_id_ = 0;
  unsigned long last_check_ms_ = 0;
  bool checked_this_boot_ = false;
  Preferences preferences_;
};

}  // namespace plantlab
