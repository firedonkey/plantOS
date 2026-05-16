#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include "ota/firmware_manifest.h"
#include "platform/platform_client.h"

namespace plantlab {

class OtaUpdateManager {
 public:
  OtaUpdateManager(
      PlatformClient* client,
      const char* hardware_device_id,
      const char* hardware_model,
      const char* current_version,
      int current_version_code);

  void begin();
  void service(unsigned long now);

 private:
  struct DownloadContext {
    OtaUpdateManager* manager;
    size_t bytes_written;
    String error;
  };

  static bool writeChunk(const uint8_t* bytes, size_t length, void* context);

  bool installManifest(const FirmwareManifest& manifest);
  void reportStatus(
      const char* status,
      const FirmwareManifest* manifest,
      int progress,
      const char* error = nullptr);
  void reportPendingSuccess();
  bool finalizeSha(String* actual_sha);
  String digestHex(const uint8_t* digest, size_t length) const;

  PlatformClient* client_;
  String hardware_device_id_;
  String hardware_model_;
  String current_version_;
  int current_version_code_;
  unsigned long last_check_ms_ = 0;
  bool checked_this_boot_ = false;
  Preferences preferences_;
};

}  // namespace plantlab
