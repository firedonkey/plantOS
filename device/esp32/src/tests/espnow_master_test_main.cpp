#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "config.h"
#include "espnow_test_protocol.h"

namespace {
uint32_t g_next_request_id = 1;

uint8_t kBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
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

void handle_serial_commands() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == 'c' || ch == 'C') {
      send_command(EspNowCommandType::kCaptureImage);
    } else if (ch == 'p' || ch == 'P') {
      send_command(EspNowCommandType::kProvisionStart);
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

  if (!init_espnow()) {
    Serial.println("[espnow-master] init failed");
    return;
  }

  Serial.println("[espnow-master] ready");
}

void loop() {
  handle_serial_commands();
}
