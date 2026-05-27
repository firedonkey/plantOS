#pragma once

#include "platform/platform_client.h"

namespace plantlab {
namespace contracts {

bool isSupportedMasterCommand(const PlatformCommand& command);
const char* unsupportedCommandErrorCode(const PlatformCommand& command);

}  // namespace contracts
}  // namespace plantlab
