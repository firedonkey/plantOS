#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_now.h>

#include <algorithm>
#include <memory>
#include <vector>

#include "actuators/light_controller.h"
#include "camera_capture_schedule.h"
#include "actuators/pump_controller.h"
#include "config.h"
#include "espnow_test_protocol.h"
#include "platform/platform_client.h"
#include "sensors/dht22_sensor.h"
#include "sensors/moisture_sensor.h"
#include "system/power_button.h"
#include "system/status_led.h"

namespace {
constexpr char kPreferencesNamespace[] = "plantlab";
constexpr char kConfigKeySsid[] = "wifi_ssid";
constexpr char kConfigKeyPassword[] = "wifi_pass";
constexpr char kConfigKeyClaimToken[] = "claim_token";
constexpr char kConfigKeyDeviceToken[] = "device_token";
constexpr char kConfigKeyPlatformDeviceId[] = "platform_id";
constexpr char kConfigKeyBackendUrl[] = "backend_url";
constexpr char kConfigKeyPlatformUrl[] = "platform_url";
constexpr char kProvisioningApName[] = "PlantLab-Setup";
constexpr char kSoftwareVersion[] = "0.1.0";
constexpr uint16_t kProvisioningPort = 8080;
constexpr uint32_t kReconnectRetryMs = 5000UL;
constexpr uint32_t kHttpTimeoutMs = 20000UL;
constexpr uint16_t kCameraProvisioningConfigVersion = 1;
constexpr uint16_t kDefaultCameraNodeIndex = 1;
constexpr uint32_t kCameraProvisioningRetryMs = 5000UL;

struct DeviceConfig {
  String wifi_ssid;
  String wifi_password;
  String claim_token;
  String device_token;
  String backend_url;
  String platform_url;
  int platform_device_id = 0;
};

struct WiFiNetworkOption {
  String ssid;
  int rssi = -127;
};

enum class DeviceMode {
  kBooting = 0,
  kProvisioning,
  kConnecting,
  kConnected,
  kWifiFailed,
};

Dht22Sensor g_dht22(PIN_DHT22_DATA);
MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
LightController g_growing_light(
    PIN_LIGHT_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PumpController g_pump(PIN_PUMP_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PowerButton g_power_button(
    PIN_POWER_BUTTON,
    POWER_BUTTON_ACTIVE_LEVEL,
    POWER_BUTTON_DEBOUNCE_MS,
    POWER_BUTTON_LONG_PRESS_MS);
StatusLed g_status_led(PIN_STATUS_LED, STATUS_LED_ON_LEVEL, STATUS_LED_OFF_LEVEL);
Preferences g_preferences;
WebServer g_web_server(kProvisioningPort);
std::unique_ptr<PlatformClient> g_platform_client;
MasterCaptureScheduleState g_camera_capture_schedule{};

DeviceConfig g_config;
DeviceMode g_device_mode = DeviceMode::kBooting;
unsigned long g_last_dht22_read_ms = 0;
unsigned long g_last_platform_send_ms = 0;
unsigned long g_last_platform_status_ms = 0;
unsigned long g_last_command_poll_ms = 0;
unsigned long g_last_wifi_attempt_ms = 0;
bool g_provisioning_mode = false;
bool g_wifi_ready = false;
bool g_web_routes_registered = false;
bool g_restart_scheduled = false;
unsigned long g_restart_at_ms = 0;
String g_pending_claim_token;
String g_pending_backend_url;
String g_pending_platform_url;
String g_pending_return_url;
std::vector<WiFiNetworkOption> g_cached_wifi_networks;
bool g_espnow_ready = false;
uint32_t g_next_espnow_request_id = 1;
MasterProvisioningSession g_camera_provisioning_session{};
bool g_camera_provisioning_ready = false;
unsigned long g_last_camera_provisioning_attempt_ms = 0;
constexpr uint8_t kEspNowBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

String html_escape(const String& value) {
  String escaped = value;
  escaped.replace("&", "&amp;");
  escaped.replace("<", "&lt;");
  escaped.replace(">", "&gt;");
  escaped.replace("\"", "&quot;");
  return escaped;
}

String js_string_escape(const String& value) {
  String escaped = value;
  escaped.replace("\\", "\\\\");
  escaped.replace("\"", "\\\"");
  escaped.replace("\n", "\\n");
  escaped.replace("\r", "\\r");
  return escaped;
}

String withNoImageExpectation(const String& return_url) {
  if (return_url.length() == 0) {
    return return_url;
  }
  if (return_url.indexOf("expect_image=") >= 0) {
    return return_url;
  }
  if (return_url.indexOf('?') >= 0) {
    return return_url + "&expect_image=0";
  }
  return return_url + "?expect_image=0";
}

bool hasWifiCredentials() {
  return g_config.wifi_ssid.length() > 0;
}

bool hasPendingClaim() {
  return g_config.claim_token.length() > 0;
}

bool hasRuntimeRegistration() {
  return g_config.platform_device_id > 0 && g_config.device_token.length() > 0;
}

String runtimePlatformUrl() {
  if (g_config.platform_url.length() > 0) {
    return g_config.platform_url;
  }
  return String(PLANTLAB_PLATFORM_URL);
}

String runtimeProvisioningUrl() {
  if (g_config.backend_url.length() > 0) {
    return g_config.backend_url;
  }
  return String(PLANTLAB_PROVISIONING_API_URL);
}

String stableHardwareDeviceId() {
  const uint64_t chip_id = ESP.getEfuseMac();
  char buffer[32];
  snprintf(
      buffer,
      sizeof(buffer),
      "pl-esp32-%04x%08x",
      static_cast<unsigned int>((chip_id >> 32) & 0xFFFF),
      static_cast<unsigned int>(chip_id & 0xFFFFFFFF));
  return String(buffer);
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

const char* espnowCommandToString(EspNowCommandType command) {
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

const char* espnowAckToString(EspNowAckStatus status) {
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

void rebuildPlatformClient() {
  g_platform_client.reset();
  if (!hasRuntimeRegistration()) {
    Serial.println("[platform] disabled: runtime registration is incomplete");
    return;
  }
  String platform_url = runtimePlatformUrl();
  platform_url.trim();
  if (platform_url.length() == 0) {
    Serial.println("[platform] disabled: platform URL is not configured");
    return;
  }

  g_platform_client.reset(
      new PlatformClient(platform_url.c_str(), g_config.platform_device_id, g_config.device_token.c_str()));
  Serial.printf("[platform] base_url: %s\n", g_platform_client->base_url().c_str());
  Serial.printf("[platform] device_id: %d\n", g_platform_client->device_id());
}

bool platform_enabled() {
  return g_platform_client != nullptr && g_platform_client->configured();
}

bool buildCameraProvisioningPayload(CameraProvisioningPayload* payload) {
  if (payload == nullptr || !hasWifiCredentials() || !hasRuntimeRegistration()) {
    return false;
  }
  String platform_url = runtimePlatformUrl();
  platform_url.trim();
  if (platform_url.length() == 0) {
    return false;
  }
  return espnow_build_provisioning_payload(
      payload,
      kCameraProvisioningConfigVersion,
      kDefaultCameraNodeIndex,
      static_cast<uint32_t>(g_config.platform_device_id),
      g_config.wifi_ssid.c_str(),
      g_config.wifi_password.c_str(),
      platform_url.c_str(),
      g_config.device_token.c_str());
}

void onEspNowDataSent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  if (status != ESP_NOW_SEND_SUCCESS) {
    Serial.printf(
        "[camera-schedule] ESP-NOW send failed status=%d target=%s\n",
        static_cast<int>(status),
        mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
  }
}

void onEspNowDataReceived(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    return;
  }

  if (static_cast<EspNowMessageKind>(packet.kind) != EspNowMessageKind::kAck) {
    return;
  }

  const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);

  if (command == EspNowCommandType::kProvisionStart &&
      espnow_handle_provisioning_ack(&g_camera_provisioning_session, mac_addr, packet)) {
    g_camera_provisioning_ready =
        g_camera_provisioning_session.state == MasterProvisioningState::kSucceeded;
    Serial.printf(
        "[camera-provisioning] ACK request=%u command=%s status=%s from %s\n",
        static_cast<unsigned int>(packet.request_id),
        espnowCommandToString(command),
        espnowAckToString(static_cast<EspNowAckStatus>(packet.ack_status)),
        mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
    return;
  }

  if (command != EspNowCommandType::kCaptureImage) {
    return;
  }

  Serial.printf(
      "[camera-schedule] ACK request=%u command=%s status=%s from %s\n",
      static_cast<unsigned int>(packet.request_id),
      espnowCommandToString(command),
      espnowAckToString(static_cast<EspNowAckStatus>(packet.ack_status)),
      mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
}

bool setupEspNow() {
  if (g_espnow_ready || !hasWifiCredentials() || g_provisioning_mode) {
    return g_espnow_ready;
  }

  if (esp_now_init() != ESP_OK) {
    Serial.println("[camera-schedule] ESP-NOW init failed");
    return false;
  }

  esp_now_register_send_cb(onEspNowDataSent);
  esp_now_register_recv_cb(onEspNowDataReceived);

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, kEspNowBroadcastMac, sizeof(kEspNowBroadcastMac));
  peer.channel = 0;
  peer.encrypt = false;
  if (!esp_now_is_peer_exist(kEspNowBroadcastMac)) {
    if (esp_now_add_peer(&peer) != ESP_OK) {
      Serial.println("[camera-schedule] failed to add broadcast ESP-NOW peer");
      esp_now_deinit();
      return false;
    }
  }

  g_espnow_ready = true;
  Serial.println("[camera-schedule] ESP-NOW ready");
  return true;
}

bool sendCameraProvisioningPacket(unsigned long now) {
  if (!g_espnow_ready || !espnow_should_send_provisioning_packet(g_camera_provisioning_session)) {
    return false;
  }

  EspNowPacket packet{};
  espnow_build_provisioning_packet(g_camera_provisioning_session, now, &packet);
  const esp_err_t err = esp_now_send(
      g_camera_provisioning_session.target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    Serial.printf("[camera-provisioning] provisioning send failed err=%d\n", static_cast<int>(err));
    return false;
  }

  espnow_mark_provisioning_packet_sent(&g_camera_provisioning_session, now);
  Serial.printf(
      "[camera-provisioning] request=%u sent camera_index=%u target=%s\n",
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned int>(g_camera_provisioning_session.payload.camera_node_index),
      macToString(g_camera_provisioning_session.target_mac).c_str());
  return true;
}

void serviceCameraProvisioning(unsigned long now) {
  const bool runtime_ready =
      g_espnow_ready && g_wifi_ready && platform_enabled() && !g_provisioning_mode;
  if (!runtime_ready || g_camera_provisioning_ready) {
    return;
  }

  espnow_update_provisioning_session(&g_camera_provisioning_session, now);
  if (g_camera_provisioning_session.state == MasterProvisioningState::kTimedOut ||
      g_camera_provisioning_session.state == MasterProvisioningState::kFailed) {
    g_camera_provisioning_session = MasterProvisioningSession{};
  }

  if (!g_camera_provisioning_session.active) {
    if (now - g_last_camera_provisioning_attempt_ms < kCameraProvisioningRetryMs) {
      return;
    }
    CameraProvisioningPayload payload{};
    if (!buildCameraProvisioningPayload(&payload)) {
      return;
    }
    espnow_start_provisioning_session(
        &g_camera_provisioning_session,
        kEspNowBroadcastMac,
        g_next_espnow_request_id++,
        payload,
        now,
        1500UL,
        3);
    g_last_camera_provisioning_attempt_ms = now;
  }

  sendCameraProvisioningPacket(now);
}

bool sendEspNowCaptureCommand(uint32_t now) {
  if (!g_espnow_ready) {
    return false;
  }

  EspNowPacket packet{};
  packet.magic = ESPNOW_TEST_MAGIC;
  packet.version = ESPNOW_TEST_VERSION;
  packet.kind = static_cast<uint8_t>(EspNowMessageKind::kCommand);
  packet.command = static_cast<uint8_t>(EspNowCommandType::kCaptureImage);
  packet.ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  packet.request_id = g_next_espnow_request_id++;
  packet.timestamp_ms = now;

  const esp_err_t err = esp_now_send(
      kEspNowBroadcastMac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    Serial.printf("[camera-schedule] capture send failed err=%d\n", static_cast<int>(err));
    return false;
  }

  capture_schedule_mark_requested(&g_camera_capture_schedule, now);
  Serial.printf(
      "[camera-schedule] capture request=%u sent interval_ms=%lu\n",
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned long>(g_camera_capture_schedule.interval_ms));
  return true;
}

void pollCameraCaptureSchedule(unsigned long now) {
  const bool runtime_ready =
      g_espnow_ready && g_wifi_ready && platform_enabled() && !g_provisioning_mode &&
      g_camera_provisioning_ready;
  if (!capture_schedule_should_request(g_camera_capture_schedule, now, runtime_ready)) {
    return;
  }
  sendEspNowCaptureCommand(now);
}

void updateStatusLed() {
  switch (g_device_mode) {
    case DeviceMode::kProvisioning:
      g_status_led.set_mode(StatusLedMode::kProvisioning);
      break;
    case DeviceMode::kConnecting:
      g_status_led.set_mode(StatusLedMode::kBooting);
      break;
    case DeviceMode::kConnected:
      g_status_led.set_mode(StatusLedMode::kNormal);
      break;
    case DeviceMode::kWifiFailed:
      g_status_led.set_mode(StatusLedMode::kOff);
      break;
    case DeviceMode::kBooting:
    default:
      g_status_led.set_mode(StatusLedMode::kBooting);
      break;
  }
}

bool loadConfig() {
  Serial.println("[provisioning] loading config from Preferences");
  g_preferences.begin(kPreferencesNamespace, true);
  g_config.wifi_ssid = g_preferences.getString(kConfigKeySsid, "");
  g_config.wifi_password = g_preferences.getString(kConfigKeyPassword, "");
  g_config.claim_token = g_preferences.getString(kConfigKeyClaimToken, "");
  g_config.device_token = g_preferences.getString(kConfigKeyDeviceToken, "");
  g_config.backend_url = g_preferences.getString(kConfigKeyBackendUrl, "");
  g_config.platform_url = g_preferences.getString(kConfigKeyPlatformUrl, "");
  g_config.platform_device_id = g_preferences.getInt(kConfigKeyPlatformDeviceId, 0);
  g_preferences.end();

  g_config.wifi_ssid.trim();
  g_config.claim_token.trim();
  g_config.device_token.trim();
  g_config.backend_url.trim();
  g_config.platform_url.trim();

  Serial.printf(
      "[provisioning] config loaded: ssid=%s claim=%s device_token=%s platform_id=%d backend=%s platform=%s\n",
      g_config.wifi_ssid.length() > 0 ? g_config.wifi_ssid.c_str() : "<empty>",
      g_config.claim_token.length() > 0 ? "<set>" : "<empty>",
      g_config.device_token.length() > 0 ? "<set>" : "<empty>",
      g_config.platform_device_id,
      g_config.backend_url.length() > 0 ? g_config.backend_url.c_str() : "<empty>",
      g_config.platform_url.length() > 0 ? g_config.platform_url.c_str() : "<empty>");

  rebuildPlatformClient();
  return hasWifiCredentials();
}

bool saveConfig() {
  g_config.wifi_ssid.trim();
  g_config.claim_token.trim();
  g_config.device_token.trim();
  g_config.backend_url.trim();
  g_config.platform_url.trim();

  Serial.println("[provisioning] saving config to Preferences");
  g_preferences.begin(kPreferencesNamespace, false);
  const size_t ssid_written = g_preferences.putString(kConfigKeySsid, g_config.wifi_ssid);
  g_preferences.putString(kConfigKeyPassword, g_config.wifi_password);
  g_preferences.putString(kConfigKeyClaimToken, g_config.claim_token);
  g_preferences.putString(kConfigKeyDeviceToken, g_config.device_token);
  g_preferences.putString(kConfigKeyBackendUrl, g_config.backend_url);
  g_preferences.putString(kConfigKeyPlatformUrl, g_config.platform_url);
  g_preferences.putInt(kConfigKeyPlatformDeviceId, g_config.platform_device_id);
  g_preferences.end();

  rebuildPlatformClient();
  if (ssid_written > 0 || g_config.wifi_ssid.isEmpty()) {
    Serial.println("[provisioning] config saved");
    return true;
  }
  Serial.println("[provisioning] failed to save config");
  return false;
}

void clearConfig() {
  Serial.println("[provisioning] clearing config from Preferences");
  g_preferences.begin(kPreferencesNamespace, false);
  g_preferences.clear();
  g_preferences.end();
  g_config = DeviceConfig{};
  g_platform_client.reset();
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_ready = false;
}

std::vector<WiFiNetworkOption> scanNearbyWifiNetworks() {
  std::vector<WiFiNetworkOption> networks;
  Serial.println("[provisioning] scanning nearby Wi-Fi before SoftAP");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, true);
  delay(200);

  const int network_count = WiFi.scanNetworks(false, true);
  if (network_count < 0) {
    Serial.printf("[provisioning] Wi-Fi scan failed: %d\n", network_count);
    WiFi.scanDelete();
    return networks;
  }

  for (int index = 0; index < network_count; ++index) {
    String ssid = WiFi.SSID(index);
    ssid.trim();
    if (ssid.length() == 0) {
      continue;
    }
    const int rssi = WiFi.RSSI(index);
    auto existing = std::find_if(
        networks.begin(),
        networks.end(),
        [&ssid](const WiFiNetworkOption& network) { return network.ssid == ssid; });
    if (existing == networks.end()) {
      WiFiNetworkOption network;
      network.ssid = ssid;
      network.rssi = rssi;
      networks.push_back(network);
    } else if (rssi > existing->rssi) {
      existing->rssi = rssi;
    }
  }
  WiFi.scanDelete();
  std::sort(
      networks.begin(),
      networks.end(),
      [](const WiFiNetworkOption& left, const WiFiNetworkOption& right) {
        if (left.rssi == right.rssi) {
          return left.ssid < right.ssid;
        }
        return left.rssi > right.rssi;
      });
  Serial.printf("[provisioning] captured %u nearby network(s)\n", static_cast<unsigned>(networks.size()));
  return networks;
}

String wifiOptionsHtml() {
  String options = "<option value=\"\">Select nearby Wi-Fi</option>";
  for (const WiFiNetworkOption& network : g_cached_wifi_networks) {
    options += "<option value=\"" + html_escape(network.ssid) + "\">" + html_escape(network.ssid) + "</option>";
  }
  options += "<option value=\"__manual__\">My Wi-Fi is not listed</option>";
  return options;
}

String connectingPageHtml(const String& return_url) {
  const String effective_return_url = withNoImageExpectation(return_url);
  String html = R"HTML(
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PlantLab Setup</title>
    <style>
      :root{color-scheme:light;--green:#2f7d4b;--text:#17201a;--muted:#566259;--line:#d9e1d8;--soft:#f6f8f4;}
      *{box-sizing:border-box;} body{margin:0;background:var(--soft);color:var(--text);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
      main{width:min(520px,calc(100% - 32px));margin:0 auto;padding:42px 0;}
      .card{border:1px solid var(--line);border-radius:8px;padding:24px;background:#fff;box-shadow:0 16px 40px rgba(23,32,26,0.07);}
      .eyebrow{margin:0 0 8px;color:var(--green);font-size:.78rem;font-weight:850;text-transform:uppercase;}
      h1{margin:0 0 10px;font-size:2rem;} p{color:var(--muted);line-height:1.55;}
      .connecting-view{display:grid;gap:18px;}
      .connecting-hero{display:grid;gap:18px;margin-top:12px;padding:18px;border:1px solid var(--line);border-radius:8px;background:linear-gradient(180deg,#f9fbf8 0%,#f3f8f3 100%);}
      .connecting-hero-topline{display:flex;align-items:center;gap:12px;}
      .connecting-spinner{width:18px;height:18px;border-radius:999px;border:2px solid rgba(47,125,75,.18);border-top-color:var(--green);animation:spin .95s linear infinite;}
      .connecting-signal{display:grid;grid-template-columns:72px 1fr 72px;align-items:center;gap:14px;}
      .connecting-node{display:grid;justify-items:center;gap:8px;}
      .connecting-node-badge{display:grid;place-items:center;width:52px;height:52px;border:1px solid #cfe0d2;border-radius:8px;background:#fff;color:var(--green);font-size:1.35rem;}
      .connecting-node-label{color:var(--muted);font-size:.9rem;font-weight:700;}
      .connecting-wave{position:relative;height:12px;border-radius:999px;background:#e3ebe3;overflow:hidden;}
      .connecting-wave::before{content:"";position:absolute;inset:0 auto 0 -32%;width:32%;border-radius:inherit;background:linear-gradient(90deg,rgba(47,125,75,.08),rgba(47,125,75,.8),rgba(47,125,75,.08));animation:wave 1.8s ease-in-out infinite;}
      .connecting-checklist{display:grid;gap:12px;margin:0;padding:0;list-style:none;}
      .connecting-check{display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#f9fbf8;}
      .connecting-check-dot{width:12px;height:12px;border-radius:999px;background:#c8d2c8;}
      .status{display:block;margin-top:16px;border:1px solid #b8d8c0;border-radius:8px;padding:12px;background:#eff9f1;color:var(--green);font-weight:700;}
      @keyframes spin{to{transform:rotate(360deg);}} @keyframes wave{0%{transform:translateX(0);}100%{transform:translateX(430%);}}
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <div class="connecting-view" aria-live="polite">
          <p class="eyebrow">Setup</p>
          <h1>Connecting your PlantLab</h1>
          <p>Your device is leaving setup mode, joining your Wi‑Fi, and reopening PlantLab as soon as it is ready.</p>
          <div class="connecting-hero" aria-hidden="true">
            <div class="connecting-hero-topline"><span class="connecting-spinner"></span><strong>Reconnecting and syncing</strong></div>
            <div class="connecting-signal">
              <div class="connecting-node"><div class="connecting-node-badge">PL</div><div class="connecting-node-label">Device</div></div>
              <div class="connecting-wave"></div>
              <div class="connecting-node"><div class="connecting-node-badge">☁</div><div class="connecting-node-label">PlantLab</div></div>
            </div>
          </div>
          <ul class="connecting-checklist">
            <li class="connecting-check"><span class="connecting-check-dot"></span><div><strong>Joining your Wi‑Fi</strong><span>PlantLab is switching from setup mode back to your home network.</span></div></li>
            <li class="connecting-check"><span class="connecting-check-dot"></span><div><strong>Reopening your dashboard</strong><span>The next page will open automatically when your browser can reach PlantLab again.</span></div></li>
          </ul>
          <div class="status">Setup saved. PlantLab is reconnecting to your Wi‑Fi and will reopen the dashboard when it is ready.</div>
        </div>
      </div>
    </main>
    <script>
      const returnUrl = "__RETURN_URL__";
      async function waitForPlantLab() {
        if (!returnUrl) {
          return;
        }
        try {
          await fetch(returnUrl, {
            cache: "no-store",
            mode: "no-cors",
            credentials: "include",
          });
          window.location.replace(returnUrl);
          return;
        } catch (_error) {}
        setTimeout(waitForPlantLab, 1500);
      }
      setTimeout(waitForPlantLab, 2000);
    </script>
  </body>
</html>)HTML";
  html.replace("__RETURN_URL__", js_string_escape(effective_return_url));
  return html;
}

String provisioningPageHtml(
    const String& claim_token,
    const String& return_url,
    const String& backend_url,
    const String& platform_url,
    const String& notice = "",
    bool is_error = false) {
  const bool has_setup_code = claim_token.length() > 0;
  String effective_backend_url = backend_url.length() > 0 ? backend_url : runtimeProvisioningUrl();
  String effective_platform_url = platform_url.length() > 0 ? platform_url : runtimePlatformUrl();
  effective_backend_url.trim();
  effective_platform_url.trim();
  const bool has_platform = effective_platform_url.length() > 0;
  const bool setup_ready = has_setup_code && has_platform;
  const String notice_block = notice.length() == 0
                                  ? ""
                                  : String("<p style=\"padding:12px 14px;border-radius:8px;border:1px solid ") +
                                        (is_error ? "#ef4444;background:#fef2f2;color:#991b1b;"
                                                  : "#86efac;background:#f0fdf4;color:#166534;") +
                                        "\">" + html_escape(notice) + "</p>";
  String setup_warning = "";
  if (!has_setup_code) {
    setup_warning =
        "<small style=\"margin-top:14px;color:#9b332b;display:block;\">This setup page needs a valid Add Device session from PlantLab. Go back to the website, click Add device, and continue from there.</small>";
  } else if (!has_platform) {
    setup_warning =
        "<small style=\"margin-top:14px;color:#9b332b;display:block;\">PlantLab setup details are incomplete. Restart Add device, or update the firmware default for the platform URL.</small>";
  }
  String html = R"HTML(
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PlantLab Setup</title>
    <style>
      :root{color-scheme:light;--green:#2f7d4b;--text:#17201a;--muted:#566259;--line:#d9e1d8;--soft:#f6f8f4;--error:#9b332b;}
      *{box-sizing:border-box;} body{margin:0;background:var(--soft);color:var(--text);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
      main{width:min(520px,calc(100% - 32px));margin:0 auto;padding:42px 0;}
      .card{border:1px solid var(--line);border-radius:8px;padding:24px;background:#fff;box-shadow:0 16px 40px rgba(23,32,26,0.07);}
      .eyebrow{margin:0 0 8px;color:var(--green);font-size:.78rem;font-weight:850;text-transform:uppercase;}
      h1{margin:0 0 10px;font-size:2rem;} p{color:var(--muted);line-height:1.55;}
      label{display:grid;gap:8px;margin-top:16px;font-weight:700;}
      input,select{width:100%;min-height:42px;border:1px solid #cfd8cf;border-radius:8px;padding:8px 10px;font:inherit;background:#fff;}
      input:focus,select:focus{outline:2px solid rgba(47,125,75,.22);border-color:var(--green);}
      .password-row{display:grid;grid-template-columns:1fr auto;gap:8px;}
      .secondary-button{min-height:42px;border:1px solid #cfd8cf;border-radius:8px;padding:8px 10px;background:#fff;color:var(--text);font:inherit;font-weight:750;}
      button{cursor:pointer;}
      .submit-button{width:100%;min-height:44px;margin-top:20px;border:1px solid var(--green);border-radius:8px;background:var(--green);color:#fff;font:inherit;font-weight:800;}
      .submit-button:disabled{cursor:not-allowed;opacity:.45;}
      .manual-ssid{display:none;}
      .manual-ssid.visible{display:block;}
      .hint{margin-top:18px;font-size:.92rem;}
      .status{display:none;margin-top:16px;border:1px solid var(--line);border-radius:8px;padding:12px;background:#f7faf6;color:var(--muted);font-weight:700;}
      .status.visible{display:block;} .status.success{border-color:#b8d8c0;background:#eff9f1;color:var(--green);} .status.error{border-color:#e0b0aa;background:#fff2f1;color:var(--error);}
      .connecting-view{display:none;gap:18px;} .connecting-view.visible{display:grid;}
      .connecting-hero{display:grid;gap:18px;margin-top:12px;padding:18px;border:1px solid var(--line);border-radius:8px;background:linear-gradient(180deg,#f9fbf8 0%,#f3f8f3 100%);}
      .connecting-hero-topline{display:flex;align-items:center;gap:12px;}
      .connecting-spinner{width:18px;height:18px;border-radius:999px;border:2px solid rgba(47,125,75,.18);border-top-color:var(--green);animation:spin .95s linear infinite;}
      .connecting-signal{display:grid;grid-template-columns:72px 1fr 72px;align-items:center;gap:14px;}
      .connecting-node{display:grid;justify-items:center;gap:8px;}
      .connecting-node-badge{display:grid;place-items:center;width:52px;height:52px;border:1px solid #cfe0d2;border-radius:8px;background:#fff;color:var(--green);font-size:1.35rem;}
      .connecting-node-label{color:var(--muted);font-size:.9rem;font-weight:700;}
      .connecting-wave{position:relative;height:12px;border-radius:999px;background:#e3ebe3;overflow:hidden;}
      .connecting-wave::before{content:"";position:absolute;inset:0 auto 0 -32%;width:32%;border-radius:inherit;background:linear-gradient(90deg,rgba(47,125,75,.08),rgba(47,125,75,.8),rgba(47,125,75,.08));animation:wave 1.8s ease-in-out infinite;}
      .connecting-checklist{display:grid;gap:12px;margin:0;padding:0;list-style:none;}
      .connecting-check{display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#f9fbf8;}
      .connecting-check-dot{width:12px;height:12px;border-radius:999px;background:#c8d2c8;}
      @keyframes spin{to{transform:rotate(360deg);}} @keyframes wave{0%{transform:translateX(0);}100%{transform:translateX(430%);}}
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <div id="setup-form-view">
          <p class="eyebrow">PlantLab Local Setup</p>
          <h1>PlantLab Setup</h1>
          <p>Connect this device to your home Wi-Fi and add it to your PlantLab account.</p>
          <p>Enter your Wi-Fi details to finish setup.</p>
          __NOTICE_BLOCK__
          <form id="provision-form" method="post" action="/save" novalidate>
            <label>Wi-Fi SSID
              <select id="ssid-select" name="ssid_select">__WIFI_OPTIONS__</select>
              <input class="manual-ssid" id="ssid" name="ssid" autocomplete="off" placeholder="Type Wi-Fi name">
            </label>
            <label>Wi-Fi password
              <div class="password-row">
                <input id="password" name="password" type="password" autocomplete="current-password" placeholder="Leave empty for open Wi-Fi">
                <button class="secondary-button" id="toggle-password" type="button">Show</button>
              </div>
            </label>
            <input id="resolved-ssid" name="wifi_ssid" type="hidden" value="">
            <button class="submit-button" id="submit-button" type="submit" __DISABLED_ATTR__>Save and connect</button>
          </form>
          __SETUP_WARNING__
          <div class="status" id="status" role="status" aria-live="polite"></div>
          <p class="hint">After submitting, the device will leave setup mode and try to join your Wi-Fi.</p>
        </div>
      </div>
    </main>
    <script>
      const form=document.querySelector("#provision-form");
      const ssidInput=document.querySelector("#ssid");
      const ssidSelect=document.querySelector("#ssid-select");
      const resolvedSsidInput=document.querySelector("#resolved-ssid");
      const passwordInput=document.querySelector("#password");
      const togglePasswordButton=document.querySelector("#toggle-password");
      const submitButton=document.querySelector("#submit-button");
      const statusBox=document.querySelector("#status");
      function selectedSsid(){return ssidSelect.value==="__manual__"?ssidInput.value.trim():ssidSelect.value.trim();}
      function updateSsidMode(){const manual=ssidSelect.value==="__manual__";ssidInput.classList.toggle("visible",manual);ssidInput.required=manual;if(!manual){ssidInput.value="";}}
      function setStatus(message,type="info"){statusBox.textContent=message;statusBox.className=`status visible ${type}`;}
      function clearStatus(){statusBox.textContent="";statusBox.className="status";}
      function validateForm(){if(!selectedSsid()){return "Enter your home Wi-Fi name.";} return "";}
      ssidSelect.addEventListener("change",updateSsidMode);
      togglePasswordButton.addEventListener("click",()=>{const show=passwordInput.type==="password"; passwordInput.type=show?"text":"password"; togglePasswordButton.textContent=show?"Hide":"Show";});
      form.addEventListener("submit", (event)=>{clearStatus(); const error=validateForm(); if(error){event.preventDefault(); setStatus(error,"error"); return;} resolvedSsidInput.value=selectedSsid(); submitButton.disabled=true;});
      updateSsidMode();
    </script>
  </body>
</html>)HTML";

  html.replace("__NOTICE_BLOCK__", notice_block);
  html.replace("__WIFI_OPTIONS__", wifiOptionsHtml());
  html.replace("__CLAIM_TOKEN__", html_escape(claim_token));
  html.replace("__BACKEND_URL__", html_escape(effective_backend_url));
  html.replace("__PLATFORM_URL__", html_escape(effective_platform_url));
  html.replace("__RETURN_URL__", html_escape(return_url));
  html.replace("__DISABLED_ATTR__", setup_ready ? "" : "disabled");
  html.replace("__SETUP_WARNING__", setup_ready ? "" : setup_warning);
  return html;
}

void handleProvisioningSubmit() {
  Serial.println("[provisioning] received setup form submission");
  const String wifi_ssid = g_web_server.arg("wifi_ssid");
  const String ssid = wifi_ssid.length() > 0 ? wifi_ssid : g_web_server.arg("ssid");
  const String wifi_password = g_web_server.arg("wifi_password");
  const String password = wifi_password.length() > 0 ? wifi_password : g_web_server.arg("password");
  const String claim_token = g_pending_claim_token;
  const String backend_url = g_pending_backend_url;
  const String platform_url = g_pending_platform_url;
  const String return_url = g_pending_return_url;

  if (ssid.length() == 0 || claim_token.length() == 0 || platform_url.length() == 0) {
    Serial.println("[provisioning] submission rejected: Wi-Fi SSID, setup code, or platform URL missing");
    g_web_server.send(400, "text/plain", "Wi-Fi SSID, setup code, and platform URL are required.");
    return;
  }

  g_config.wifi_ssid = ssid;
  g_config.wifi_password = password;
  g_config.claim_token = claim_token;
  g_config.backend_url = backend_url;
  g_config.platform_url = platform_url;
  g_config.device_token = "";
  g_config.platform_device_id = 0;

  if (!saveConfig()) {
    g_web_server.send(500, "text/plain", "Failed to save configuration.");
    return;
  }
  g_web_server.send(200, "text/html", connectingPageHtml(return_url));
  g_restart_scheduled = true;
  g_restart_at_ms = millis() + 5000UL;
  Serial.println("[provisioning] saved Wi-Fi and setup code, reboot scheduled");
}

void startProvisioningMode() {
  if (g_provisioning_mode) {
    return;
  }

  Serial.println("[provisioning] entering provisioning mode");
  g_provisioning_mode = true;
  g_wifi_ready = false;
  g_device_mode = DeviceMode::kProvisioning;
  updateStatusLed();

  g_cached_wifi_networks = scanNearbyWifiNetworks();
  WiFi.disconnect(true, true);
  delay(200);
  WiFi.mode(WIFI_AP);

  const IPAddress ap_ip(10, 42, 0, 1);
  const IPAddress ap_gateway(10, 42, 0, 1);
  const IPAddress ap_subnet(255, 255, 255, 0);
  if (!WiFi.softAPConfig(ap_ip, ap_gateway, ap_subnet)) {
    Serial.println("[provisioning] warning: failed to apply SoftAP IP config, using ESP32 default");
  }

  if (!g_web_routes_registered) {
    g_web_server.on("/", HTTP_GET, []() {
      const String setup_code = g_web_server.arg("setup_code");
      const String return_url = withNoImageExpectation(g_web_server.arg("return_url"));
      const String backend_url = g_web_server.arg("backend_url");
      const String platform_url = g_web_server.arg("platform_url");
      if (setup_code.length() > 0) {
        g_pending_claim_token = setup_code;
      }
      if (return_url.length() > 0) {
        g_pending_return_url = return_url;
      }
      if (backend_url.length() > 0) {
        g_pending_backend_url = backend_url;
      }
      if (platform_url.length() > 0) {
        g_pending_platform_url = platform_url;
      }
      g_web_server.send(
          200,
          "text/html",
          provisioningPageHtml(
              g_pending_claim_token,
              g_pending_return_url,
              g_pending_backend_url,
              g_pending_platform_url));
    });
    g_web_server.on("/save", HTTP_POST, handleProvisioningSubmit);
    g_web_routes_registered = true;
  }

  const bool ap_ok = WiFi.softAP(kProvisioningApName);
  if (ap_ok) {
    Serial.printf("[provisioning] SoftAP started: %s\n", kProvisioningApName);
    Serial.printf("[provisioning] AP IP: %s\n", WiFi.softAPIP().toString().c_str());
  } else {
    Serial.println("[provisioning] failed to start SoftAP");
  }

  g_web_server.begin();
  Serial.printf(
      "[provisioning] web server listening on http://%s:%u/\n",
      WiFi.softAPIP().toString().c_str(),
      kProvisioningPort);
}

bool connectToWiFi() {
  if (!hasWifiCredentials() || g_provisioning_mode) {
    return false;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!g_wifi_ready) {
      g_wifi_ready = true;
      g_device_mode = DeviceMode::kConnected;
      updateStatusLed();
      Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    return true;
  }

  const unsigned long now = millis();
  if (now - g_last_wifi_attempt_ms < kReconnectRetryMs) {
    return false;
  }

  g_last_wifi_attempt_ms = now;
  g_wifi_ready = false;
  g_device_mode = DeviceMode::kConnecting;
  updateStatusLed();

  Serial.printf("[wifi] connecting to %s\n", g_config.wifi_ssid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(g_config.wifi_ssid.c_str(), g_config.wifi_password.c_str());

  const unsigned long started_at = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started_at < PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    g_status_led.update(millis());
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    g_wifi_ready = true;
    g_device_mode = DeviceMode::kConnected;
    updateStatusLed();
    Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
    return true;
  }

  WiFi.disconnect();
  g_device_mode = DeviceMode::kWifiFailed;
  updateStatusLed();
  Serial.println("[wifi] connect timed out");
  return false;
}

bool registerProvisionedDevice() {
  if (!hasPendingClaim()) {
    return hasRuntimeRegistration();
  }
  String platform_url = runtimePlatformUrl();
  platform_url.trim();
  if (platform_url.length() == 0) {
    Serial.println("[provisioning] cannot register: platform URL is not configured");
    return false;
  }

  Serial.println("[provisioning] registering device with setup code");
  StaticJsonDocument<384> payload;
  payload["device_id"] = stableHardwareDeviceId();
  payload["claim_token"] = g_config.claim_token;
  payload["node_role"] = "master";
  payload["display_name"] = "Master";
  payload["hardware_model"] = "esp32_master";
  payload["hardware_version"] = BOARD_NAME;
  payload["software_version"] = kSoftwareVersion;
  JsonObject capabilities = payload.createNestedObject("capabilities");
  capabilities["camera"] = false;
  capabilities["pump"] = true;
  capabilities["moisture_sensor"] = true;
  capabilities["light_control"] = true;
  capabilities["temperature_sensor"] = true;
  capabilities["humidity_sensor"] = true;

  String body;
  serializeJson(payload, body);

  HTTPClient http;
  http.setTimeout(kHttpTimeoutMs);
  const String url = platform_url + "/api/devices/register-provisioned";
  if (!http.begin(url)) {
    Serial.println("[provisioning] register request setup failed");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  const int status_code = http.POST(body);
  const String response_body = status_code > 0 ? http.getString() : http.errorToString(status_code);
  http.end();

  if (status_code < 200 || status_code >= 300) {
    Serial.printf("[provisioning] registration failed HTTP %d: %s\n", status_code, response_body.c_str());
    return false;
  }

  DynamicJsonDocument response(1024);
  const DeserializationError json_error = deserializeJson(response, response_body);
  if (json_error) {
    Serial.println("[provisioning] registration response JSON parse failed");
    return false;
  }

  const int platform_device_id = response["platform_device_id"] | 0;
  const char* device_access_token = response["device_access_token"] | "";
  if (platform_device_id <= 0 || String(device_access_token).length() == 0) {
    Serial.println("[provisioning] registration response missing platform device id or device token");
    return false;
  }

  g_config.platform_device_id = platform_device_id;
  g_config.device_token = String(device_access_token);
  g_config.claim_token = "";
  saveConfig();
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_ready = false;
  Serial.printf("[provisioning] registration complete, platform_device_id=%d\n", g_config.platform_device_id);
  return true;
}

void checkProvisioningButton() {
  const PowerButtonEvent event = g_power_button.update(millis());
  if (event == PowerButtonEvent::kLongPress && !g_provisioning_mode) {
    Serial.println("[button] long press detected -> provisioning mode");
    g_config.claim_token = "";
    g_config.device_token = "";
    g_config.platform_device_id = 0;
    g_camera_provisioning_session = MasterProvisioningSession{};
    g_camera_provisioning_ready = false;
    saveConfig();
    startProvisioningMode();
    return;
  }
}
}  // namespace

PlatformReading read_platform_reading() {
  const Dht22Reading reading = g_dht22.read();
  const MoistureReading moisture = g_moisture.read();

  if (!reading.valid) {
    Serial.println("[dht22] read failed (NaN)");
  } else {
    Serial.printf(
        "[dht22] temp_c=%.1f humidity=%.1f%%\n",
        reading.temperature_c,
        reading.humidity_percent);
  }

  if (!moisture.valid) {
    Serial.println("[moisture] read failed");
  } else {
    Serial.printf(
        "[moisture] raw=%d percent=%.1f%%\n",
        moisture.raw_adc,
        moisture.moisture_percent);
  }

  Serial.printf(
      "[actuators] growing_light=%s pump=%s\n",
      g_growing_light.is_on() ? "on" : "off",
      g_pump.is_on() ? "on" : "off");

  PlatformReading platform_reading{};
  platform_reading.hardware_device_id = stableHardwareDeviceId();
  platform_reading.temperature_c = reading.temperature_c;
  platform_reading.humidity_percent = reading.humidity_percent;
  platform_reading.moisture_percent = moisture.moisture_percent;
  platform_reading.temperature_valid = reading.valid;
  platform_reading.humidity_valid = reading.valid;
  platform_reading.moisture_valid = moisture.valid;
  platform_reading.light_on = g_growing_light.is_on();
  platform_reading.pump_on = g_pump.is_on();
  platform_reading.pump_status = g_pump.is_on() ? "running" : "idle";
  return platform_reading;
}

PlatformStatus platform_status(const String& message) {
  PlatformStatus status{};
  status.light_on = g_growing_light.is_on();
  status.pump_on = g_pump.is_on();
  status.message = message;
  return status;
}

void send_platform_reading(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_platform_send_ms < PLANTLAB_SENSOR_SEND_INTERVAL_MS) {
    return;
  }
  g_last_platform_send_ms = now;

  const PlatformReading reading = read_platform_reading();
  String error;
  if (g_platform_client->send_reading(reading, &error)) {
    Serial.printf(
        "[platform] reading sent to %s/api/data (device_id=%d)\n",
        g_platform_client->base_url().c_str(),
        g_platform_client->device_id());
  } else {
    Serial.printf("[platform] reading upload failed: %s\n", error.c_str());
  }
}

void send_platform_status(unsigned long now, const String& message = "online") {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_platform_status_ms < PLANTLAB_STATUS_INTERVAL_MS) {
    return;
  }
  g_last_platform_status_ms = now;

  String error;
  if (!g_platform_client->send_status(platform_status(message), &error)) {
    Serial.printf("[platform] status upload failed: %s\n", error.c_str());
  }
}

void execute_platform_command(const PlatformCommand& command) {
  String message;
  bool success = true;

  if (command.target == "light") {
    if (command.action == "on") {
      g_growing_light.set_on(true);
      message = "growing light turned on";
    } else if (command.action == "off") {
      g_growing_light.set_on(false);
      message = "growing light turned off";
    } else {
      success = false;
      message = "unsupported growing light command";
    }
  } else if (command.target == "pump") {
    if (command.action == "run") {
      const unsigned long seconds =
          command.value.length() > 0 ? static_cast<unsigned long>(command.value.toInt()) : 5UL;
      g_pump.start_for_ms(seconds * 1000UL);
      message = "pump started for " + String(seconds) + " seconds";
    } else if (command.action == "off") {
      g_pump.stop();
      message = "pump turned off";
    } else {
      success = false;
      message = "unsupported pump command";
    }
  } else {
    success = false;
    message = "unsupported command target";
  }

  String status_error;
  g_platform_client->send_status(platform_status(message), &status_error);
  String ack_error;
  if (!g_platform_client->acknowledge_command(
          command.id,
          success ? "completed" : "failed",
          message.c_str(),
          g_growing_light.is_on(),
          g_pump.is_on(),
          &ack_error)) {
    Serial.printf("[platform] command ack failed: %s\n", ack_error.c_str());
  } else {
    Serial.printf("[platform] command %d handled: %s\n", command.id, message.c_str());
  }
}

void poll_platform_commands(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready || now - g_last_command_poll_ms < PLANTLAB_COMMAND_POLL_INTERVAL_MS) {
    return;
  }
  g_last_command_poll_ms = now;

  PlatformCommand commands[4]{};
  String error;
  const int count = g_platform_client->poll_pending_commands(commands, 4, &error);
  if (count < 0) {
    Serial.printf("[platform] command poll failed: %s\n", error.c_str());
    return;
  }

  for (int i = 0; i < count; ++i) {
    if (!commands[i].valid) {
      continue;
    }
    execute_platform_command(commands[i]);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab ESP32 Master Node ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf("Provisioning env: %s\n", PLANTLAB_ENV_LABEL);
  Serial.printf("DHT22 pin: GPIO%d\n", PIN_DHT22_DATA);
  Serial.printf("Moisture ADC pin: GPIO%d\n", PIN_SOIL_MOISTURE_ADC);
  Serial.printf("Growing light gate pin: GPIO%d\n", PIN_LIGHT_MOSFET_GATE);
  Serial.printf("Pump gate pin: GPIO%d\n", PIN_PUMP_MOSFET_GATE);
  Serial.printf("Provisioning button pin: GPIO%d\n", PIN_POWER_BUTTON);
  Serial.printf("Status LED pin: GPIO%d\n", PIN_STATUS_LED);
  if (String(PLANTLAB_PLATFORM_URL).length() > 0) {
    Serial.printf("Fallback platform URL: %s\n", PLANTLAB_PLATFORM_URL);
  }
  if (String(PLANTLAB_PROVISIONING_API_URL).length() > 0) {
    Serial.printf("Fallback provisioning URL: %s\n", PLANTLAB_PROVISIONING_API_URL);
  }
  Serial.printf(
      "Camera capture schedule: %s (%lu ms)\n",
      PLANTLAB_CAMERA_CAPTURE_ENABLED ? "enabled" : "disabled",
      static_cast<unsigned long>(PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS));

  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_POWER_BUTTON, INPUT_PULLUP);

  g_status_led.begin();
  g_power_button.begin();
  g_status_led.set_mode(StatusLedMode::kBooting);
  g_dht22.begin();
  g_moisture.begin();
  g_growing_light.begin();
  g_pump.begin();

  Serial.println("[dht22] sensor initialized");
  Serial.println("[moisture] sensor initialized");
  Serial.println("[growing-light] initialized OFF");
  Serial.println("[pump] initialized OFF");
  capture_schedule_init(
      &g_camera_capture_schedule,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0,
      PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS);

  loadConfig();
  if (hasWifiCredentials()) {
    Serial.println("[provisioning] saved Wi-Fi config found, connecting to Wi-Fi");
    connectToWiFi();
  } else {
    Serial.println("[provisioning] no saved Wi-Fi config, starting provisioning mode");
    startProvisioningMode();
  }
}

void loop() {
  const unsigned long now = millis();
  checkProvisioningButton();
  g_status_led.update(now);
  g_pump.update();

  if (g_provisioning_mode) {
    g_web_server.handleClient();
    if (g_restart_scheduled && static_cast<long>(now - g_restart_at_ms) >= 0) {
      Serial.println("[provisioning] rebooting ESP32");
      delay(100);
      ESP.restart();
    }
    return;
  }

  connectToWiFi();
  if (g_wifi_ready) {
    setupEspNow();
  }

  if (g_wifi_ready && hasPendingClaim()) {
    if (registerProvisionedDevice()) {
      rebuildPlatformClient();
    }
  }

  if (platform_enabled()) {
    serviceCameraProvisioning(now);
    pollCameraCaptureSchedule(now);
    poll_platform_commands(now);
    send_platform_status(now);
    send_platform_reading(now);
  }

  if (now - g_last_dht22_read_ms >= DHT22_READ_INTERVAL_MS) {
    g_last_dht22_read_ms = now;
    if (!platform_enabled()) {
      read_platform_reading();
    }
  }
}
