#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "camera/xiao_camera.h"
#include "config.h"
#include "espnow_test_protocol.h"
#include "platform/platform_client.h"

extern "C" {
#include "esp_bt.h"
}

namespace {
XiaoCamera g_camera;
PlatformClient g_platform_client(
    PLANTLAB_PLATFORM_URL,
    PLANTLAB_DEVICE_ID,
    PLANTLAB_DEVICE_TOKEN);

constexpr uint32_t kWifiReconnectRetryMs = 5000UL;
constexpr uint32_t kHeartbeatHttpTimeoutMs = 8000UL;

unsigned long g_last_wifi_attempt_ms = 0;
unsigned long g_last_heartbeat_ms = 0;
unsigned long g_wifi_connect_started_at_ms = 0;
bool g_wifi_connecting = false;
bool g_wifi_ready = false;
bool g_wifi_power_save_configured = false;
bool g_camera_initialized = false;
bool g_capture_in_progress = false;

volatile bool g_capture_requested = false;
volatile bool g_capture_request_has_sender = false;
volatile uint32_t g_capture_request_id = 0;
uint8_t g_capture_request_mac[6] = {0};
}

bool platform_enabled() {
  return g_platform_client.configured() && String(PLANTLAB_WIFI_SSID).length() > 0;
}

String macToString(const uint8_t* mac) {
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

const char* commandToString(EspNowCommandType command) {
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

bool ensurePeer(const uint8_t* peer_mac) {
  if (peer_mac == nullptr) {
    return false;
  }
  if (esp_now_is_peer_exist(peer_mac)) {
    return true;
  }

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, peer_mac, 6);
  peer.channel = 0;  // use current STA channel
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.printf("[camera-node] failed to add ESP-NOW peer %s\n", macToString(peer_mac).c_str());
    return false;
  }
  return true;
}

void sendAck(
    const uint8_t* target_mac,
    EspNowCommandType command,
    uint32_t request_id,
    EspNowAckStatus status,
    uint32_t value_u32_1 = 0,
    uint32_t value_u32_2 = 0) {
  if (!ensurePeer(target_mac)) {
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
        "[camera-node] ESP-NOW ack request=%u command=%s status=%u -> %s\n",
        static_cast<unsigned int>(request_id),
        commandToString(command),
        static_cast<unsigned int>(status),
        macToString(target_mac).c_str());
  } else {
    Serial.printf("[camera-node] ESP-NOW ack send failed err=%d\n", static_cast<int>(err));
  }
}

void disableBluetooth() {
  const bool stopped = btStop();
  Serial.printf("[camera-node] bluetooth %s\n", stopped ? "disabled" : "already disabled");
}

void enterIdlePowerMode() {
  setCpuFrequencyMhz(PLANTLAB_CAMERA_IDLE_CPU_MHZ);
}

void enterActiveCaptureMode() {
  setCpuFrequencyMhz(PLANTLAB_CAMERA_ACTIVE_CPU_MHZ);
}

void enableLowPowerWiFi() {
  if (g_wifi_power_save_configured || !g_wifi_ready) {
    return;
  }

  esp_err_t ps_err = esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
  esp_err_t tx_err = esp_wifi_set_max_tx_power(PLANTLAB_WIFI_MAX_TX_POWER);
  if (ps_err == ESP_OK && tx_err == ESP_OK) {
    g_wifi_power_save_configured = true;
    Serial.printf(
        "[camera-node] Wi-Fi power save enabled mode=min_modem tx_power=%d\n",
        static_cast<int>(PLANTLAB_WIFI_MAX_TX_POWER));
  } else {
    Serial.printf(
        "[camera-node] Wi-Fi power tuning failed ps_err=%d tx_err=%d\n",
        static_cast<int>(ps_err),
        static_cast<int>(tx_err));
  }
}

void setupWiFi() {
  if (!platform_enabled()) {
    Serial.println("[camera-node] Wi-Fi disabled (missing credentials or platform config)");
    return;
  }

  Serial.printf("[camera-node] connecting to %s\n", PLANTLAB_WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);
  WiFi.begin(PLANTLAB_WIFI_SSID, PLANTLAB_WIFI_PASSWORD);
  g_last_wifi_attempt_ms = millis();
  g_wifi_connect_started_at_ms = millis();
  g_wifi_connecting = true;
}

void maintainWiFiConnection() {
  if (!platform_enabled()) {
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!g_wifi_ready) {
      g_wifi_ready = true;
      g_wifi_connecting = false;
      g_wifi_power_save_configured = false;
      Serial.printf("[camera-node] Wi-Fi connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    enableLowPowerWiFi();
    return;
  }

  g_wifi_ready = false;
  g_wifi_power_save_configured = false;

  const unsigned long now = millis();
  if (g_wifi_connecting && now - g_wifi_connect_started_at_ms >= PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    g_wifi_connecting = false;
    Serial.println("[camera-node] Wi-Fi connect timed out");
  }

  if (!g_wifi_connecting && now - g_last_wifi_attempt_ms >= kWifiReconnectRetryMs) {
    Serial.printf("[camera-node] retrying Wi-Fi for %s\n", PLANTLAB_WIFI_SSID);
    WiFi.begin(PLANTLAB_WIFI_SSID, PLANTLAB_WIFI_PASSWORD);
    g_last_wifi_attempt_ms = now;
    g_wifi_connect_started_at_ms = now;
    g_wifi_connecting = true;
  }
}

bool sendHeartbeat() {
  if (!platform_enabled() || !g_wifi_ready) {
    return false;
  }

  HTTPClient http;
  http.setTimeout(kHeartbeatHttpTimeoutMs);
  const String url = g_platform_client.base_url() + "/health";
  if (!http.begin(url)) {
    Serial.println("[camera-node] heartbeat failed: request setup failed");
    return false;
  }

  const int code = http.GET();
  const String body = code > 0 ? http.getString() : http.errorToString(code);
  http.end();

  if (code >= 200 && code < 300) {
    Serial.printf("[camera-node] heartbeat sent to %s (%d)\n", url.c_str(), code);
    return true;
  }

  Serial.printf("[camera-node] heartbeat failed HTTP %d: %s\n", code, body.c_str());
  return false;
}

bool initCamera() {
  if (g_camera_initialized) {
    return true;
  }

  if (!g_camera.begin()) {
    Serial.println("[camera-node] camera init failed");
    return false;
  }

  g_camera_initialized = true;
  Serial.println("[camera-node] camera init succeeded");
  return true;
}

void deinitCamera() {
  if (!g_camera_initialized) {
    return;
  }

  const esp_err_t err = esp_camera_deinit();
  if (err == ESP_OK) {
    Serial.println("[camera-node] camera deinitialized");
  } else {
    Serial.printf("[camera-node] camera deinit returned err=%d\n", static_cast<int>(err));
  }
  g_camera_initialized = false;
}

bool captureAndUploadImage() {
  if (!platform_enabled() || !g_wifi_ready) {
    Serial.println("[camera-node] upload skipped: Wi-Fi not ready");
    return false;
  }

  if (!initCamera()) {
    return false;
  }

  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    Serial.println("[camera-node] image capture failed");
    deinitCamera();
    return false;
  }

  Serial.printf(
      "[camera-node] image captured %ux%u %u bytes\n",
      static_cast<unsigned int>(frame->width),
      static_cast<unsigned int>(frame->height),
      static_cast<unsigned int>(frame->len));

  String error;
  const bool uploaded = g_platform_client.upload_jpeg(
      frame->buf,
      frame->len,
      "esp32-camera.jpg",
      &error);
  esp_camera_fb_return(frame);

  if (uploaded) {
    Serial.println("[camera-node] image upload succeeded");
  } else {
    Serial.printf("[camera-node] image upload failed: %s\n", error.c_str());
  }

  deinitCamera();
  return uploaded;
}

void onEspNowReceive(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    Serial.printf("[camera-node] ESP-NOW ignored packet length=%d\n", len);
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    Serial.println("[camera-node] ESP-NOW ignored invalid packet");
    return;
  }

  const EspNowMessageKind kind = static_cast<EspNowMessageKind>(packet.kind);
  if (kind != EspNowMessageKind::kCommand) {
    return;
  }

  const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);
  Serial.printf(
      "[camera-node] ESP-NOW command received request=%u command=%s from %s\n",
      static_cast<unsigned int>(packet.request_id),
      commandToString(command),
      macToString(mac_addr).c_str());

  if (command != EspNowCommandType::kCaptureImage) {
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kUnsupported);
    return;
  }

  if (g_capture_requested || g_capture_in_progress) {
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kBusy);
    return;
  }

  memcpy(g_capture_request_mac, mac_addr, sizeof(g_capture_request_mac));
  g_capture_request_id = packet.request_id;
  g_capture_request_has_sender = true;
  g_capture_requested = true;
}

bool setupEspNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("[camera-node] ESP-NOW init failed");
    return false;
  }
  esp_now_register_recv_cb(onEspNowReceive);
  Serial.println("[camera-node] ESP-NOW ready in STA mode");
  return true;
}

void handleCaptureRequest() {
  if (!g_capture_requested || g_capture_in_progress) {
    return;
  }

  g_capture_requested = false;
  g_capture_in_progress = true;
  enterActiveCaptureMode();

  const bool success = captureAndUploadImage();

  if (g_capture_request_has_sender) {
    sendAck(
        g_capture_request_mac,
        EspNowCommandType::kCaptureImage,
        g_capture_request_id,
        success ? EspNowAckStatus::kOk : EspNowAckStatus::kFailed);
  }
  g_capture_request_has_sender = false;

  enterIdlePowerMode();
  g_capture_in_progress = false;
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println();
  Serial.println("=== PlantLab ESP32 Camera Platform Test ===");
  Serial.printf("[camera-node] base_url: %s\n", g_platform_client.base_url().c_str());
  Serial.printf("[camera-node] device_id: %d\n", g_platform_client.device_id());

  disableBluetooth();
  enterIdlePowerMode();
  setupWiFi();
  setupEspNow();
  deinitCamera();
}

void loop() {
  maintainWiFiConnection();

  const unsigned long now = millis();
  if (platform_enabled() && g_wifi_ready && now - g_last_heartbeat_ms >= PLANTLAB_CAMERA_HEARTBEAT_INTERVAL_MS) {
    g_last_heartbeat_ms = now;
    sendHeartbeat();
  }

  handleCaptureRequest();
  delay(2);
}
