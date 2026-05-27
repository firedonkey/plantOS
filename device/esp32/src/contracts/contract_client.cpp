#include "contracts/contract_client.h"

#include "contracts/plantlab_contracts.h"

namespace plantlab {
namespace contracts {
namespace {

bool hasText(const char* value) {
  return value != nullptr && String(value).length() > 0;
}

}  // namespace

bool validateSchemaVersion(const char* schema_version, String* error) {
  const String value = schema_version == nullptr ? String("") : String(schema_version);
  const int dot = value.indexOf('.');
  if (dot <= 0) {
    if (error != nullptr) {
      *error = "schema_version must use MAJOR.MINOR";
    }
    return false;
  }
  if (value.substring(0, dot).toInt() != 1) {
    if (error != nullptr) {
      *error = "unsupported schema major version";
    }
    return false;
  }
  return true;
}

bool validateCommandPollMetadata(
    const char* hardware_device_id,
    const char* node_role,
    const char* firmware_version,
    String* error) {
  if (!hasText(hardware_device_id)) {
    if (error != nullptr) {
      *error = "missing hardware_device_id";
    }
    return false;
  }
  if (!hasText(node_role)) {
    if (error != nullptr) {
      *error = "missing node_role";
    }
    return false;
  }
  if (!hasText(firmware_version)) {
    if (error != nullptr) {
      *error = "missing firmware_version";
    }
    return false;
  }
  return true;
}

}  // namespace contracts
}  // namespace plantlab
