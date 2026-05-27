#pragma once

#include <Arduino.h>

namespace plantlab {

struct FirmwareManifest {
  bool update_available = false;
  String release_id;
  String node_role;
  String hardware_model;
  String version;
  int version_code = 0;
  String artifact_url;
  size_t artifact_size_bytes = 0;
  String sha256;
  String signature;
  String firmware_channel;
};

bool parseFirmwareManifest(
    const String& json,
    const char* expected_node_role,
    const char* expected_hardware_model,
    int current_version_code,
    FirmwareManifest* manifest,
    String* error);

}  // namespace plantlab
