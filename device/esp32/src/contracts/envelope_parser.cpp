#include "contracts/envelope_parser.h"

#include <ArduinoJson.h>

#include "contracts/contract_client.h"
#include "contracts/plantlab_contracts.h"

namespace plantlab {
namespace contracts {
namespace {

int boundedPercent(JsonVariantConst value, int fallback) {
  if (!value.is<int>()) {
    return fallback;
  }
  const int parsed = value.as<int>();
  if (parsed < 0) {
    return 0;
  }
  if (parsed > 100) {
    return 100;
  }
  return parsed;
}

bool mapCommandPayload(JsonObjectConst payload, PlatformCommand* command, String* error) {
  if (command == nullptr) {
    return false;
  }

  const char* command_id = payload["command_id"] | "";
  const char* command_type = payload["command_type"] | "";
  if (String(command_id).length() == 0 || String(command_type).length() == 0) {
    if (error != nullptr) {
      *error = "command payload missing command_id or command_type";
    }
    return false;
  }

  command->id = parseContractCommandId(String(command_id));
  command->command_id = command_id;
  command->command_type = command_type;
  command->contract_native = true;
  command->target_node_role = payload["target"]["node_role"] | "";
  command->target_hardware_device_id = payload["target"]["hardware_device_id"] | "";

  JsonObjectConst params = payload["params"].as<JsonObjectConst>();
  if (String(command_type) == PLANTLAB_COMMAND_SET_LIGHT_BRIGHTNESS) {
    const int brightness = boundedPercent(params["brightness_percent"], 100);
    command->target = "light";
    command->action = "set_intensity";
    command->value = String(brightness);
  } else if (String(command_type) == PLANTLAB_COMMAND_CAPTURE_IMAGE) {
    command->target = "camera";
    command->action = "capture";
    command->value = params["reason"] | "";
  } else if (String(command_type) == PLANTLAB_COMMAND_REBOOT) {
    command->target = "system";
    command->action = "reboot";
    command->value = "";
  } else if (String(command_type) == PLANTLAB_COMMAND_START_OTA) {
    command->target = "ota";
    command->action = "start";
    command->ota_target_version = params["target_version"] | "";
    command->ota_download_url = params["download_url"] | "";
    command->ota_checksum_sha256 = params["checksum_sha256"] | "";
    command->ota_hardware_model = params["hardware_model"] | "";
    command->ota_firmware_channel = params["firmware_channel"] | "";
    command->ota_release_id = params["release_id"] | "";
    if (params["artifact_size_bytes"].is<size_t>()) {
      command->ota_artifact_size_bytes = params["artifact_size_bytes"].as<size_t>();
    }
    command->value = command->ota_target_version;
  } else if (String(command_type) == PLANTLAB_COMMAND_ENTER_PAIRING_MODE) {
    command->target = "provisioning";
    command->action = "enter_pairing";
    command->value = "";
  } else if (String(command_type) == PLANTLAB_COMMAND_FACTORY_RESET) {
    command->target = "system";
    command->action = "factory_reset";
    command->value = "";
  } else if (String(command_type) == PLANTLAB_COMMAND_REQUEST_DIAGNOSTICS) {
    command->target = "diagnostics";
    command->action = "request";
    command->value = "";
  } else if (String(command_type) == PLANTLAB_COMMAND_UPDATE_CAPTURE_INTERVAL) {
    command->target = "camera";
    command->action = "update_capture_interval";
    if (params["interval_ms"].is<int>()) {
      command->value = String(params["interval_ms"].as<int>());
    } else {
      command->value = "";
    }
  } else {
    if (error != nullptr) {
      *error = "unsupported command_type";
    }
    return false;
  }

  command->valid = command->id > 0 && command->target.length() > 0 && command->action.length() > 0;
  if (!command->valid && error != nullptr) {
    *error = "contract command_id must be formatted as cmd_<number>";
  }
  return command->valid;
}

}  // namespace

int parseContractCommandId(const String& command_id) {
  String normalized = command_id;
  normalized.trim();
  if (normalized.startsWith("cmd_")) {
    normalized.remove(0, 4);
  }
  if (normalized.length() == 0) {
    return 0;
  }
  for (size_t index = 0; index < normalized.length(); ++index) {
    const char value = normalized.charAt(index);
    if (value < '0' || value > '9') {
      return 0;
    }
  }
  return normalized.toInt();
}

int parseCommandPollResponse(
    const String& response_body,
    PlatformCommand* commands,
    size_t max_commands,
    String* error) {
  if (commands == nullptr || max_commands == 0) {
    return 0;
  }

  StaticJsonDocument<4096> doc;
  const DeserializationError json_error = deserializeJson(doc, response_body);
  if (json_error) {
    if (error != nullptr) {
      *error = "contract command poll JSON parse failed";
    }
    return -1;
  }

  const char* schema_version = doc["schema_version"] | "";
  if (!validateSchemaVersion(schema_version, error)) {
    return -1;
  }

  JsonArrayConst command_array = doc["commands"].as<JsonArrayConst>();
  if (command_array.isNull()) {
    if (error != nullptr) {
      *error = "contract command poll missing commands array";
    }
    return -1;
  }

  size_t count = 0;
  for (JsonObjectConst envelope : command_array) {
    if (count >= max_commands) {
      break;
    }
    const char* envelope_schema = envelope["schema_version"] | "";
    if (!validateSchemaVersion(envelope_schema, error)) {
      return -1;
    }
    const char* message_type = envelope["message_type"] | "";
    if (String(message_type) != PLANTLAB_MESSAGE_TYPE_COMMAND) {
      if (error != nullptr) {
        *error = "contract command poll received non-COMMAND envelope";
      }
      return -1;
    }
    JsonObjectConst payload = envelope["payload"].as<JsonObjectConst>();
    if (payload.isNull()) {
      if (error != nullptr) {
        *error = "contract command envelope missing payload";
      }
      return -1;
    }

    PlatformCommand parsed{};
    if (!mapCommandPayload(payload, &parsed, error)) {
      return -1;
    }
    commands[count] = parsed;
    ++count;
  }
  return static_cast<int>(count);
}

}  // namespace contracts
}  // namespace plantlab
