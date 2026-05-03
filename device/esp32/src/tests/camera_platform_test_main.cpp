#include <Arduino.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include <memory>

#include "camera_node_runtime_config.h"
#include "camera/xiao_camera.h"
#include "config.h"
#include "espnow_test_protocol.h"
#include "platform/platform_client.h"

extern "C" {
#include "esp_bt.h"
}

namespace {
constexpr char kPreferencesNamespace[] = "plcam";
constexpr char kConfigKeyProvisioned[] = "prov";
constexpr char kConfigKeyVersion[] = "ver";
constexpr char kConfigKeyCameraIndex[] = "cam_idx";
constexpr char kConfigKeyPlatformId[] = "plat_id";
constexpr char kConfigKeySsid[] = "wifi_ssid";
constexpr char kConfigKeyPassword[] = "wifi_pass";
constexpr char kConfigKeyPlatformUrl[] = "plat_url";
constexpr char kConfigKeyDeviceToken[] = "dev_token";
constexpr char kNodeRoleCamera[] = "camera";
constexpr char kCameraSoftwareVersion[] = "0.1.0";
XiaoCamera g_camera;
Preferences g_preferences;
std::unique_ptr<PlatformClient> g_platform_client;
CameraNodeRuntimeConfig g_runtime_config{};
String g_hardware_device_id;

constexpr uint32_t kWifiReconnectRetryMs = 5000UL;
constexpr uint32_t kHeartbeatHttpTimeoutMs = 8000UL;
constexpr uint32_t kNodeRegisterRetryMs = 5000UL;

unsigned long g_last_wifi_attempt_ms = 0;
unsigned long g_last_heartbeat_ms = 0;
unsigned long g_last_node_register_attempt_ms = 0;
unsigned long g_wifi_connect_started_at_ms = 0;
bool g_wifi_connecting = false;
bool g_wifi_ready = false;
bool g_wifi_power_save_configured = false;
bool g_camera_initialized = false;
bool g_capture_in_progress = false;
bool g_node_registered = false;
bool g_restart_scheduled = false;
unsigned long g_restart_at_ms = 0;

volatile bool g_capture_requested = false;
volatile bool g_capture_request_has_sender = false;
volatile uint32_t g_capture_request_id = 0;
uint8_t g_capture_request_mac[6] = {0};
}

String stableHardwareDeviceId() {
  if (g_hardware_device_id.length() > 0) {
    return g_hardware_device_id;
  }
  const uint64_t chip_id = ESP.getEfuseMac();
  char buffer[32];
  snprintf(
      buffer,
      sizeof(buffer),
      "pl-cam-%04x%08x",
      static_cast<unsigned int>((chip_id >> 32) & 0xFFFF),
      static_cast<unsigned int>(chip_id & 0xFFFFFFFF));
  g_hardware_device_id = String(buffer);
  return g_hardware_device_id;
}

String runtimeWifiSsid() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return String(g_runtime_config.wifi_ssid);
  }
  return String(PLANTLAB_WIFI_SSID);
}

String runtimeWifiPassword() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return String(g_runtime_config.wifi_password);
  }
  return String(PLANTLAB_WIFI_PASSWORD);
}

String runtimePlatformUrl() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return String(g_runtime_config.platform_url);
  }
  return String(PLANTLAB_PLATFORM_URL);
}

int runtimePlatformDeviceId() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return static_cast<int>(g_runtime_config.platform_device_id);
  }
  return PLANTLAB_DEVICE_ID;
}

String runtimeDeviceToken() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return String(g_runtime_config.device_token);
  }
  return String(PLANTLAB_DEVICE_TOKEN);
}

void rebuildPlatformClient() {
  g_platform_client.reset();
  const String platform_url = runtimePlatformUrl();
  const String device_token = runtimeDeviceToken();
  const int device_id = runtimePlatformDeviceId();
  g_platform_client.reset(new PlatformClient(platform_url.c_str(), device_id, device_token.c_str()));
}

bool loadProvisionedConfig() {
  camera_node_clear_runtime_config(&g_runtime_config);
  g_preferences.begin(kPreferencesNamespace, true);
  const bool provisioned = g_preferences.getBool(kConfigKeyProvisioned, false);
  if (!provisioned) {
    g_preferences.end();
    rebuildPlatformClient();
    Serial.println("[camera-node] no stored provisioning config");
    return false;
  }

  g_runtime_config.provisioned = provisioned;
  g_runtime_config.config_version = static_cast<uint16_t>(g_preferences.getUShort(kConfigKeyVersion, 0));
  g_runtime_config.camera_node_index = static_cast<uint16_t>(g_preferences.getUShort(kConfigKeyCameraIndex, 0));
  g_runtime_config.platform_device_id = static_cast<uint32_t>(g_preferences.getUInt(kConfigKeyPlatformId, 0));
  String ssid = g_preferences.getString(kConfigKeySsid, "");
  String password = g_preferences.getString(kConfigKeyPassword, "");
  String platform_url = g_preferences.getString(kConfigKeyPlatformUrl, "");
  String device_token = g_preferences.getString(kConfigKeyDeviceToken, "");
  g_preferences.end();

  espnow_copy_bounded_string(g_runtime_config.wifi_ssid, sizeof(g_runtime_config.wifi_ssid), ssid.c_str());
  espnow_copy_bounded_string(g_runtime_config.wifi_password, sizeof(g_runtime_config.wifi_password), password.c_str());
  espnow_copy_bounded_string(g_runtime_config.platform_url, sizeof(g_runtime_config.platform_url), platform_url.c_str());
  espnow_copy_bounded_string(g_runtime_config.device_token, sizeof(g_runtime_config.device_token), device_token.c_str());

  rebuildPlatformClient();
  Serial.printf(
      "[camera-node] loaded provisioning config version=%u camera_index=%u platform_device_id=%u ssid=%s\n",
      static_cast<unsigned int>(g_runtime_config.config_version),
      static_cast<unsigned int>(g_runtime_config.camera_node_index),
      static_cast<unsigned int>(g_runtime_config.platform_device_id),
      g_runtime_config.wifi_ssid);
  return camera_node_runtime_config_complete(g_runtime_config);
}

bool saveProvisionedConfig(const CameraNodeRuntimeConfig& config) {
  if (!camera_node_runtime_config_complete(config)) {
    return false;
  }
  g_preferences.begin(kPreferencesNamespace, false);
  g_preferences.putBool(kConfigKeyProvisioned, true);
  g_preferences.putUShort(kConfigKeyVersion, config.config_version);
  g_preferences.putUShort(kConfigKeyCameraIndex, config.camera_node_index);
  g_preferences.putUInt(kConfigKeyPlatformId, config.platform_device_id);
  g_preferences.putString(kConfigKeySsid, String(config.wifi_ssid));
  g_preferences.putString(kConfigKeyPassword, String(config.wifi_password));
  g_preferences.putString(kConfigKeyPlatformUrl, String(config.platform_url));
  g_preferences.putString(kConfigKeyDeviceToken, String(config.device_token));
  g_preferences.end();
  g_runtime_config = config;
  rebuildPlatformClient();
  return true;
}

String defaultCameraDisplayName() {
  const uint16_t index =
      camera_node_runtime_config_complete(g_runtime_config) ? g_runtime_config.camera_node_index : 0;
  if (index > 0) {
    return String("Camera ") + String(index);
  }
  return String("Camera");
}

void scheduleRestart(uint32_t delay_ms) {
  g_restart_scheduled = true;
  g_restart_at_ms = millis() + delay_ms;
  Serial.printf("[camera-node] reboot scheduled in %lu ms\n", static_cast<unsigned long>(delay_ms));
}

bool platform_enabled() {
  return g_platform_client != nullptr && g_platform_client->configured() &&
         runtimeWifiSsid().length() > 0;
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

  const String wifi_ssid = runtimeWifiSsid();
  const String wifi_password = runtimeWifiPassword();
  Serial.printf("[camera-node] connecting to %s\n", wifi_ssid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);
  WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
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
    const String wifi_ssid = runtimeWifiSsid();
    const String wifi_password = runtimeWifiPassword();
    Serial.printf("[camera-node] retrying Wi-Fi for %s\n", wifi_ssid.c_str());
    WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
    g_last_wifi_attempt_ms = now;
    g_wifi_connect_started_at_ms = now;
    g_wifi_connecting = true;
  }
}

bool sendHeartbeat() {
  if (!platform_enabled() || !g_wifi_ready) {
    return false;
  }

  if (camera_node_runtime_config_complete(g_runtime_config)) {
    HTTPClient http;
    http.setTimeout(kHeartbeatHttpTimeoutMs);
    const String url = g_platform_client->base_url() + "/api/device-nodes/heartbeat";
    if (!http.begin(url)) {
      Serial.println("[camera-node] heartbeat failed: request setup failed");
      return false;
    }
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", runtimeDeviceToken());

    String body =
        "{\"device_id\":" + String(g_platform_client->device_id()) +
        ",\"hardware_device_id\":\"" + stableHardwareDeviceId() +
        "\",\"node_role\":\"camera\",\"status\":\"online\"}";
    const int code = http.POST(body);
    const String response = code > 0 ? http.getString() : http.errorToString(code);
    http.end();
    if (code >= 200 && code < 300) {
      Serial.printf("[camera-node] heartbeat sent to %s (%d)\n", url.c_str(), code);
      return true;
    }
    Serial.printf("[camera-node] heartbeat failed HTTP %d: %s\n", code, response.c_str());
    return false;
  }

  HTTPClient http;
  http.setTimeout(kHeartbeatHttpTimeoutMs);
  const String url = g_platform_client->base_url() + "/health";
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

bool registerDeviceNode() {
  if (!camera_node_runtime_config_complete(g_runtime_config) || !platform_enabled() || !g_wifi_ready) {
    return false;
  }
  if (g_node_registered) {
    return true;
  }

  const unsigned long now = millis();
  if (now - g_last_node_register_attempt_ms < kNodeRegisterRetryMs) {
    return false;
  }
  g_last_node_register_attempt_ms = now;

  HTTPClient http;
  http.setTimeout(kHeartbeatHttpTimeoutMs);
  const String url = g_platform_client->base_url() + "/api/device-nodes/register";
  if (!http.begin(url)) {
    Serial.println("[camera-node] node registration failed: request setup failed");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", runtimeDeviceToken());

  String body =
      "{\"device_id\":" + String(g_platform_client->device_id()) +
      ",\"hardware_device_id\":\"" + stableHardwareDeviceId() +
      "\",\"node_role\":\"camera\"" +
      ",\"node_index\":" + String(static_cast<unsigned int>(g_runtime_config.camera_node_index)) +
      ",\"display_name\":\"" + defaultCameraDisplayName() +
      "\",\"hardware_model\":\"xiao_esp32s3_camera\"" +
      ",\"hardware_version\":\"" + String(BOARD_NAME) +
      "\",\"software_version\":\"" + String(kCameraSoftwareVersion) +
      "\",\"capabilities\":{\"camera\":true}" +
      ",\"status\":\"online\"}";

  const int code = http.POST(body);
  const String response = code > 0 ? http.getString() : http.errorToString(code);
  http.end();

  if (code >= 200 && code < 300) {
    g_node_registered = true;
    Serial.printf("[camera-node] node registration succeeded at %s (%d)\n", url.c_str(), code);
    return true;
  }

  Serial.printf("[camera-node] node registration failed HTTP %d: %s\n", code, response.c_str());
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
  if (camera_node_runtime_config_complete(g_runtime_config) && !registerDeviceNode()) {
    Serial.println("[camera-node] upload skipped: camera node is not registered yet");
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
  const bool uploaded = g_platform_client->upload_jpeg(
      frame->buf,
      frame->len,
      "esp32-camera.jpg",
      camera_node_runtime_config_complete(g_runtime_config) ? stableHardwareDeviceId().c_str() : nullptr,
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

  if (command == EspNowCommandType::kProvisionStart) {
    if (g_capture_in_progress) {
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kBusy);
      return;
    }
    const CameraProvisioningPayload payload = espnow_packet_get_provisioning_payload(packet);
    CameraNodeRuntimeConfig next_config{};
    if (!camera_node_apply_provisioning_payload(&next_config, payload)) {
      Serial.println("[camera-node] provisioning payload invalid");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kInvalid);
      return;
    }
    if (camera_node_runtime_config_equal(g_runtime_config, next_config)) {
      Serial.println("[camera-node] provisioning config unchanged");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
      return;
    }
    if (!saveProvisionedConfig(next_config)) {
      Serial.println("[camera-node] provisioning save failed");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kFailed);
      return;
    }
    g_node_registered = false;
    Serial.printf(
        "[camera-node] provisioning config saved version=%u camera_index=%u platform_device_id=%u ssid=%s\n",
        static_cast<unsigned int>(next_config.config_version),
        static_cast<unsigned int>(next_config.camera_node_index),
        static_cast<unsigned int>(next_config.platform_device_id),
        next_config.wifi_ssid);
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
    scheduleRestart(1500UL);
    return;
  }

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
  Serial.printf("[camera-node] hardware_device_id: %s\n", stableHardwareDeviceId().c_str());

  disableBluetooth();
  enterIdlePowerMode();
  const bool loaded_provisioned_config = loadProvisionedConfig();
  if (loaded_provisioned_config) {
    Serial.println("[camera-node] runtime config source: Preferences");
  } else {
    rebuildPlatformClient();
    Serial.println("[camera-node] runtime config source: compile-time fallback");
  }
  if (g_platform_client != nullptr) {
    Serial.printf("[camera-node] base_url: %s\n", g_platform_client->base_url().c_str());
    Serial.printf("[camera-node] device_id: %d\n", g_platform_client->device_id());
  }
  setupWiFi();
  setupEspNow();
  deinitCamera();
}

void loop() {
  if (g_restart_scheduled && millis() >= g_restart_at_ms) {
    g_restart_scheduled = false;
    Serial.println("[camera-node] rebooting to apply provisioning");
    ESP.restart();
  }

  maintainWiFiConnection();

  const unsigned long now = millis();
  if (camera_node_runtime_config_complete(g_runtime_config) && g_wifi_ready) {
    registerDeviceNode();
  }
  if (platform_enabled() && g_wifi_ready && now - g_last_heartbeat_ms >= PLANTLAB_CAMERA_HEARTBEAT_INTERVAL_MS) {
    g_last_heartbeat_ms = now;
    sendHeartbeat();
  }

  handleCaptureRequest();
  delay(2);
}
