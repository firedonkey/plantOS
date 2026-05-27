#include "contracts/ota_status_reporter.h"

#include "contracts/plantlab_contracts.h"

namespace plantlab {
namespace contracts {

String otaCommandIdForRelease(const char* release_id) {
  String command_id = "ota";
  if (release_id != nullptr && String(release_id).length() > 0) {
    command_id += "_";
    command_id += release_id;
  }
  return command_id;
}

const char* otaPhaseForStatus(const char* status) {
  const String value = status == nullptr ? String("") : String(status);
  if (value == PLANTLAB_OTA_STATUS_AVAILABLE) {
    return PLANTLAB_OTA_PHASE_CHECK;
  }
  if (value == PLANTLAB_OTA_STATUS_PREPARING) {
    return PLANTLAB_OTA_PHASE_PREPARE;
  }
  if (value == PLANTLAB_OTA_STATUS_DOWNLOADING) {
    return PLANTLAB_OTA_PHASE_DOWNLOAD;
  }
  if (value == PLANTLAB_OTA_STATUS_VALIDATING) {
    return PLANTLAB_OTA_PHASE_VALIDATE;
  }
  if (value == PLANTLAB_OTA_STATUS_INSTALLING) {
    return PLANTLAB_OTA_PHASE_INSTALL;
  }
  if (value == PLANTLAB_OTA_STATUS_REBOOTING) {
    return PLANTLAB_OTA_PHASE_REBOOT;
  }
  if (value == PLANTLAB_OTA_STATUS_SUCCESS) {
    return PLANTLAB_OTA_PHASE_COMPLETED;
  }
  if (value == PLANTLAB_OTA_STATUS_ROLLED_BACK) {
    return PLANTLAB_OTA_PHASE_ROLLBACK;
  }
  return nullptr;
}

const char* otaFailureReasonForMessage(const char* message) {
  const String value = message == nullptr ? String("") : String(message);
  if (value.indexOf("SHA-256") >= 0 || value.indexOf("checksum") >= 0) {
    return PLANTLAB_OTA_FAILURE_CHECKSUM_MISMATCH;
  }
  if (value.indexOf("download") >= 0 || value.indexOf("network") >= 0) {
    return PLANTLAB_OTA_FAILURE_DOWNLOAD_FAILED;
  }
  if (value.indexOf("length mismatch") >= 0) {
    return PLANTLAB_OTA_FAILURE_VALIDATION_FAILED;
  }
  if (value.indexOf("timed out") >= 0 || value.indexOf("timeout") >= 0) {
    return PLANTLAB_OTA_FAILURE_TIMEOUT;
  }
  if (value.length() > 0) {
    return PLANTLAB_OTA_FAILURE_INSTALL_FAILED;
  }
  return nullptr;
}

}  // namespace contracts
}  // namespace plantlab
