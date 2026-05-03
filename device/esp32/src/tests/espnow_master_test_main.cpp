#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "config.h"
#include "espnow_test_protocol.h"

namespace {
uint32_t g_next_request_id = 1;

uint8_t kBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
MasterProvisioningSession g_provisioning_session;
}

String mac_to_string(const uint8_t* mac) {
  char buffer[18];
  snprintf(
      buffer,
      sizeof(buffer),
      "%02X:%02X:%02X:%02X:%02X:%02X",
      mac[0],
      mac[1],
      mac[2],
      mac[3],
      mac[4],
      mac[5]);
  return String(buffer);
}

const char* command_to_string(EspNowCommandType command) {
  switch (command) {
    case EspNowCommandType::kCaptureImage:
      return "capture_image";
    case EspNowCommandType::kProvisionStart:
      return "provision_start";
    case EspNowCommandType::kHealthCheck:
      return "health_check";
    default:
      return "unknown";
  }
}

const char* ack_to_string(EspNowAckStatus status) {
  switch (status) {
    case EspNowAckStatus::kOk:
      return "ok";
    case EspNowAckStatus::kUnsupported:
      return "unsupported";
    case EspNowAckStatus::kBusy:
      return "busy";
    case EspNowAckStatus::kFailed:
      return "failed";
    case EspNowAckStatus::kInvalid:
      return "invalid";
    default:
      return "unknown";
  }
}

const char* provisioning_state_to_string(MasterProvisioningState state) {
  switch (state) {
    case MasterProvisioningState::kIdle:
      return "idle";
    case MasterProvisioningState::kAwaitingSend:
      return "awaiting_send";
    case MasterProvisioningState::kAwaitingAck:
      return "awaiting_ack";
    case MasterProvisioningState::kSucceeded:
      return "succeeded";
    case MasterProvisioningState::kTimedOut:
      return "timed_out";
    case MasterProvisioningState::kFailed:
      return "failed";
    default:
      return "unknown";
  }
}

void on_data_sent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  (void)mac_addr;
  (void)status;
}

void on_data_received(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    Serial.printf("[espnow-master] received unexpected length=%d\n", len);
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    Serial.println("[espnow-master] ignored invalid packet");
    return;
  }

  const EspNowMessageKind kind = static_cast<EspNowMessageKind>(packet.kind);
  if (kind == EspNowMessageKind::kAck) {
    if (espnow_handle_provisioning_ack(&g_provisioning_session, mac_addr, packet)) {
      Serial.printf(
          "[espnow-master] provisioning ACK request=%u status=%s from %s\n",
          static_cast<unsigned int>(packet.request_id),
          ack_to_string(static_cast<EspNowAckStatus>(packet.ack_status)),
          mac_to_string(mac_addr).c_str());
      return;
    }
    const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);
    const EspNowAckStatus status = static_cast<EspNowAckStatus>(packet.ack_status);
    if (command == EspNowCommandType::kCaptureImage) {
      Serial.printf(
          "[espnow-master] ACK request=%u command=%s status=%s bytes=%u capture_count=%u from %s\n",
          static_cast<unsigned int>(packet.request_id),
          command_to_string(command),
          ack_to_string(status),
          static_cast<unsigned int>(packet.value_u32_1),
          static_cast<unsigned int>(packet.value_u32_2),
          mac_to_string(mac_addr).c_str());
    } else {
      Serial.printf(
          "[espnow-master] ACK request=%u command=%s status=%s from %s\n",
          static_cast<unsigned int>(packet.request_id),
          command_to_string(command),
          ack_to_string(status),
          mac_to_string(mac_addr).c_str());
    }
    return;
  }

  if (kind == EspNowMessageKind::kHealthReport) {
    Serial.printf(
        "[espnow-master] HEALTH request=%u uptime_ms=%u free_heap=%u from %s\n",
        static_cast<unsigned int>(packet.request_id),
        static_cast<unsigned int>(packet.value_u32_1),
        static_cast<unsigned int>(packet.value_u32_2),
        mac_to_string(mac_addr).c_str());
    return;
  }

  Serial.printf(
      "[espnow-master] received unknown kind=%u from %s\n",
      static_cast<unsigned int>(packet.kind),
      mac_to_string(mac_addr).c_str());
}

bool init_espnow() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(ESPNOW_TEST_WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("[espnow-master] esp_now_init failed");
    return false;
  }

  esp_now_register_send_cb(on_data_sent);
  esp_now_register_recv_cb(on_data_received);

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, kBroadcastMac, 6);
  peer.channel = ESPNOW_TEST_WIFI_CHANNEL;
  peer.encrypt = false;
  if (!esp_now_is_peer_exist(kBroadcastMac)) {
    if (esp_now_add_peer(&peer) != ESP_OK) {
      Serial.println("[espnow-master] failed to add broadcast peer");
      return false;
    }
  }
  return true;
}

void send_command(EspNowCommandType command, uint32_t extra_1 = 0, uint32_t extra_2 = 0) {
  EspNowPacket packet{};
  packet.magic = ESPNOW_TEST_MAGIC;
  packet.version = ESPNOW_TEST_VERSION;
  packet.kind = static_cast<uint8_t>(EspNowMessageKind::kCommand);
  packet.command = static_cast<uint8_t>(command);
  packet.ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  packet.request_id = g_next_request_id++;
  packet.timestamp_ms = millis();
  packet.value_u32_1 = extra_1;
  packet.value_u32_2 = extra_2;

  const esp_err_t err = esp_now_send(
      kBroadcastMac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    Serial.printf("[espnow-master] send failed err=%d\n", static_cast<int>(err));
  }
}

bool build_default_provisioning_payload(CameraProvisioningPayload* payload) {
  return espnow_build_provisioning_payload(
      payload,
      ESPNOW_PROVISION_CONFIG_VERSION,
      ESPNOW_PROVISION_CAMERA_NODE_INDEX,
      ESPNOW_PROVISION_PLATFORM_DEVICE_ID,
      PLANTLAB_WIFI_SSID,
      PLANTLAB_WIFI_PASSWORD,
      PLANTLAB_PLATFORM_URL,
      ESPNOW_PROVISION_DEVICE_TOKEN);
}

void start_provisioning_request() {
  if (g_provisioning_session.active) {
    Serial.printf(
        "[espnow-master] provisioning already in progress request=%u state=%s attempts=%u\n",
        static_cast<unsigned int>(g_provisioning_session.request_id),
        provisioning_state_to_string(g_provisioning_session.state),
        static_cast<unsigned int>(g_provisioning_session.attempts_started));
    return;
  }

  CameraProvisioningPayload payload{};
  if (!build_default_provisioning_payload(&payload)) {
    Serial.println("[espnow-master] provisioning payload invalid or too large for the configured fields");
    return;
  }

  const uint32_t request_id = g_next_request_id++;
  espnow_start_provisioning_session(
      &g_provisioning_session,
      kBroadcastMac,
      request_id,
      payload,
      millis(),
      ESPNOW_PROVISION_ACK_TIMEOUT_MS,
      ESPNOW_PROVISION_MAX_RETRIES);
  Serial.printf(
      "[espnow-master] provisioning request=%u prepared camera_index=%u platform_device_id=%u\n",
      static_cast<unsigned int>(request_id),
      static_cast<unsigned int>(payload.camera_node_index),
      static_cast<unsigned int>(payload.platform_device_id));
}

void process_provisioning_session() {
  const unsigned long now = millis();
  espnow_update_provisioning_session(&g_provisioning_session, now);
  if (espnow_should_send_provisioning_packet(g_provisioning_session)) {
    EspNowPacket packet{};
    espnow_build_provisioning_packet(g_provisioning_session, now, &packet);
    const esp_err_t err = esp_now_send(
        g_provisioning_session.target_mac,
        reinterpret_cast<const uint8_t*>(&packet),
        sizeof(packet));
    if (err != ESP_OK) {
      Serial.printf("[espnow-master] provisioning send failed err=%d\n", static_cast<int>(err));
      g_provisioning_session.active = false;
      g_provisioning_session.send_pending = false;
      g_provisioning_session.final_ack_status = EspNowAckStatus::kFailed;
      g_provisioning_session.state = MasterProvisioningState::kFailed;
      return;
    }
    espnow_mark_provisioning_packet_sent(&g_provisioning_session, now);
    Serial.printf(
        "[espnow-master] provisioning send request=%u attempt=%u state=%s\n",
        static_cast<unsigned int>(g_provisioning_session.request_id),
        static_cast<unsigned int>(g_provisioning_session.attempts_started),
        provisioning_state_to_string(g_provisioning_session.state));
  }

  static MasterProvisioningState last_reported_state = MasterProvisioningState::kIdle;
  if (g_provisioning_session.state != last_reported_state &&
      (g_provisioning_session.state == MasterProvisioningState::kSucceeded ||
       g_provisioning_session.state == MasterProvisioningState::kTimedOut ||
       g_provisioning_session.state == MasterProvisioningState::kFailed)) {
    Serial.printf(
        "[espnow-master] provisioning finished state=%s attempts=%u final_status=%s\n",
        provisioning_state_to_string(g_provisioning_session.state),
        static_cast<unsigned int>(g_provisioning_session.attempts_started),
        ack_to_string(g_provisioning_session.final_ack_status));
  }
  last_reported_state = g_provisioning_session.state;
}

void handle_serial_commands() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == 'c' || ch == 'C') {
      send_command(EspNowCommandType::kCaptureImage);
    } else if (ch == 'p' || ch == 'P') {
      start_provisioning_request();
    } else if (ch == 'h' || ch == 'H') {
      send_command(EspNowCommandType::kHealthCheck);
    } else if (ch == '?') {
      Serial.println("[espnow-master] keys: c=capture, p=provision_start, h=health_check");
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.mode(WIFI_STA);

  Serial.println();
  Serial.println("=== PlantLab ESP-NOW Master Command Test ===");
  Serial.printf("[espnow-master] local MAC: %s\n", WiFi.macAddress().c_str());
  Serial.printf("[espnow-master] channel: %u\n", static_cast<unsigned int>(ESPNOW_TEST_WIFI_CHANNEL));
  Serial.println("[espnow-master] keys: c=capture, p=provision_start, h=health_check");
  Serial.printf(
      "[espnow-master] default provision config_version=%u camera_index=%u platform_device_id=%u\n",
      static_cast<unsigned int>(ESPNOW_PROVISION_CONFIG_VERSION),
      static_cast<unsigned int>(ESPNOW_PROVISION_CAMERA_NODE_INDEX),
      static_cast<unsigned int>(ESPNOW_PROVISION_PLATFORM_DEVICE_ID));

  if (!init_espnow()) {
    Serial.println("[espnow-master] init failed");
    return;
  }

  Serial.println("[espnow-master] ready");
}

void loop() {
  handle_serial_commands();
  process_provisioning_session();
}
