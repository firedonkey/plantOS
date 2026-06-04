#include "contracts/envelope_builder.h"

#include <ArduinoJson.h>

#include "contracts/plantlab_contracts.h"
#include "time/time_sync_manager.h"

namespace plantlab {
namespace contracts {
namespace {

const char* safeText(const char* value, const char* fallback = "") {
  return value == nullptr ? fallback : value;
}

String makeMessageId(const char* prefix, const char* id) {
  String message_id = prefix == nullptr ? "msg" : String(prefix);
  message_id += "_";
  if (id != nullptr && String(id).length() > 0) {
    message_id += id;
    message_id += "_";
  }
  message_id += String(millis());
  return message_id;
}

void addBaseEnvelope(
    JsonDocument& doc,
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* message_type,
    const String& message_id) {
  doc["schema_version"] = PLANTLAB_CONTRACT_SCHEMA_VERSION;
  doc["message_id"] = message_id;
  if (device_id > 0) {
    doc["device_id"] = device_id;
  }
  doc["hardware_device_id"] = safeText(hardware_device_id);
  doc["node_role"] = safeText(node_role, PLANTLAB_NODE_ROLE_MASTER);
  doc["message_type"] = safeText(message_type);
  char sent_at[32]{};
  plantlab::time_sync::currentUtcIso8601(sent_at, sizeof(sent_at));
  doc["sent_at"] = sent_at;
}

}  // namespace

bool buildHeartbeatEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* node_status,
    const char* firmware_version,
    const char* hardware_model,
    const char* hardware_version,
    uint32_t uptime_seconds,
    bool has_wifi_rssi_dbm,
    int wifi_rssi_dbm,
    const char* ip_address,
    bool has_free_heap_bytes,
    uint32_t free_heap_bytes,
    bool include_light_state,
    bool light_enabled,
    int light_brightness_percent,
    bool has_capture_interval_seconds,
    uint32_t capture_interval_seconds,
    const char* ota_status,
    const char* provisioning_status,
    const char* camera_node_status,
    const char* last_command_id,
    const char* last_command_status,
    const char* last_command_poll_at,
    const char* last_command_poll_status,
    const char* last_command_poll_error,
    bool has_last_command_poll_latency_ms,
    uint32_t last_command_poll_latency_ms,
    bool has_command_poll_stale_seconds,
    uint32_t command_poll_stale_seconds,
    String* body) {
  if (body == nullptr || hardware_device_id == nullptr || String(hardware_device_id).length() == 0 ||
      firmware_version == nullptr || String(firmware_version).length() == 0) {
    return false;
  }

  StaticJsonDocument<1792> doc;
  addBaseEnvelope(
      doc,
      device_id,
      hardware_device_id,
      node_role,
      PLANTLAB_MESSAGE_TYPE_HEARTBEAT,
      makeMessageId("heartbeat", hardware_device_id));

  JsonObject payload = doc.createNestedObject("payload");
  payload["uptime_seconds"] = uptime_seconds;
  if (has_wifi_rssi_dbm) {
    payload["wifi_rssi_dbm"] = wifi_rssi_dbm;
  }
  if (ip_address != nullptr && String(ip_address).length() > 0) {
    payload["ip_address"] = ip_address;
  }
  if (has_free_heap_bytes) {
    payload["free_heap_bytes"] = free_heap_bytes;
  }
  payload["node_status"] = node_status == nullptr || String(node_status).length() == 0
                               ? PLANTLAB_DEVICE_STATUS_ONLINE
                               : node_status;
  payload["firmware_version"] = firmware_version;
  if (hardware_model != nullptr && String(hardware_model).length() > 0) {
    payload["hardware_model"] = hardware_model;
  }
  if (hardware_version != nullptr && String(hardware_version).length() > 0) {
    payload["hardware_version"] = hardware_version;
  }

  JsonArray capabilities = payload.createNestedArray("capabilities");
  capabilities.add(PLANTLAB_CAPABILITY_OTA);
  if (include_light_state) {
    capabilities.add(PLANTLAB_CAPABILITY_AMBIENT_LED);
    capabilities.add(PLANTLAB_CAPABILITY_LIGHT_CONTROL);
    if (light_brightness_percent >= 0) {
      capabilities.add(PLANTLAB_CAPABILITY_LIGHT_INTENSITY);
    }
  }
  if (camera_node_status != nullptr && String(camera_node_status).length() > 0) {
    capabilities.add(PLANTLAB_CAPABILITY_CAMERA_GATEWAY);
  }

  if (include_light_state) {
    JsonObject actuators = payload.createNestedObject("actuators");
    JsonObject ambient_light = actuators.createNestedObject("ambient_light");
    ambient_light["enabled"] = light_enabled;
    if (light_brightness_percent >= 0) {
      ambient_light["brightness_percent"] = light_brightness_percent;
    }
  }

  if (has_capture_interval_seconds ||
      (ota_status != nullptr && String(ota_status).length() > 0) ||
      (provisioning_status != nullptr && String(provisioning_status).length() > 0) ||
      (camera_node_status != nullptr && String(camera_node_status).length() > 0) ||
      (last_command_id != nullptr && String(last_command_id).length() > 0) ||
      (last_command_status != nullptr && String(last_command_status).length() > 0) ||
      (last_command_poll_at != nullptr && String(last_command_poll_at).length() > 0) ||
      (last_command_poll_status != nullptr && String(last_command_poll_status).length() > 0) ||
      (last_command_poll_error != nullptr && String(last_command_poll_error).length() > 0) ||
      has_last_command_poll_latency_ms ||
      has_command_poll_stale_seconds ||
      plantlab::time_sync::statusName() != nullptr) {
    JsonObject runtime = payload.createNestedObject("runtime");
    if (has_capture_interval_seconds) {
      runtime["capture_interval_seconds"] = capture_interval_seconds;
    }
    if (ota_status != nullptr && String(ota_status).length() > 0) {
      runtime["ota_status"] = ota_status;
    }
    if (provisioning_status != nullptr && String(provisioning_status).length() > 0) {
      runtime["provisioning_status"] = provisioning_status;
    }
    if (camera_node_status != nullptr && String(camera_node_status).length() > 0) {
      runtime["camera_node_status"] = camera_node_status;
    }
    if (last_command_id != nullptr && String(last_command_id).length() > 0) {
      runtime["last_command_id"] = last_command_id;
    }
    if (last_command_status != nullptr && String(last_command_status).length() > 0) {
      runtime["last_command_status"] = last_command_status;
    }
    if (last_command_poll_at != nullptr && String(last_command_poll_at).length() > 0) {
      runtime["last_command_poll_at"] = last_command_poll_at;
    }
    if (last_command_poll_status != nullptr && String(last_command_poll_status).length() > 0) {
      runtime["last_command_poll_status"] = last_command_poll_status;
    }
    if (last_command_poll_error != nullptr && String(last_command_poll_error).length() > 0) {
      runtime["last_command_poll_error"] = last_command_poll_error;
    }
    if (has_last_command_poll_latency_ms) {
      runtime["last_command_poll_latency_ms"] = last_command_poll_latency_ms;
    }
    if (has_command_poll_stale_seconds) {
      runtime["command_poll_stale_seconds"] = command_poll_stale_seconds;
    }
    runtime["time_sync_status"] = plantlab::time_sync::statusName();
    char last_ntp_sync_at[32]{};
    if (plantlab::time_sync::lastSyncUtcIso8601(last_ntp_sync_at, sizeof(last_ntp_sync_at))) {
      runtime["last_ntp_sync_at"] = last_ntp_sync_at;
    }
  }

  body->remove(0);
  serializeJson(doc, *body);
  return body->length() > 0;
}

bool buildCommandResultEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* command_id,
    const char* command_type,
    const char* status,
    const char* message,
    bool light_on,
    bool pump_on,
    int light_intensity_percent,
    const char* error_code,
    bool include_actuator_state,
    String* body) {
  if (body == nullptr || command_id == nullptr || String(command_id).length() == 0 ||
      command_type == nullptr || String(command_type).length() == 0) {
    return false;
  }

  StaticJsonDocument<768> doc;
  addBaseEnvelope(
      doc,
      device_id,
      hardware_device_id,
      node_role,
      PLANTLAB_MESSAGE_TYPE_COMMAND_RESULT,
      makeMessageId("cmdres", command_id));

  JsonObject payload = doc.createNestedObject("payload");
  payload["command_id"] = command_id;
  payload["command_type"] = command_type;
  payload["status"] = status == nullptr ? PLANTLAB_COMMAND_STATUS_FAILED : status;
  if (message != nullptr && String(message).length() > 0) {
    payload["message"] = message;
  }
  if (error_code != nullptr && String(error_code).length() > 0) {
    payload["error_code"] = error_code;
  }
  JsonObject result = payload.createNestedObject("result");
  if (include_actuator_state) {
    result["light_on"] = light_on;
    result["pump_on"] = pump_on;
    if (light_intensity_percent >= 0) {
      result["light_intensity_percent"] = light_intensity_percent;
    }
  }

  body->remove(0);
  serializeJson(doc, *body);
  return body->length() > 0;
}

bool buildOtaStatusEnvelope(
    int device_id,
    const char* hardware_device_id,
    const char* node_role,
    const char* command_id,
    const char* status,
    const char* release_id,
    const char* target_version,
    const char* current_version,
    int progress,
    const char* firmware_channel,
    const char* phase,
    const char* failure_reason,
    const char* message,
    String* body) {
  if (body == nullptr || hardware_device_id == nullptr || String(hardware_device_id).length() == 0) {
    return false;
  }

  String resolved_command_id = command_id == nullptr ? String("") : String(command_id);
  if (resolved_command_id.length() == 0) {
    resolved_command_id = "ota";
    if (release_id != nullptr && String(release_id).length() > 0) {
      resolved_command_id += "_";
      resolved_command_id += release_id;
    }
  }

  StaticJsonDocument<768> doc;
  addBaseEnvelope(
      doc,
      device_id,
      hardware_device_id,
      node_role,
      PLANTLAB_MESSAGE_TYPE_OTA_STATUS,
      makeMessageId("otamsg", resolved_command_id.c_str()));

  JsonObject payload = doc.createNestedObject("payload");
  payload["command_id"] = resolved_command_id;
  payload["status"] = status == nullptr ? PLANTLAB_OTA_STATUS_FAILED : status;
  if (progress >= 0) {
    payload["progress_percent"] = progress;
  }
  if (current_version != nullptr && String(current_version).length() > 0) {
    payload["current_version"] = current_version;
  }
  if (target_version != nullptr && String(target_version).length() > 0) {
    payload["target_version"] = target_version;
  }
  if (firmware_channel != nullptr && String(firmware_channel).length() > 0) {
    payload["firmware_channel"] = firmware_channel;
  }
  if (phase != nullptr && String(phase).length() > 0) {
    payload["phase"] = phase;
  }
  if (message != nullptr && String(message).length() > 0) {
    payload["message"] = message;
  }
  if (failure_reason != nullptr && String(failure_reason).length() > 0) {
    payload["failure_reason"] = failure_reason;
  }
  if (release_id != nullptr && String(release_id).length() > 0) {
    payload["release_id"] = release_id;
  }

  body->remove(0);
  serializeJson(doc, *body);
  return body->length() > 0;
}

}  // namespace contracts
}  // namespace plantlab
