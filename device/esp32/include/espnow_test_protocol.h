#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

constexpr uint32_t ESPNOW_TEST_MAGIC = 0x504C4142;  // "PLAB"
constexpr uint8_t ESPNOW_TEST_VERSION = 1;
constexpr size_t ESPNOW_TEST_MAX_PACKET_BYTES = 250;
constexpr size_t ESPNOW_TEST_WIFI_SSID_MAX_LEN = 32;
constexpr size_t ESPNOW_TEST_WIFI_PASSWORD_MAX_LEN = 63;
constexpr size_t ESPNOW_TEST_PLATFORM_URL_MAX_LEN = 56;
constexpr size_t ESPNOW_TEST_DEVICE_TOKEN_MAX_LEN = 56;
constexpr uint32_t ESPNOW_HEALTH_FLAG_WIFI_READY = 1u << 0;
constexpr uint32_t ESPNOW_HEALTH_FLAG_NODE_REGISTERED = 1u << 1;
constexpr uint32_t ESPNOW_HEALTH_FLAG_CONFIG_READY = 1u << 2;

enum class EspNowMessageKind : uint8_t {
  kCommand = 1,
  kAck = 2,
  kHealthReport = 3,
};

enum class EspNowCommandType : uint8_t {
  kCaptureImage = 1,
  kProvisionStart = 2,
  kHealthCheck = 3,
  kPauseCapture = 4,
  kUpdateCaptureInterval = 5,
};

enum class EspNowAckStatus : uint8_t {
  kOk = 0,
  kUnsupported = 1,
  kBusy = 2,
  kFailed = 3,
  kInvalid = 4,
};

enum class MasterProvisioningState : uint8_t {
  kIdle = 0,
  kAwaitingSend = 1,
  kAwaitingAck = 2,
  kSucceeded = 3,
  kTimedOut = 4,
  kFailed = 5,
};

struct __attribute__((packed)) CameraProvisioningPayload {
  uint16_t config_version;
  uint16_t camera_node_index;
  uint32_t platform_device_id;
  char wifi_ssid[ESPNOW_TEST_WIFI_SSID_MAX_LEN + 1];
  char wifi_password[ESPNOW_TEST_WIFI_PASSWORD_MAX_LEN + 1];
  char platform_url[ESPNOW_TEST_PLATFORM_URL_MAX_LEN + 1];
  char device_token[ESPNOW_TEST_DEVICE_TOKEN_MAX_LEN + 1];
};

// Single fixed-size packet for all test messages.
// Field usage depends on message kind:
// - COMMAND: command + request_id are required.
// - ACK: command + request_id + ack_status.
// - HEALTH_REPORT: request_id (correlates to health command), health fields.
struct __attribute__((packed)) EspNowPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t kind;
  uint8_t command;
  uint8_t ack_status;
  uint32_t request_id;
  uint32_t timestamp_ms;
  uint32_t value_u32_1;
  uint32_t value_u32_2;
  uint8_t payload[sizeof(CameraProvisioningPayload)];
};

static_assert(sizeof(EspNowPacket) <= ESPNOW_TEST_MAX_PACKET_BYTES, "ESP-NOW packet must fit in one frame");

struct MasterProvisioningSession {
  bool active = false;
  bool send_pending = false;
  uint8_t target_mac[6] = {0, 0, 0, 0, 0, 0};
  uint32_t request_id = 0;
  uint32_t last_send_ms = 0;
  uint32_t ack_timeout_ms = 1500;
  uint8_t attempts_started = 0;
  uint8_t max_attempts = 3;
  EspNowAckStatus final_ack_status = EspNowAckStatus::kOk;
  MasterProvisioningState state = MasterProvisioningState::kIdle;
  CameraProvisioningPayload payload{};
};

inline bool espnow_copy_bounded_string(char* destination, size_t destination_size, const char* source) {
  if (destination == nullptr || destination_size == 0 || source == nullptr) {
    return false;
  }
  const size_t source_length = strlen(source);
  if (source_length >= destination_size) {
    return false;
  }
  memset(destination, 0, destination_size);
  memcpy(destination, source, source_length);
  destination[source_length] = '\0';
  return true;
}

inline bool espnow_build_provisioning_payload(
    CameraProvisioningPayload* payload,
    uint16_t config_version,
    uint16_t camera_node_index,
    uint32_t platform_device_id,
    const char* wifi_ssid,
    const char* wifi_password,
    const char* platform_url,
    const char* device_token) {
  if (payload == nullptr) {
    return false;
  }
  memset(payload, 0, sizeof(*payload));
  payload->config_version = config_version;
  payload->camera_node_index = camera_node_index;
  payload->platform_device_id = platform_device_id;

  return espnow_copy_bounded_string(payload->wifi_ssid, sizeof(payload->wifi_ssid), wifi_ssid) &&
         espnow_copy_bounded_string(
             payload->wifi_password, sizeof(payload->wifi_password), wifi_password != nullptr ? wifi_password : "") &&
         espnow_copy_bounded_string(payload->platform_url, sizeof(payload->platform_url), platform_url) &&
         espnow_copy_bounded_string(payload->device_token, sizeof(payload->device_token), device_token);
}

inline bool espnow_validate_provisioning_payload(const CameraProvisioningPayload& payload) {
  return payload.config_version > 0 && payload.camera_node_index > 0 && payload.platform_device_id > 0 &&
         payload.wifi_ssid[0] != '\0' && payload.platform_url[0] != '\0' && payload.device_token[0] != '\0';
}

inline void espnow_packet_set_provisioning_payload(
    EspNowPacket* packet,
    const CameraProvisioningPayload& payload) {
  if (packet == nullptr) {
    return;
  }
  memset(packet->payload, 0, sizeof(packet->payload));
  memcpy(packet->payload, &payload, sizeof(payload));
}

inline CameraProvisioningPayload espnow_packet_get_provisioning_payload(const EspNowPacket& packet) {
  CameraProvisioningPayload payload{};
  memcpy(&payload, packet.payload, sizeof(payload));
  return payload;
}

inline void espnow_start_provisioning_session(
    MasterProvisioningSession* session,
    const uint8_t* target_mac,
    uint32_t request_id,
    const CameraProvisioningPayload& payload,
    uint32_t now_ms,
    uint32_t ack_timeout_ms,
    uint8_t max_attempts) {
  if (session == nullptr || target_mac == nullptr) {
    return;
  }
  memset(session, 0, sizeof(*session));
  memcpy(session->target_mac, target_mac, 6);
  session->active = true;
  session->send_pending = true;
  session->request_id = request_id;
  session->last_send_ms = now_ms;
  session->ack_timeout_ms = ack_timeout_ms;
  session->max_attempts = max_attempts;
  session->payload = payload;
  session->state = MasterProvisioningState::kAwaitingSend;
}

inline bool espnow_should_send_provisioning_packet(const MasterProvisioningSession& session) {
  return session.active && session.send_pending && session.state == MasterProvisioningState::kAwaitingSend;
}

inline void espnow_build_provisioning_packet(
    const MasterProvisioningSession& session,
    uint32_t now_ms,
    EspNowPacket* packet) {
  if (packet == nullptr) {
    return;
  }
  memset(packet, 0, sizeof(*packet));
  packet->magic = ESPNOW_TEST_MAGIC;
  packet->version = ESPNOW_TEST_VERSION;
  packet->kind = static_cast<uint8_t>(EspNowMessageKind::kCommand);
  packet->command = static_cast<uint8_t>(EspNowCommandType::kProvisionStart);
  packet->ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  packet->request_id = session.request_id;
  packet->timestamp_ms = now_ms;
  packet->value_u32_1 = session.payload.config_version;
  packet->value_u32_2 = session.payload.camera_node_index;
  espnow_packet_set_provisioning_payload(packet, session.payload);
}

inline void espnow_mark_provisioning_packet_sent(MasterProvisioningSession* session, uint32_t now_ms) {
  if (session == nullptr) {
    return;
  }
  session->send_pending = false;
  session->last_send_ms = now_ms;
  session->attempts_started = static_cast<uint8_t>(session->attempts_started + 1);
  session->state = MasterProvisioningState::kAwaitingAck;
}

inline bool espnow_target_matches(const uint8_t* target_mac, const uint8_t* received_mac) {
  if (target_mac == nullptr || received_mac == nullptr) {
    return false;
  }
  static const uint8_t kBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  return memcmp(target_mac, received_mac, 6) == 0 || memcmp(target_mac, kBroadcastMac, 6) == 0;
}

inline bool espnow_handle_provisioning_ack(
    MasterProvisioningSession* session,
    const uint8_t* source_mac,
    const EspNowPacket& packet) {
  if (session == nullptr || !session->active || session->state != MasterProvisioningState::kAwaitingAck) {
    return false;
  }
  if (static_cast<EspNowMessageKind>(packet.kind) != EspNowMessageKind::kAck ||
      static_cast<EspNowCommandType>(packet.command) != EspNowCommandType::kProvisionStart ||
      packet.request_id != session->request_id || !espnow_target_matches(session->target_mac, source_mac)) {
    return false;
  }

  session->final_ack_status = static_cast<EspNowAckStatus>(packet.ack_status);
  session->active = false;
  session->send_pending = false;
  session->state = session->final_ack_status == EspNowAckStatus::kOk
                       ? MasterProvisioningState::kSucceeded
                       : MasterProvisioningState::kFailed;
  return true;
}

inline void espnow_update_provisioning_session(MasterProvisioningSession* session, uint32_t now_ms) {
  if (session == nullptr || !session->active || session->state != MasterProvisioningState::kAwaitingAck) {
    return;
  }
  if (now_ms - session->last_send_ms < session->ack_timeout_ms) {
    return;
  }
  if (session->attempts_started < session->max_attempts) {
    session->send_pending = true;
    session->state = MasterProvisioningState::kAwaitingSend;
    return;
  }
  session->active = false;
  session->send_pending = false;
  session->final_ack_status = EspNowAckStatus::kFailed;
  session->state = MasterProvisioningState::kTimedOut;
}
