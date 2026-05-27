#pragma once

#include <Arduino.h>

namespace plantlab {
namespace contracts {

bool validateSchemaVersion(const char* schema_version, String* error = nullptr);
bool validateCommandPollMetadata(
    const char* hardware_device_id,
    const char* node_role,
    const char* firmware_version,
    String* error = nullptr);

}  // namespace contracts
}  // namespace plantlab
