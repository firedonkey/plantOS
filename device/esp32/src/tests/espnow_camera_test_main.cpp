#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "camera/xiao_camera.h"
#include "config.h"
#include "espnow_test_protocol.h"

namespace {
uint32_t g_capture_counter = 0;
XiaoCamera g_camera;
bool g_camera_ready = false;
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

bool ensure_peer(const uint8_t* peer_mac) {
  if (esp_now_is_peer_exist(peer_mac)) {
    return true;
  }

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, peer_mac, 6);
  peer.channel = ESPNOW_TEST_WIFI_CHANNEL;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.printf("[espnow-camera] failed to add peer %s\n", mac_to_string(peer_mac).c_str());
    return false;
  }
  return true;
}

void send_ack(
    const uint8_t* target_mac,
    EspNowCommandType command,
    uint32_t request_id,
    EspNowAckStatus status,
    uint32_t value_u32_1 = 0,
    uint32_t value_u32_2 = 0) {
  if (!ensure_peer(target_mac)) {
    return;
  }

  EspNowPacket packet{};
  packet.magic = ESPNOW_TEST_MAGIC;
  packet.version = ESPNOW_TEST_VERSION;
  packet.kind = static_cast<uint8_t>(EspNowMessageKind::kAck);
  packet.command = static_cast<uint8_t>(command);
  packet.ack_status = static_cast<uint8_t>(status);
  packet.request_id = request_id;
  packet.timestamp_ms = millis();
  packet.value_u32_1 = value_u32_1;
  packet.value_u32_2 = value_u32_2;

  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));

  if (err == ESP_OK) {
    Serial.printf(
      "[espnow-camera] ACK request=%u command=%s status=%u -> %s\n",
      static_cast<unsigned int>(request_id),
      command_to_string(command),
        static_cast<unsigned int>(status),
        mac_to_string(target_mac).c_str());
  } else {
    Serial.printf("[espnow-camera] ACK send failed err=%d\n", static_cast<int>(err));
  }
}

void send_health_report(const uint8_t* target_mac, uint32_t request_id) {
  if (!ensure_peer(target_mac)) {
    return;
  }

  EspNowPacket packet{};
  packet.magic = ESPNOW_TEST_MAGIC;
  packet.version = ESPNOW_TEST_VERSION;
  packet.kind = static_cast<uint8_t>(EspNowMessageKind::kHealthReport);
  packet.command = static_cast<uint8_t>(EspNowCommandType::kHealthCheck);
  packet.ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  packet.request_id = request_id;
  packet.timestamp_ms = millis();
  packet.value_u32_1 = millis();       // uptime ms
  packet.value_u32_2 = ESP.getFreeHeap();

  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err == ESP_OK) {
    Serial.printf(
        "[espnow-camera] HEALTH request=%u uptime_ms=%u free_heap=%u -> %s\n",
        static_cast<unsigned int>(request_id),
        static_cast<unsigned int>(packet.value_u32_1),
        static_cast<unsigned int>(packet.value_u32_2),
        mac_to_string(target_mac).c_str());
  } else {
    Serial.printf("[espnow-camera] HEALTH send failed err=%d\n", static_cast<int>(err));
  }
}

void on_data_sent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  (void)mac_addr;
  (void)status;
}

void on_data_received(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    Serial.printf("[espnow-camera] received unexpected length=%d\n", len);
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    Serial.println("[espnow-camera] ignored invalid packet");
    return;
  }

  const EspNowMessageKind kind = static_cast<EspNowMessageKind>(packet.kind);
  if (kind != EspNowMessageKind::kCommand) {
    Serial.printf("[espnow-camera] ignored non-command kind=%u\n", static_cast<unsigned int>(packet.kind));
    return;
  }

  const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);
  Serial.printf(
      "[espnow-camera] COMMAND request=%u command=%s from %s\n",
      static_cast<unsigned int>(packet.request_id),
      command_to_string(command),
      mac_to_string(mac_addr).c_str());

  switch (command) {
    case EspNowCommandType::kCaptureImage:
      if (!g_camera_ready) {
        Serial.println("[espnow-camera] capture failed: camera not ready");
        send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kFailed);
        break;
      }

      {
        const CameraFrameInfo frame = g_camera.capture_once();
        if (!frame.valid) {
          Serial.println("[espnow-camera] capture failed: frame invalid");
          send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kFailed);
          break;
        }

        ++g_capture_counter;
        Serial.printf(
            "[espnow-camera] captured image count=%u %ux%u %u bytes\n",
            static_cast<unsigned int>(g_capture_counter),
            static_cast<unsigned int>(frame.width),
            static_cast<unsigned int>(frame.height),
            static_cast<unsigned int>(frame.length_bytes));

        send_ack(
            mac_addr,
            command,
            packet.request_id,
            EspNowAckStatus::kOk,
            static_cast<uint32_t>(frame.length_bytes),
            g_capture_counter);
      }
      break;
    case EspNowCommandType::kProvisionStart:
      {
        const CameraProvisioningPayload payload = espnow_packet_get_provisioning_payload(packet);
        if (!espnow_validate_provisioning_payload(payload)) {
          Serial.println("[espnow-camera] provisioning payload invalid");
          send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kInvalid);
          break;
        }
        Serial.printf(
            "[espnow-camera] provisioning payload config_version=%u camera_index=%u platform_device_id=%u ssid=%s platform=%s token_len=%u\n",
            static_cast<unsigned int>(payload.config_version),
            static_cast<unsigned int>(payload.camera_node_index),
            static_cast<unsigned int>(payload.platform_device_id),
            payload.wifi_ssid,
            payload.platform_url,
            static_cast<unsigned int>(strlen(payload.device_token)));
        // Stage 10: ACK payload receipt only. Stage 11 will persist and apply it.
        send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
      }
      break;
    case EspNowCommandType::kHealthCheck:
      send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
      send_health_report(mac_addr, packet.request_id);
      break;
    default:
      send_ack(mac_addr, command, packet.request_id, EspNowAckStatus::kUnsupported);
      break;
  }
}

bool init_espnow() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(ESPNOW_TEST_WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("[espnow-camera] esp_now_init failed");
    return false;
  }

  esp_now_register_send_cb(on_data_sent);
  esp_now_register_recv_cb(on_data_received);
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.mode(WIFI_STA);

  Serial.println();
  Serial.println("=== PlantLab ESP-NOW Camera Command Test ===");
  Serial.printf("[espnow-camera] local MAC: %s\n", WiFi.macAddress().c_str());
  Serial.printf("[espnow-camera] channel: %u\n", static_cast<unsigned int>(ESPNOW_TEST_WIFI_CHANNEL));

  g_camera_ready = g_camera.begin();
  if (g_camera_ready) {
    Serial.println("[espnow-camera] camera initialized");
  } else {
    Serial.println("[espnow-camera] camera init failed");
  }

  if (!init_espnow()) {
    Serial.println("[espnow-camera] init failed");
    return;
  }
  Serial.println("[espnow-camera] ready and waiting for commands");
}

void loop() {}
