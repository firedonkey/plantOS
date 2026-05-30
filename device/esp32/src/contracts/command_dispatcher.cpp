#include "contracts/command_dispatcher.h"

#include "contracts/plantlab_contracts.h"

namespace plantlab {
namespace contracts {

bool isSupportedMasterCommand(const PlatformCommand& command) {
  if (!command.contract_native) {
    return true;
  }
  if (command.command_type == PLANTLAB_COMMAND_SET_LIGHT_BRIGHTNESS &&
      command.target == "light" &&
      command.action == "set_intensity") {
    return true;
  }
  if (command.command_type == PLANTLAB_COMMAND_CAPTURE_IMAGE &&
      command.target == "camera" &&
      command.action == "capture") {
    return true;
  }
  if (command.command_type == PLANTLAB_COMMAND_REQUEST_DIAGNOSTICS &&
      command.target == "diagnostics" &&
      command.action == "request") {
    return true;
  }
  if (command.command_type == PLANTLAB_COMMAND_REBOOT &&
      command.target == "system" &&
      command.action == "reboot") {
    return true;
  }
  if (command.command_type == PLANTLAB_COMMAND_START_OTA &&
      command.target == "ota" &&
      command.action == "start") {
    return true;
  }
  return false;
}

const char* unsupportedCommandErrorCode(const PlatformCommand& command) {
  if (command.command_type == PLANTLAB_COMMAND_ENTER_PAIRING_MODE ||
      command.command_type == PLANTLAB_COMMAND_FACTORY_RESET ||
      command.command_type == PLANTLAB_COMMAND_UPDATE_CAPTURE_INTERVAL) {
    return PLANTLAB_COMMAND_ERROR_UNSUPPORTED_TARGET;
  }
  return PLANTLAB_COMMAND_ERROR_UNKNOWN_COMMAND;
}

}  // namespace contracts
}  // namespace plantlab
