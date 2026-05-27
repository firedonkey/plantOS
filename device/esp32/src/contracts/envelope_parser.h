#pragma once

#include <Arduino.h>

#include "platform/platform_client.h"

namespace plantlab {
namespace contracts {

int parseCommandPollResponse(
    const String& response_body,
    PlatformCommand* commands,
    size_t max_commands,
    String* error = nullptr);

int parseContractCommandId(const String& command_id);

}  // namespace contracts
}  // namespace plantlab
