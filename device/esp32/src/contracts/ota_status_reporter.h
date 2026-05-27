#pragma once

#include <Arduino.h>

namespace plantlab {
namespace contracts {

String otaCommandIdForRelease(const char* release_id);
const char* otaPhaseForStatus(const char* status);
const char* otaFailureReasonForMessage(const char* message);

}  // namespace contracts
}  // namespace plantlab
