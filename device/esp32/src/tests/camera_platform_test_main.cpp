#include <Arduino.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_now.h>
#include <esp_system.h>
#include <esp_wifi.h>

#include <memory>

#include "camera_node_runtime_config.h"
#include "camera/xiao_camera.h"
#include "config.h"
#include "contracts/plantlab_contracts.h"
#include "espnow_test_protocol.h"
#include "firmware_version.h"
#include "ota/ota_update_manager.h"
#include "platform/platform_client.h"
#include "time/time_sync_manager.h"

extern "C" {
#include "esp_bt.h"
}

namespace {
constexpr char kPreferencesNamespace[] = "plcam";
constexpr char kConfigKeyProvisioned[] = "prov";
constexpr char kConfigKeyVersion[] = "ver";
constexpr char kConfigKeyCameraIndex[] = "cam_idx";
constexpr char kConfigKeyPlatformId[] = "plat_id";
constexpr char kConfigKeyCameraRole[] = "cam_role";
constexpr char kConfigKeyCapturePhaseSeconds[] = "cap_phase";
constexpr char kConfigKeySsid[] = "wifi_ssid";
constexpr char kConfigKeyPassword[] = "wifi_pass";
constexpr char kConfigKeyPlatformUrl[] = "plat_url";
constexpr char kConfigKeyDeviceToken[] = "dev_token";
constexpr char kConfigKeyBootCounter[] = "boot_count";
constexpr char kNodeRoleCamera[] = "camera";
constexpr char kCameraHardwareModel[] = "xiao_esp32s3_camera";
constexpr const char* kCameraSoftwareVersion = plantlab::kCameraSoftwareVersion;
constexpr uint16_t kTopCameraNodeIndex = 1;
constexpr uint16_t kSideCameraNodeIndex = 2;
constexpr uint16_t kTopCameraCapturePhaseSeconds = 0;
constexpr uint16_t kSideCameraCapturePhaseSeconds = 30;
XiaoCamera g_camera;
Preferences g_preferences;
std::unique_ptr<PlatformClient> g_platform_client;
std::unique_ptr<plantlab::OtaUpdateManager> g_ota_update_manager;
CameraNodeRuntimeConfig g_runtime_config{};
String g_hardware_device_id;
String g_serial_command_buffer;

constexpr uint32_t kWifiReconnectRetryMs = 5000UL;
constexpr uint32_t kHeartbeatHttpTimeoutMs = 8000UL;
constexpr uint32_t kNodeRegisterRetryMs = 5000UL;
constexpr uint32_t kCommandPollIntervalMs = 1000UL;
constexpr uint8_t kImageUploadMaxAttempts = 3;
constexpr uint32_t kImageUploadRetryBaseDelayMs = 1000UL;
constexpr uint8_t kEspNowBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

unsigned long g_last_wifi_attempt_ms = 0;
unsigned long g_last_heartbeat_ms = 0;
unsigned long g_last_node_register_attempt_ms = 0;
unsigned long g_last_command_poll_ms = 0;
unsigned long g_wifi_connect_started_at_ms = 0;
bool g_wifi_connecting = false;
bool g_wifi_ready = false;
bool g_wifi_runtime_configured = false;
bool g_camera_initialized = false;
bool g_capture_in_progress = false;
bool g_scheduled_capture_paused = false;
bool g_node_registered = false;
bool g_restart_scheduled = false;
unsigned long g_restart_at_ms = 0;
uint32_t g_boot_counter = 0;
uint32_t g_capture_sequence = 0;
PlatformErrorCounters g_diagnostic_error_counters{};
String g_last_diagnostic_error_code;
String g_last_diagnostic_error_message;
unsigned long g_last_image_upload_ms = 0;
bool g_last_provision_sender_known = false;
uint8_t g_last_provision_sender_mac[6] = {0};
uint32_t g_last_provision_request_id = 0;

volatile bool g_capture_requested = false;
volatile bool g_capture_request_has_sender = false;
volatile uint32_t g_capture_request_id = 0;
volatile uint32_t g_capture_command_id = 0;
volatile uint32_t g_capture_request_received_at_ms = 0;
uint8_t g_capture_request_mac[6] = {0};
}

const char* resetReasonLabel(esp_reset_reason_t reason) {
  switch (reason) {
    case ESP_RST_POWERON:
      return "power_on";
    case ESP_RST_SW:
      return "software_reset";
    case ESP_RST_DEEPSLEEP:
      return "deep_sleep";
    case ESP_RST_BROWNOUT:
      return "brownout";
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT:
    case ESP_RST_INT_WDT:
      return "watchdog";
    case ESP_RST_PANIC:
      return "panic";
    default:
      return "unknown";
  }
}

uint32_t ageSecondsSince(unsigned long now, unsigned long started_at_ms) {
  if (started_at_ms == 0 || now < started_at_ms) {
    return 0;
  }
  return static_cast<uint32_t>((now - started_at_ms) / 1000UL);
}

void recordDiagnosticError(const char* code, const String& message) {
  g_last_diagnostic_error_code = code == nullptr ? "" : String(code);
  g_last_diagnostic_error_message = message;
  if (g_last_diagnostic_error_message.length() > 120) {
    g_last_diagnostic_error_message = g_last_diagnostic_error_message.substring(0, 120);
  }
}

void clearRecoveredDiagnosticError(const char* code) {
  if (code == nullptr || g_last_diagnostic_error_code != code) {
    return;
  }
  g_last_diagnostic_error_code = "";
  g_last_diagnostic_error_message = "";
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

void initReliabilityBootCounter() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[camera-node] boot counter unavailable");
    return;
  }
  const uint32_t previous = g_preferences.getUInt(kConfigKeyBootCounter, 0);
  g_boot_counter = previous + 1;
  g_preferences.putUInt(kConfigKeyBootCounter, g_boot_counter);
  g_preferences.end();
  Serial.printf("[camera-node] reliability boot_counter=%lu\n", static_cast<unsigned long>(g_boot_counter));
}

String nextImageIdempotencyKey() {
  ++g_capture_sequence;
  return stableHardwareDeviceId() + ":" + String(g_boot_counter) + ":" + String(g_capture_sequence) +
         ":" + String(static_cast<unsigned long>(g_capture_request_id)) +
         ":" + String(static_cast<unsigned long>(g_capture_command_id));
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

const char* runtimeCameraRole() {
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    return espnow_camera_role_label(g_runtime_config.camera_role);
  }
  return "";
}

void scheduleRestart(uint32_t delay_ms);

void rebuildPlatformClient() {
  g_ota_update_manager.reset();
  g_platform_client.reset();
  const String platform_url = runtimePlatformUrl();
  const String device_token = runtimeDeviceToken();
  const int device_id = runtimePlatformDeviceId();
  g_platform_client.reset(new PlatformClient(platform_url.c_str(), device_id, device_token.c_str()));
  g_ota_update_manager.reset(new plantlab::OtaUpdateManager(
      g_platform_client.get(),
      stableHardwareDeviceId().c_str(),
      kNodeRoleCamera,
      kCameraHardwareModel,
      kCameraSoftwareVersion,
      plantlab::kCameraSoftwareVersionCode));
  g_ota_update_manager->begin();
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
  g_runtime_config.camera_role = static_cast<uint8_t>(g_preferences.getUChar(kConfigKeyCameraRole, 0));
  g_runtime_config.capture_phase_seconds =
      static_cast<uint16_t>(g_preferences.getUShort(kConfigKeyCapturePhaseSeconds, 0));
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
      "[camera-node] loaded provisioning config version=%u camera_index=%u camera_role=%s phase_s=%u platform_device_id=%u ssid=%s\n",
      static_cast<unsigned int>(g_runtime_config.config_version),
      static_cast<unsigned int>(g_runtime_config.camera_node_index),
      runtimeCameraRole(),
      static_cast<unsigned int>(g_runtime_config.capture_phase_seconds),
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
  g_preferences.putUChar(kConfigKeyCameraRole, config.camera_role);
  g_preferences.putUShort(kConfigKeyCapturePhaseSeconds, config.capture_phase_seconds);
  g_preferences.putString(kConfigKeySsid, String(config.wifi_ssid));
  g_preferences.putString(kConfigKeyPassword, String(config.wifi_password));
  g_preferences.putString(kConfigKeyPlatformUrl, String(config.platform_url));
  g_preferences.putString(kConfigKeyDeviceToken, String(config.device_token));
  g_preferences.end();
  g_runtime_config = config;
  rebuildPlatformClient();
  return true;
}

void printRuntimeConfig() {
  Serial.printf("[camera-node] hardware_device_id=%s\n", stableHardwareDeviceId().c_str());
  Serial.printf("[camera-node] firmware_version=%s version_code=%d\n", kCameraSoftwareVersion, plantlab::kCameraSoftwareVersionCode);
  Serial.printf("[camera-node] provisioned=%s complete=%s\n", g_runtime_config.provisioned ? "yes" : "no", camera_node_runtime_config_complete(g_runtime_config) ? "yes" : "no");
  Serial.printf(
      "[camera-node] camera_index=%u camera_role=%s phase_s=%u platform_device_id=%u\n",
      static_cast<unsigned int>(g_runtime_config.camera_node_index),
      runtimeCameraRole(),
      static_cast<unsigned int>(g_runtime_config.capture_phase_seconds),
      static_cast<unsigned int>(g_runtime_config.platform_device_id));
  Serial.printf("[camera-node] wifi_ready=%s node_registered=%s base_url=%s\n", g_wifi_ready ? "yes" : "no", g_node_registered ? "yes" : "no", runtimePlatformUrl().c_str());
}

bool setStoredCameraRole(CameraRoleCode role) {
  if (!camera_node_runtime_config_complete(g_runtime_config)) {
    Serial.println("[camera-node] role update failed: no complete stored provisioning config");
    return false;
  }

  CameraNodeRuntimeConfig next_config = g_runtime_config;
  next_config.camera_role = static_cast<uint8_t>(role);
  if (role == CameraRoleCode::kSide) {
    next_config.camera_node_index = kSideCameraNodeIndex;
    next_config.capture_phase_seconds = kSideCameraCapturePhaseSeconds;
  } else {
    next_config.camera_node_index = kTopCameraNodeIndex;
    next_config.capture_phase_seconds = kTopCameraCapturePhaseSeconds;
  }

  if (camera_node_runtime_config_equal(g_runtime_config, next_config)) {
    Serial.printf("[camera-node] role already %s\n", espnow_camera_role_label(next_config.camera_role));
    printRuntimeConfig();
    return true;
  }

  if (!saveProvisionedConfig(next_config)) {
    Serial.println("[camera-node] role update failed: save failed");
    return false;
  }
  g_node_registered = false;
  Serial.printf(
      "[camera-node] role updated to %s camera_index=%u phase_s=%u; Wi-Fi/token/platform settings preserved\n",
      espnow_camera_role_label(next_config.camera_role),
      static_cast<unsigned int>(next_config.camera_node_index),
      static_cast<unsigned int>(next_config.capture_phase_seconds));
  scheduleRestart(1500UL);
  return true;
}

void queueLocalCapture() {
  if (!camera_node_runtime_config_complete(g_runtime_config)) {
    Serial.println("[camera-node] local capture rejected: no complete stored provisioning config");
    return;
  }
  if (g_capture_requested || g_capture_in_progress) {
    Serial.println("[camera-node] local capture rejected: capture already active");
    return;
  }
  memset(g_capture_request_mac, 0, sizeof(g_capture_request_mac));
  g_capture_request_id = 0;
  g_capture_command_id = 0;
  g_capture_request_received_at_ms = millis();
  g_capture_request_has_sender = false;
  g_capture_requested = true;
  Serial.printf("[camera-node] local capture queued camera_role=%s\n", runtimeCameraRole());
}

bool captureAndDumpSerialImage();

void printSerialHelp() {
  Serial.println("[camera-node] USB commands:");
  Serial.println("  camera status");
  Serial.println("  camera role side");
  Serial.println("  camera role top");
  Serial.println("  camera capture");
  Serial.println("  camera local-capture");
  Serial.println("  camera help");
}

void handleSerialCommandLine(String line) {
  line.trim();
  if (line.length() == 0) {
    return;
  }
  line.toLowerCase();

  if (line == "help" || line == "camera help") {
    printSerialHelp();
    return;
  }
  if (line == "status" || line == "camera status") {
    printRuntimeConfig();
    return;
  }
  if (line == "camera capture" || line == "capture") {
    queueLocalCapture();
    return;
  }
  if (line == "camera local-capture" || line == "local-capture") {
    captureAndDumpSerialImage();
    return;
  }
  if (line == "camera role side" || line == "role side") {
    setStoredCameraRole(CameraRoleCode::kSide);
    return;
  }
  if (line == "camera role top" || line == "role top") {
    setStoredCameraRole(CameraRoleCode::kTop);
    return;
  }

  Serial.printf("[camera-node] unknown USB command: %s\n", line.c_str());
  printSerialHelp();
}

String defaultCameraDisplayName() {
  const char* role = runtimeCameraRole();
  if (String(role) == "top") {
    return String("Top Camera");
  }
  if (String(role) == "side") {
    return String("Side Camera");
  }
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
    case EspNowCommandType::kPauseCapture:
      return "pause_capture";
    case EspNowCommandType::kUpdateCaptureInterval:
      return "update_capture_interval";
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
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
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
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
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
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_ack_failed", "ESP-NOW ACK send failed");
    Serial.printf("[camera-node] ESP-NOW ack send failed err=%d\n", static_cast<int>(err));
  }
}

void sendHealthReport(const uint8_t* target_mac, uint32_t request_id = 0) {
  if (!ensurePeer(target_mac)) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
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
  uint32_t flags = 0;
  if (g_wifi_ready) {
    flags |= ESPNOW_HEALTH_FLAG_WIFI_READY;
  }
  if (g_node_registered) {
    flags |= ESPNOW_HEALTH_FLAG_NODE_REGISTERED;
  }
  if (camera_node_runtime_config_complete(g_runtime_config)) {
    flags |= ESPNOW_HEALTH_FLAG_CONFIG_READY;
  }
  packet.value_u32_1 = flags;
  packet.value_u32_2 = camera_node_runtime_config_complete(g_runtime_config)
                           ? (static_cast<uint32_t>(g_runtime_config.camera_role) << 16) |
                                 static_cast<uint32_t>(g_runtime_config.camera_node_index)
                           : 0;

  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err == ESP_OK) {
    Serial.printf(
        "[camera-node] HEALTH request=%u flags=%u camera_role=%s camera_index=%u -> %s\n",
        static_cast<unsigned int>(request_id),
        static_cast<unsigned int>(packet.value_u32_1),
        runtimeCameraRole(),
        static_cast<unsigned int>(packet.value_u32_2 & 0xFFFFu),
        macToString(target_mac).c_str());
  } else {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_health_failed", "ESP-NOW health report failed");
    Serial.printf("[camera-node] HEALTH send failed err=%d\n", static_cast<int>(err));
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
  if (g_wifi_runtime_configured || !g_wifi_ready) {
    return;
  }

  esp_err_t ps_err = esp_wifi_set_ps(WIFI_PS_NONE);
  esp_err_t tx_err = esp_wifi_set_max_tx_power(PLANTLAB_WIFI_MAX_TX_POWER);
  if (ps_err == ESP_OK && tx_err == ESP_OK) {
    g_wifi_runtime_configured = true;
    Serial.printf(
        "[camera-node] Wi-Fi tuned for ESP-NOW reliability mode=none tx_power=%d\n",
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
  WiFi.setSleep(false);
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
      g_wifi_runtime_configured = false;
      Serial.printf("[camera-node] Wi-Fi connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    enableLowPowerWiFi();
    return;
  }

  g_wifi_ready = false;
  g_wifi_runtime_configured = false;

  const unsigned long now = millis();
  if (g_wifi_connecting && now - g_wifi_connect_started_at_ms >= PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    g_wifi_connecting = false;
    recordDiagnosticError("wifi_connect_timeout", "Wi-Fi connect timed out");
    Serial.println("[camera-node] Wi-Fi connect timed out");
  }

  if (!g_wifi_connecting && now - g_last_wifi_attempt_ms >= kWifiReconnectRetryMs) {
    if (g_last_wifi_attempt_ms != 0 || g_wifi_ready) {
      ++g_diagnostic_error_counters.wifi_reconnects;
    }
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
    PlatformStatus heartbeat{};
    heartbeat.hardware_device_id = stableHardwareDeviceId();
    heartbeat.node_role = kNodeRoleCamera;
    heartbeat.status = "online";
    heartbeat.message = "camera online";
    heartbeat.software_version = kCameraSoftwareVersion;
    heartbeat.camera_role = runtimeCameraRole();
    const unsigned long now = millis();
    heartbeat.diagnostics.valid = true;
    heartbeat.diagnostics.has_uptime_seconds = true;
    heartbeat.diagnostics.uptime_seconds = static_cast<uint32_t>(now / 1000UL);
    if (WiFi.status() == WL_CONNECTED) {
      heartbeat.diagnostics.has_wifi_rssi_dbm = true;
      heartbeat.diagnostics.wifi_rssi_dbm = WiFi.RSSI();
    }
    heartbeat.diagnostics.reboot_reason = resetReasonLabel(esp_reset_reason());
    heartbeat.diagnostics.provisioning_state =
        g_capture_in_progress ? "capture_busy" : (g_node_registered ? "online" : "node_registering");
    if (g_last_image_upload_ms > 0) {
      heartbeat.diagnostics.has_last_camera_image_upload_age_seconds = true;
      heartbeat.diagnostics.last_camera_image_upload_age_seconds = ageSecondsSince(now, g_last_image_upload_ms);
    }
    heartbeat.diagnostics.has_error_counters = true;
    heartbeat.diagnostics.error_counters = g_diagnostic_error_counters;
    heartbeat.diagnostics.last_error_code = g_last_diagnostic_error_code;
    heartbeat.diagnostics.last_error_message = g_last_diagnostic_error_message;

    String error;
    if (g_platform_client->send_hardware_heartbeat(heartbeat, &error)) {
      clearRecoveredDiagnosticError("heartbeat_upload_failed");
      Serial.printf(
          "[camera-node] heartbeat sent to %s/api/hardware/heartbeat\n",
          g_platform_client->base_url().c_str());
      if (g_last_provision_sender_known) {
        sendHealthReport(g_last_provision_sender_mac, g_last_provision_request_id);
      }
      return true;
    }
    Serial.printf("[camera-node] heartbeat failed: %s\n", error.c_str());
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("heartbeat_upload_failed", "heartbeat upload failed");
    return false;
  }

  HTTPClient http;
  http.setTimeout(kHeartbeatHttpTimeoutMs);
  const String url = g_platform_client->base_url() + "/health";
  if (!http.begin(url)) {
    Serial.println("[camera-node] heartbeat failed: request setup failed");
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("heartbeat_upload_failed", "heartbeat request setup failed");
    return false;
  }

  const int code = http.GET();
  const String body = code > 0 ? http.getString() : http.errorToString(code);
  http.end();

  if (code >= 200 && code < 300) {
    clearRecoveredDiagnosticError("heartbeat_upload_failed");
    Serial.printf("[camera-node] heartbeat sent to %s (%d)\n", url.c_str(), code);
    return true;
  }

  Serial.printf("[camera-node] heartbeat failed HTTP %d: %s\n", code, body.c_str());
  ++g_diagnostic_error_counters.upload_failures;
  recordDiagnosticError("heartbeat_upload_failed", "heartbeat upload failed");
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
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("node_register_failed", "node registration request setup failed");
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
      "\",\"hardware_model\":\"" + String(kCameraHardwareModel) +
      "\"" +
      ",\"hardware_version\":\"" + String(BOARD_NAME) +
      "\",\"software_version\":\"" + String(kCameraSoftwareVersion) +
      "\",\"camera_role\":\"" + String(runtimeCameraRole()) +
      "\",\"capabilities\":{\"camera\":true,\"camera_role\":\"" + String(runtimeCameraRole()) +
      "\",\"capture_phase_seconds\":" + String(static_cast<unsigned int>(g_runtime_config.capture_phase_seconds)) + "}" +
      ",\"status\":\"online\"}";

  const int code = http.POST(body);
  const String response = code > 0 ? http.getString() : http.errorToString(code);
  http.end();

  if (code >= 200 && code < 300) {
    g_node_registered = true;
    Serial.printf("[camera-node] node registration succeeded at %s (%d)\n", url.c_str(), code);
    sendHealthReport(kEspNowBroadcastMac);
    if (g_last_provision_sender_known) {
      sendHealthReport(g_last_provision_sender_mac, g_last_provision_request_id);
    }
    return true;
  }

  Serial.printf("[camera-node] node registration failed HTTP %d: %s\n", code, response.c_str());
  ++g_diagnostic_error_counters.upload_failures;
  recordDiagnosticError("node_register_failed", "node registration failed");
  return false;
}

bool initCamera() {
  if (g_camera_initialized) {
    return true;
  }

  XiaoCameraOptions camera_options = makeDefaultXiaoCameraOptions();
  if (!g_camera.begin(camera_options)) {
    Serial.println("[camera-node] camera init failed");
    recordDiagnosticError("camera_init_failed", "camera init failed");
    return false;
  }

  g_camera_initialized = true;
  Serial.println("[camera-node] camera init succeeded");
  if (g_camera.warmup()) {
    Serial.println("[camera-node] camera warm-up complete");
  } else {
    Serial.println("[camera-node] camera warm-up skipped: no frames captured");
  }
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

bool captureAndDumpSerialImage() {
  if (g_capture_requested || g_capture_in_progress) {
    Serial.println("[camera-node] local serial capture rejected: capture already active");
    return false;
  }
  if (!initCamera()) {
    return false;
  }

  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    Serial.println("[camera-node] local serial image capture failed");
    recordDiagnosticError("image_capture_failed", "local serial image capture failed");
    deinitCamera();
    return false;
  }

  Serial.printf(
      "[camera-node] LOCAL_JPEG_BEGIN bytes=%u width=%u height=%u\n",
      static_cast<unsigned int>(frame->len),
      static_cast<unsigned int>(frame->width),
      static_cast<unsigned int>(frame->height));
  Serial.write(frame->buf, frame->len);
  Serial.println();
  Serial.println("[camera-node] LOCAL_JPEG_END");
  Serial.flush();

  esp_camera_fb_return(frame);
  deinitCamera();
  return true;
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
    recordDiagnosticError("image_capture_failed", "image capture failed");
    deinitCamera();
    return false;
  }

  Serial.printf(
      "[camera-node] image captured %ux%u %u bytes\n",
      static_cast<unsigned int>(frame->width),
      static_cast<unsigned int>(frame->height),
      static_cast<unsigned int>(frame->len));

  const unsigned long upload_started_at_ms = millis();
  Serial.printf(
      "[camera-node] upload start command_id=%lu request=%u bytes=%u\n",
      static_cast<unsigned long>(g_capture_command_id),
      static_cast<unsigned int>(g_capture_request_id),
      static_cast<unsigned int>(frame->len));
  const String idempotency_key = nextImageIdempotencyKey();
  String error;
  int upload_http_status = 0;
  bool uploaded = false;
  for (uint8_t attempt = 1; attempt <= kImageUploadMaxAttempts; ++attempt) {
    error = "";
    upload_http_status = 0;
    uploaded = g_platform_client->upload_jpeg(
        frame->buf,
        frame->len,
        "esp32-camera.jpg",
        camera_node_runtime_config_complete(g_runtime_config) ? stableHardwareDeviceId().c_str() : nullptr,
        camera_node_runtime_config_complete(g_runtime_config) ? runtimeCameraRole() : nullptr,
        idempotency_key.c_str(),
        &upload_http_status,
        &error);
    if (uploaded) {
      Serial.printf(
          "[camera-node] upload attempt success command_id=%lu request=%u attempt=%u/%u http=%d idempotency_key=%s\n",
          static_cast<unsigned long>(g_capture_command_id),
          static_cast<unsigned int>(g_capture_request_id),
          static_cast<unsigned int>(attempt),
          static_cast<unsigned int>(kImageUploadMaxAttempts),
          upload_http_status,
          idempotency_key.c_str());
      break;
    }
    Serial.printf(
        "[camera-node] upload attempt failed command_id=%lu request=%u attempt=%u/%u http=%d error=%s\n",
        static_cast<unsigned long>(g_capture_command_id),
        static_cast<unsigned int>(g_capture_request_id),
        static_cast<unsigned int>(attempt),
        static_cast<unsigned int>(kImageUploadMaxAttempts),
        upload_http_status,
        error.c_str());
    if (attempt < kImageUploadMaxAttempts) {
      delay(kImageUploadRetryBaseDelayMs * attempt);
    }
  }
  esp_camera_fb_return(frame);

  if (uploaded) {
    g_last_image_upload_ms = millis();
    clearRecoveredDiagnosticError("image_upload_failed");
    Serial.printf(
        "[camera-node] upload success command_id=%lu request=%u http=%d elapsed_ms=%lu\n",
        static_cast<unsigned long>(g_capture_command_id),
        static_cast<unsigned int>(g_capture_request_id),
        upload_http_status,
        static_cast<unsigned long>(millis() - upload_started_at_ms));
  } else {
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("image_upload_failed", "image upload failed");
    Serial.printf(
        "[camera-node] upload failed command_id=%lu request=%u http=%d elapsed_ms=%lu error=%s\n",
        static_cast<unsigned long>(g_capture_command_id),
        static_cast<unsigned int>(g_capture_request_id),
        upload_http_status,
        static_cast<unsigned long>(millis() - upload_started_at_ms),
        error.c_str());
  }

  deinitCamera();
  return uploaded;
}

bool reportCameraCommandResult(
    const PlatformCommand& command,
    const char* status,
    const char* message,
    const char* error_code = nullptr) {
  if (g_platform_client == nullptr) {
    return false;
  }
  String error;
  const bool reported = g_platform_client->report_contract_command_result(
      command,
      stableHardwareDeviceId().c_str(),
      kNodeRoleCamera,
      status,
      message,
      false,
      false,
      &error,
      -1,
      error_code);
  if (!reported) {
    Serial.printf("[camera-node] command result report failed command_id=%d status=%s error=%s\n", command.id, status, error.c_str());
    recordDiagnosticError("command_result_failed", "command result report failed");
    return false;
  }
  clearRecoveredDiagnosticError("command_result_failed");
  Serial.printf("[camera-node] command %d marked %s: %s\n", command.id, status, message == nullptr ? "" : message);
  return true;
}

bool cameraCommandTargetsThisNode(const PlatformCommand& command) {
  if (command.target_hardware_device_id.length() > 0 && command.target_hardware_device_id != stableHardwareDeviceId()) {
    return false;
  }
  String role = command.target_camera_role.length() > 0 ? command.target_camera_role : command.value;
  role.trim();
  role.toLowerCase();
  if (role.length() == 0 || role == "all") {
    return true;
  }
  return role == runtimeCameraRole();
}

void executeDirectCaptureCommand(const PlatformCommand& command) {
  if (!cameraCommandTargetsThisNode(command)) {
    reportCameraCommandResult(
        command,
        PLANTLAB_COMMAND_STATUS_REJECTED,
        "camera role does not match this node",
        PLANTLAB_COMMAND_ERROR_UNSUPPORTED_TARGET);
    return;
  }

  if (g_capture_requested || g_capture_in_progress) {
    reportCameraCommandResult(
        command,
        PLANTLAB_COMMAND_STATUS_FAILED,
        "camera is busy capturing another image",
        PLANTLAB_COMMAND_ERROR_DEVICE_BUSY);
    return;
  }

  reportCameraCommandResult(command, PLANTLAB_COMMAND_STATUS_IN_PROGRESS, "camera capture started");
  g_capture_requested = false;
  g_capture_request_has_sender = false;
  g_capture_request_id = 0;
  g_capture_command_id = static_cast<uint32_t>(command.id);
  g_capture_request_received_at_ms = millis();
  g_capture_in_progress = true;

  Serial.printf("[camera-node] direct capture command_id=%d camera_role=%s\n", command.id, runtimeCameraRole());
  enterActiveCaptureMode();
  const bool success = captureAndUploadImage();
  enterIdlePowerMode();
  g_capture_in_progress = false;

  if (success) {
    reportCameraCommandResult(command, PLANTLAB_COMMAND_STATUS_COMPLETED, "camera uploaded a new image");
  } else {
    reportCameraCommandResult(
        command,
        PLANTLAB_COMMAND_STATUS_FAILED,
        "camera capture failed",
        PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR);
  }
  g_capture_command_id = 0;
}

void handlePolledPlatformCommand(const PlatformCommand& command) {
  if (!command.valid) {
    return;
  }
  Serial.printf(
      "[camera-node] command polled id=%d target=%s action=%s type=%s camera_role=%s hardware_target=%s\n",
      command.id,
      command.target.c_str(),
      command.action.c_str(),
      command.command_type.c_str(),
      command.target_camera_role.c_str(),
      command.target_hardware_device_id.c_str());
  if (command.target == "camera" && command.action == "capture") {
    executeDirectCaptureCommand(command);
    return;
  }
  reportCameraCommandResult(
      command,
      PLANTLAB_COMMAND_STATUS_REJECTED,
      "camera node supports capture commands only",
      PLANTLAB_COMMAND_ERROR_UNSUPPORTED_TARGET);
}

void serviceCommandPoll(unsigned long now) {
  if (
      g_platform_client == nullptr ||
      !g_node_registered ||
      !platform_enabled() ||
      !g_wifi_ready ||
      g_capture_requested ||
      g_capture_in_progress ||
      g_restart_scheduled ||
      now - g_last_command_poll_ms < kCommandPollIntervalMs) {
    return;
  }
  g_last_command_poll_ms = now;

  PlatformCommand commands[1]{};
  String error;
  const int count = g_platform_client->poll_contract_commands(
      stableHardwareDeviceId().c_str(),
      kNodeRoleCamera,
      kCameraSoftwareVersion,
      kCameraHardwareModel,
      commands,
      1,
      &error);
  if (count < 0) {
    Serial.printf("[camera-node] command poll failed: %s\n", error.c_str());
    recordDiagnosticError("command_poll_failed", "command poll failed");
    return;
  }
  clearRecoveredDiagnosticError("command_poll_failed");
  for (int index = 0; index < count; ++index) {
    handlePolledPlatformCommand(commands[index]);
  }
}

void onEspNowReceive(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    Serial.printf("[camera-node] ESP-NOW ignored packet length=%d\n", len);
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_invalid_packet", "ESP-NOW packet length invalid");
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    Serial.println("[camera-node] ESP-NOW ignored invalid packet");
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_invalid_packet", "ESP-NOW packet invalid");
    return;
  }

  const EspNowMessageKind kind = static_cast<EspNowMessageKind>(packet.kind);
  if (kind != EspNowMessageKind::kCommand) {
    return;
  }

  const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);
  Serial.printf(
      "[camera-node] ESP-NOW command received request=%u command=%s command_id=%lu from %s\n",
      static_cast<unsigned int>(packet.request_id),
      commandToString(command),
      static_cast<unsigned long>(packet.value_u32_1),
      macToString(mac_addr).c_str());

  if (command == EspNowCommandType::kProvisionStart) {
    memcpy(g_last_provision_sender_mac, mac_addr, sizeof(g_last_provision_sender_mac));
    g_last_provision_sender_known = true;
    g_last_provision_request_id = packet.request_id;
    if (g_capture_in_progress) {
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kBusy);
      return;
    }
    const CameraProvisioningPayload payload = espnow_packet_get_provisioning_payload(packet);
    CameraNodeRuntimeConfig next_config{};
    if (!camera_node_apply_provisioning_payload(&next_config, payload)) {
      Serial.println("[camera-node] provisioning payload invalid");
      ++g_diagnostic_error_counters.ble_provisioning_failures;
      recordDiagnosticError("espnow_provisioning_invalid", "camera provisioning payload invalid");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kInvalid);
      return;
    }
    if (!camera_node_should_accept_provisioning_config(g_runtime_config, next_config)) {
      Serial.printf(
          "[camera-node] provisioning role change rejected local_role=%s requested_role=%s request=%u\n",
          runtimeCameraRole(),
          espnow_camera_role_label(next_config.camera_role),
          static_cast<unsigned int>(packet.request_id));
      recordDiagnosticError("espnow_provisioning_role_rejected", "camera provisioning role change rejected");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kInvalid);
      return;
    }
    if (camera_node_runtime_config_equal(g_runtime_config, next_config)) {
      Serial.println("[camera-node] provisioning config unchanged");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
      if (g_node_registered && g_wifi_ready) {
        sendHealthReport(mac_addr, packet.request_id);
      }
      return;
    }
    if (!saveProvisionedConfig(next_config)) {
      Serial.println("[camera-node] provisioning save failed");
      ++g_diagnostic_error_counters.ble_provisioning_failures;
      recordDiagnosticError("espnow_provisioning_save_failed", "camera provisioning save failed");
      sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kFailed);
      return;
    }
    g_node_registered = false;
    Serial.printf(
        "[camera-node] provisioning config saved version=%u camera_index=%u camera_role=%s phase_s=%u platform_device_id=%u ssid=%s\n",
        static_cast<unsigned int>(next_config.config_version),
        static_cast<unsigned int>(next_config.camera_node_index),
        espnow_camera_role_label(next_config.camera_role),
        static_cast<unsigned int>(next_config.capture_phase_seconds),
        static_cast<unsigned int>(next_config.platform_device_id),
        next_config.wifi_ssid);
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kOk);
    scheduleRestart(1500UL);
    return;
  }

  if (command == EspNowCommandType::kPauseCapture) {
    g_scheduled_capture_paused = packet.value_u32_1 != 0;
    Serial.printf(
        "[camera-node] scheduled capture pause set to %s request=%u\n",
        g_scheduled_capture_paused ? "paused" : "resumed",
        static_cast<unsigned int>(packet.request_id));
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kOk, packet.value_u32_1, 0);
    return;
  }

  if (command != EspNowCommandType::kCaptureImage) {
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kUnsupported);
    return;
  }

  const uint8_t requested_camera_role = static_cast<uint8_t>(packet.value_u32_2 & 0xFFu);
  if (requested_camera_role != 0 && camera_node_runtime_config_complete(g_runtime_config) &&
      requested_camera_role != g_runtime_config.camera_role) {
    Serial.printf(
        "[camera-node] ignoring capture for camera_role=%s local_role=%s request=%u\n",
        espnow_camera_role_label(requested_camera_role),
        runtimeCameraRole(),
        static_cast<unsigned int>(packet.request_id));
    return;
  }

  const bool is_manual_capture = packet.value_u32_1 > 0;
  if (g_scheduled_capture_paused && !is_manual_capture) {
    Serial.printf(
        "[camera-node] ignoring scheduled capture while paused request=%u\n",
        static_cast<unsigned int>(packet.request_id));
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kBusy, 0, 0);
    return;
  }

  if (g_capture_requested || g_capture_in_progress) {
    sendAck(mac_addr, command, packet.request_id, EspNowAckStatus::kBusy);
    return;
  }

  memcpy(g_capture_request_mac, mac_addr, sizeof(g_capture_request_mac));
  g_capture_request_id = packet.request_id;
  g_capture_command_id = packet.value_u32_1;
  g_capture_request_received_at_ms = millis();
  g_capture_request_has_sender = true;
  g_capture_requested = true;
}

bool setupEspNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("[camera-node] ESP-NOW init failed");
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_init_failed", "ESP-NOW init failed");
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
  Serial.printf(
      "[camera-node] capture start command_id=%lu request=%u queue_wait_ms=%lu\n",
      static_cast<unsigned long>(g_capture_command_id),
      static_cast<unsigned int>(g_capture_request_id),
      static_cast<unsigned long>(millis() - g_capture_request_received_at_ms));
  enterActiveCaptureMode();

  const bool success = captureAndUploadImage();
  const unsigned long capture_elapsed_ms = millis() - g_capture_request_received_at_ms;

  if (g_capture_request_has_sender) {
    constexpr uint8_t kCaptureCompletionSignalAttempts = 3;
    for (uint8_t attempt = 1; attempt <= kCaptureCompletionSignalAttempts; ++attempt) {
      if (success) {
        Serial.printf(
            "[camera-node] sending capture HEALTH command_id=%lu request=%u attempt=%u/%u after successful upload\n",
            static_cast<unsigned long>(g_capture_command_id),
            static_cast<unsigned int>(g_capture_request_id),
            static_cast<unsigned int>(attempt),
            static_cast<unsigned int>(kCaptureCompletionSignalAttempts));
        sendHealthReport(g_capture_request_mac, g_capture_request_id);
      }
      Serial.printf(
          "[camera-node] sending capture ACK command_id=%lu request=%u status=%s elapsed_ms=%lu attempt=%u/%u\n",
          static_cast<unsigned long>(g_capture_command_id),
          static_cast<unsigned int>(g_capture_request_id),
          success ? "ok" : "failed",
          static_cast<unsigned long>(capture_elapsed_ms),
          static_cast<unsigned int>(attempt),
          static_cast<unsigned int>(kCaptureCompletionSignalAttempts));
      sendAck(
          g_capture_request_mac,
          EspNowCommandType::kCaptureImage,
          g_capture_request_id,
          success ? EspNowAckStatus::kOk : EspNowAckStatus::kFailed,
          g_capture_command_id,
          capture_elapsed_ms);
      if (attempt < kCaptureCompletionSignalAttempts) {
        delay(120);
      }
    }
  }
  g_capture_request_has_sender = false;

  enterIdlePowerMode();
  g_capture_in_progress = false;
}

void serviceSerialCommands() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r' || c == '\n') {
      handleSerialCommandLine(g_serial_command_buffer);
      g_serial_command_buffer = "";
      continue;
    }
    if (g_serial_command_buffer.length() < 96) {
      g_serial_command_buffer += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  g_serial_command_buffer.reserve(96);

  Serial.println();
  Serial.println("=== PlantLab ESP32 Camera Platform Test ===");
  Serial.printf(
      "[camera-node] firmware_version=%s version_code=%d\n",
      kCameraSoftwareVersion,
      plantlab::kCameraSoftwareVersionCode);
  Serial.printf("[camera-node] hardware_device_id: %s\n", stableHardwareDeviceId().c_str());
  initReliabilityBootCounter();

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
  printSerialHelp();
  plantlab::time_sync::begin();
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

  serviceSerialCommands();
  maintainWiFiConnection();

  const unsigned long now = millis();
  plantlab::time_sync::service(g_wifi_ready, now);
  if (camera_node_runtime_config_complete(g_runtime_config) && g_wifi_ready) {
    registerDeviceNode();
  }
  if (platform_enabled() && g_wifi_ready && now - g_last_heartbeat_ms >= PLANTLAB_CAMERA_HEARTBEAT_INTERVAL_MS) {
    g_last_heartbeat_ms = now;
    sendHeartbeat();
  }
  serviceCommandPoll(now);
  if (
      g_ota_update_manager &&
      g_node_registered &&
      platform_enabled() &&
      g_wifi_ready &&
      !g_capture_requested &&
      !g_capture_in_progress &&
      !g_restart_scheduled) {
    g_ota_update_manager->service(now);
  }

  handleCaptureRequest();
  delay(2);
}
