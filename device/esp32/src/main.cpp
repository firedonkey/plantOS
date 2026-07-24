#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>

#include <algorithm>
#include <cstdio>
#include <memory>
#include <vector>

#include "actuators/light_controller.h"
#include "camera_capture_schedule.h"
#include "actuators/pump_controller.h"
#include "config.h"
#include "contracts/command_dispatcher.h"
#include "contracts/plantlab_contracts.h"
#include "espnow_test_protocol.h"
#include "firmware_version.h"
#include "ambient_led_belt/ambient_led_belt_controller.h"
#include "ambient_led_belt/ambient_led_belt_fastled_transport.h"
#include "ota/ota_update_manager.h"
#include "platform/platform_client.h"
#include "provisioning/ble_provisioning.h"
#include "provisioning/wifi_networks_payload.h"
#include "sensors/i2c_environment_sensors.h"
#include "sensors/moisture_sensor.h"
#include "sensors/water_level_sensor.h"
#include "system/power_button.h"
#include "system/status_led.h"
#include "time/time_sync_manager.h"

bool reportPlatformCommandResult(
    const PlatformCommand& command,
    const char* status,
    const char* message,
    const char* error_code = nullptr);
bool reportPendingCaptureCommandResult(
    const char* status,
    const char* message,
    const char* error_code = nullptr);

namespace {
constexpr char kPreferencesNamespace[] = "plantlab";
constexpr char kConfigKeySsid[] = "wifi_ssid";
constexpr char kConfigKeyPassword[] = "wifi_pass";
constexpr char kConfigKeyClaimToken[] = "claim_token";
constexpr char kConfigKeyDeviceToken[] = "device_token";
constexpr char kConfigKeyPlatformDeviceId[] = "platform_id";
constexpr char kConfigKeyBackendUrl[] = "backend_url";
constexpr char kConfigKeyPlatformUrl[] = "platform_url";
constexpr char kConfigKeyPendingSsid[] = "pend_ssid";
constexpr char kConfigKeyPendingPassword[] = "pend_pass";
constexpr char kConfigKeyPendingClaimToken[] = "pend_claim";
constexpr char kConfigKeyPendingBackendUrl[] = "pend_backend";
constexpr char kConfigKeyPendingPlatformUrl[] = "pend_plat";
constexpr char kConfigKeyPendingAttachDeviceId[] = "pend_attach";
constexpr char kConfigKeyBootCounter[] = "boot_count";
constexpr char kConfigKeyAmbientLedBeltLogicalCount[] = "amb_led_log";
constexpr char kConfigKeyAmbientLedBeltColorOrder[] = "amb_led_ord";
constexpr char kConfigKeyAmbientLedBeltMaxBrightness[] = "amb_led_max";
constexpr char kConfigKeyAmbientLedBeltDefaultBrightness[] = "amb_led_def";
constexpr char kConfigKeyWaterLevelCalibrationVersion[] = "wl_cal_ver";
constexpr char kConfigKeyWaterLevelTopDry[] = "wl_t_dry";
constexpr char kConfigKeyWaterLevelTopWet[] = "wl_t_wet";
constexpr char kConfigKeyWaterLevelMiddleDry[] = "wl_m_dry";
constexpr char kConfigKeyWaterLevelMiddleWet[] = "wl_m_wet";
constexpr char kConfigKeyWaterLevelBottomDry[] = "wl_b_dry";
constexpr char kConfigKeyWaterLevelBottomWet[] = "wl_b_wet";
constexpr char kProvisioningApName[] = "PlantLab-Setup";
constexpr const char* kSoftwareVersion = plantlab::kMasterSoftwareVersion;
constexpr uint16_t kProvisioningPort = 8080;
constexpr uint32_t kReconnectRetryMs = 5000UL;
constexpr uint32_t kHttpTimeoutMs = 20000UL;
constexpr uint32_t kBleProvisioningTimeoutMs = 4UL * 60UL * 1000UL;
constexpr uint32_t kBleWifiScanTimeoutMs = 15000UL;
constexpr uint32_t kBleWifiScanRetryDelayMs = 750UL;
constexpr uint8_t kBleWifiScanMaxRetries = 3;
constexpr uint32_t kFactoryResetHoldMs = 20000UL;
constexpr uint16_t kCameraProvisioningConfigVersion = 1;
constexpr uint16_t kTopCameraNodeIndex = 1;
constexpr uint16_t kSideCameraNodeIndex = 2;
constexpr uint16_t kTopCameraCapturePhaseSeconds = 0;
constexpr uint16_t kSideCameraCapturePhaseSeconds = 30;
constexpr CameraRoleCode kTopCameraRole = CameraRoleCode::kTop;
constexpr CameraRoleCode kSideCameraRole = CameraRoleCode::kSide;
constexpr uint32_t kCameraProvisioningRetryMs = 5000UL;
constexpr uint32_t kManualCameraProvisioningWindowMs = 120000UL;
constexpr uint32_t kCameraBootstrapCaptureRetryMs = 3000UL;
constexpr uint8_t kCameraBootstrapCaptureMaxAttempts = 6;
constexpr uint32_t kCameraCaptureFlightTimeoutMs = 30000UL;
constexpr uint32_t kManualCaptureAttemptTimeoutMs = 20000UL;
constexpr uint32_t kManualCaptureAckTimeoutMs = 120000UL;
constexpr uint8_t kManualCaptureMaxDispatchAttempts = 3;
constexpr uint32_t kCaptureResultRetryMs = 3000UL;
constexpr uint8_t kReadingRetryQueueSize = 12;
constexpr uint32_t kReadingRetryBaseDelayMs = 1000UL;
constexpr uint32_t kReadingRetryMaxDelayMs = 30000UL;
constexpr uint32_t kMasterNodeRegisterRetryMs = 5000UL;
constexpr uint32_t kScheduledCaptureRetryDelayMs = 3000UL;
constexpr bool kCameraScheduledCaptureEnabled = true;
constexpr bool kVerboseSensorPollingLogs = false;

enum class CameraProvisioningSlotId : uint8_t {
  kTop = 0,
  kSide = 1,
};

struct CameraProvisioningSlotConfig {
  CameraProvisioningSlotId id;
  const char* name;
  uint16_t camera_node_index;
  CameraRoleCode camera_role;
  uint16_t capture_phase_seconds;
};

constexpr CameraProvisioningSlotConfig kCameraProvisioningSlots[] = {
    {CameraProvisioningSlotId::kTop, "top", kTopCameraNodeIndex, kTopCameraRole, kTopCameraCapturePhaseSeconds},
    {CameraProvisioningSlotId::kSide, "side", kSideCameraNodeIndex, kSideCameraRole, kSideCameraCapturePhaseSeconds},
};

struct DeviceConfig {
  String wifi_ssid;
  String wifi_password;
  String claim_token;
  String device_token;
  String backend_url;
  String platform_url;
  int platform_device_id = 0;
  int attach_to_platform_device_id = 0;
};

struct PendingCaptureCommand {
  bool active = false;
  bool dispatched = false;
  bool result_ready = false;
  uint8_t dispatch_attempts = 0;
  int command_id = 0;
  bool contract_native = false;
  String contract_command_id;
  String contract_command_type;
  uint8_t camera_role = 0;
  uint32_t request_id = 0;
  unsigned long started_at_ms = 0;
  unsigned long last_result_attempt_ms = 0;
  String result_status;
  String result_message;
};

struct CameraCaptureFlight {
  bool active = false;
  bool delivery_failed = false;
  bool retry_available = false;
  int command_id = 0;
  uint8_t camera_role = 0;
  uint32_t request_id = 0;
  unsigned long started_at_ms = 0;
  unsigned long last_delivery_failure_ms = 0;
};

struct QueuedPlatformReading {
  bool active = false;
  PlatformReading reading;
  uint8_t attempts = 0;
  unsigned long next_retry_ms = 0;
  unsigned long queued_at_ms = 0;
};

struct EspNowSendContext {
  bool valid = false;
  uint32_t request_id = 0;
  int command_id = 0;
  EspNowCommandType command = EspNowCommandType::kHealthCheck;
  unsigned long sent_at_ms = 0;
  uint8_t target_mac[6] = {0};
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

WaterLevelSensorConfig waterLevelSensorConfig() {
  WaterLevelSensorConfig config{};
  config.channels[0] = WaterLevelChannelConfig{
      WaterLevelPad::kTop,
      WATER_LEVEL_TOP_GPIO,
      WATER_LEVEL_TOP_TOUCH_CHANNEL};
  config.channels[1] = WaterLevelChannelConfig{
      WaterLevelPad::kMiddle,
      WATER_LEVEL_MIDDLE_GPIO,
      WATER_LEVEL_MIDDLE_TOUCH_CHANNEL};
  config.channels[2] = WaterLevelChannelConfig{
      WaterLevelPad::kBottom,
      WATER_LEVEL_BOTTOM_GPIO,
      WATER_LEVEL_BOTTOM_TOUCH_CHANNEL};
  config.filter_sample_count = WATER_LEVEL_FILTER_SAMPLE_COUNT;
  config.sample_interval_ms = WATER_LEVEL_SAMPLE_INTERVAL_MS;
  config.startup_settle_ms = WATER_LEVEL_STARTUP_SETTLE_MS;
  config.channel_debounce_ms = WATER_LEVEL_CHANNEL_DEBOUNCE_MS;
  config.state_debounce_ms = WATER_LEVEL_STATE_DEBOUNCE_MS;
  config.inconsistent_grace_ms = WATER_LEVEL_INCONSISTENT_GRACE_MS;
  config.threshold_percent = WATER_LEVEL_THRESHOLD_PERCENT;
  config.hysteresis_percent = WATER_LEVEL_HYSTERESIS_PERCENT;
  config.min_signal_delta = WATER_LEVEL_MIN_SIGNAL_DELTA;
  config.max_stable_spread = WATER_LEVEL_MAX_STABLE_SPREAD;
  config.read_failure_timeout_ms = WATER_LEVEL_READ_FAILURE_TIMEOUT_MS;
  return config;
}

MoistureSensor g_moisture(
    PIN_SOIL_MOISTURE_ADC, MOISTURE_SAMPLE_COUNT, MOISTURE_SAMPLE_DELAY_MS);
Esp32WaterLevelTouchTransport g_water_level_touch_transport;
WaterLevelSensor g_water_level(&g_water_level_touch_transport, waterLevelSensorConfig());
I2cEnvironmentSensors g_i2c_environment(PIN_I2C_SDA, PIN_I2C_SCL);
LightController g_growing_light(
    PIN_GROW_LIGHT_RED_CTRL,
    PIN_GROW_LIGHT_WHITE_CTRL,
    ACTUATOR_ON_LEVEL,
    ACTUATOR_OFF_LEVEL,
    PLANTLAB_LIGHT_INTENSITY_CONTROL_ENABLED != 0,
    PLANTLAB_GROW_LIGHT_PWM_FREQUENCY_HZ);
PumpController g_pump(PIN_PUMP_MOSFET_GATE, ACTUATOR_ON_LEVEL, ACTUATOR_OFF_LEVEL);
PowerButton g_power_button(
    PIN_POWER_BUTTON,
    POWER_BUTTON_ACTIVE_LEVEL,
    POWER_BUTTON_DEBOUNCE_MS,
    POWER_BUTTON_LONG_PRESS_MS);
StatusLed g_status_led(PIN_STATUS_LED, STATUS_LED_ON_LEVEL, STATUS_LED_OFF_LEVEL);
plantlab::ambient_led_belt::FastAmbientLedBeltTransport g_ambient_led_belt_transport;
plantlab::ambient_led_belt::AmbientLedBeltController g_ambient_led_belt(&g_ambient_led_belt_transport);
Preferences g_preferences;
WebServer g_web_server(kProvisioningPort);
plantlab::BleProvisioningService g_ble_provisioning;
std::unique_ptr<PlatformClient> g_platform_client;
std::unique_ptr<plantlab::OtaUpdateManager> g_ota_update_manager;
MasterCaptureScheduleState g_camera_capture_schedule{};
MasterCaptureScheduleState g_side_camera_capture_schedule{};

DeviceConfig g_config;
DeviceConfig g_previous_active_config;
DeviceMode g_device_mode = DeviceMode::kBooting;
unsigned long g_last_platform_send_ms = 0;
unsigned long g_last_platform_status_ms = 0;
unsigned long g_last_command_poll_ms = 0;
unsigned long g_last_wifi_attempt_ms = 0;
bool g_provisioning_mode = false;
bool g_provisioning_requested = false;
bool g_normal_tasks_paused_for_provisioning = false;
bool g_softap_provisioning_active = false;
bool g_wifi_ready = false;
bool g_pending_provisioning_config_active = false;
bool g_web_routes_registered = false;
bool g_restart_scheduled = false;
unsigned long g_restart_at_ms = 0;
String g_restart_reason;
plantlab::ProvisioningState g_provisioning_state = plantlab::ProvisioningState::NORMAL;
unsigned long g_ble_provisioning_started_at_ms = 0;
bool g_ble_had_previous_config = false;
bool g_factory_reset_fired = false;
unsigned long g_factory_reset_pressed_since_ms = 0;
String g_pending_claim_token;
String g_pending_backend_url;
String g_pending_platform_url;
String g_pending_return_url;
std::vector<WiFiNetworkOption> g_cached_wifi_networks;
bool g_ble_wifi_scan_active = false;
uint32_t g_ble_wifi_scan_id = 0;
unsigned long g_ble_wifi_scan_started_at_ms = 0;
unsigned long g_ble_wifi_scan_retry_at_ms = 0;
uint8_t g_ble_wifi_scan_retry_count = 0;
bool g_espnow_ready = false;
uint32_t g_next_espnow_request_id = 1;
MasterProvisioningSession g_camera_provisioning_session{};
bool g_camera_provisioning_acknowledged = false;
CameraProvisioningSlotId g_camera_provisioning_slot_id = CameraProvisioningSlotId::kTop;
bool g_camera_provisioning_manual_active = false;
bool g_camera_auto_provisioning_enabled = false;
unsigned long g_camera_provisioning_manual_deadline_ms = 0;
bool g_camera_runtime_ready = false;
unsigned long g_last_local_sensor_read_ms = 0;
unsigned long g_last_water_level_diagnostic_ms = 0;
String g_serial_command_buffer;
unsigned long g_last_camera_provisioning_attempt_ms = 0;
constexpr uint8_t kEspNowBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint8_t g_camera_provisioning_target_mac[6] = {0};
bool g_camera_provisioning_target_mac_known = false;
uint8_t g_camera_target_mac[6] = {0};
bool g_camera_target_mac_known = false;
bool g_camera_bootstrap_capture_active = false;
uint8_t g_camera_bootstrap_capture_attempts = 0;
unsigned long g_next_camera_bootstrap_capture_ms = 0;
PendingCaptureCommand g_pending_capture_command{};
CameraCaptureFlight g_camera_capture_in_flight{};
EspNowSendContext g_last_espnow_send{};
bool g_camera_schedule_paused_for_manual = false;
QueuedPlatformReading g_reading_retry_queue[kReadingRetryQueueSize]{};
uint32_t g_boot_counter = 0;
uint32_t g_reading_sequence = 0;
uint32_t g_consecutive_heartbeat_failures = 0;
PlatformErrorCounters g_diagnostic_error_counters{};
String g_last_diagnostic_error_code;
String g_last_diagnostic_error_message;
unsigned long g_last_sensor_reading_ms = 0;
int g_last_command_id = 0;
String g_last_command_status;
String g_last_command_code;
String g_last_command_message;
unsigned long g_last_command_result_ms = 0;
unsigned long g_last_command_poll_completed_ms = 0;
uint32_t g_last_command_poll_latency_ms = 0;
String g_last_command_poll_at_iso;
String g_last_command_poll_status = "never";
String g_last_command_poll_error;
bool g_master_node_registered = false;
unsigned long g_last_master_node_register_attempt_ms = 0;
bool g_scheduled_capture_retry_pending = false;
unsigned long g_scheduled_capture_retry_at_ms = 0;
uint8_t g_scheduled_capture_retry_camera_role = static_cast<uint8_t>(CameraRoleCode::kTop);

const char* manualCaptureAckMessage(EspNowAckStatus ack_status);
void clearPendingCaptureCommand();
void clearCameraCaptureFlight();
void markCameraCaptureInFlight(
    uint32_t request_id,
    int command_id,
    unsigned long now,
    bool retry_available = false,
    uint8_t camera_role = 0);
bool sendEspNowPauseCaptureCommand(bool paused);
void setCameraSchedulePausedForManual(bool paused);
void queuePendingCaptureCommandResult(const char* status, const String& message);
void flushPendingCaptureCommandResult();
void markPendingCaptureCommandInProgress(int command_id);
void recordDiagnosticError(const char* code, const String& message);
void recordLastCommandResult(int command_id, const char* status, const String& message, const char* code);
void recordCommandPollResult(const char* status, const String& error, unsigned long started_at_ms, unsigned long finished_at_ms);
bool startPendingCaptureCommand(const PlatformCommand& command, unsigned long now);
bool dispatchPendingCaptureCommand(unsigned long now);
void serviceCameraCaptureFlight(unsigned long now);
void servicePendingCaptureCommand(unsigned long now);
void noteEspNowSend(
    EspNowCommandType command,
    uint32_t request_id,
    int command_id,
    const uint8_t* target_mac,
    unsigned long now);
bool ensureEspNowPeer(const uint8_t* peer_mac);
MasterCaptureScheduleState* captureScheduleForRole(uint8_t camera_role);
void startProvisioningMode();
bool provisioningPriorityActive();
void pauseNormalTasksForProvisioning();
void resumeNormalTasksAfterProvisioning();
bool requestBleProvisioningMode(unsigned long now);
void checkProvisioningButton();
void resetBleWifiScanRuntime();
void stopBleWifiScanRadio();
void initReliabilityBootCounter();
bool ensureMasterDeviceNodeRegistered(unsigned long now);
bool platform_enabled();
bool loadAmbientLedBeltConfig();
bool saveAmbientLedBeltConfig();
void clearAmbientLedBeltConfig();
bool loadWaterLevelCalibration();
bool saveWaterLevelCalibration();
void clearWaterLevelCalibration();
void serviceWaterLevelDiagnostics(unsigned long now);
void serviceSerialDiagnostics(unsigned long now);
void handleSerialDiagnosticLine(const String& line);
void printWaterLevelStatus();
void applyWaterLevelStatus(PlatformStatus* status);
String masterCapabilitiesJson();
DeviceConfig normalizedConfig(DeviceConfig config);
bool saveConfigCandidate(const DeviceConfig& candidate);
bool savePendingConfigCandidate(const DeviceConfig& candidate);
bool loadPendingConfig(DeviceConfig* pending);
void clearPendingConfig();
bool restorePreviousActiveConfigAfterPendingFailure(const char* reason);

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

String withExpectedImageSetting(const String& url, bool expect_image) {
  if (url.length() == 0) {
    return url;
  }

  const String target = String("expect_image=") + (expect_image ? "1" : "0");
  const int query_index = url.indexOf('?');
  if (query_index < 0) {
    return url + "?" + target;
  }

  const int expect_index = url.indexOf("expect_image=", query_index + 1);
  if (expect_index < 0) {
    return url + "&" + target;
  }

  int value_end = url.indexOf('&', expect_index);
  if (value_end < 0) {
    value_end = url.length();
  }
  return url.substring(0, expect_index) + target + url.substring(value_end);
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

bool configHasRuntimeRegistration(const DeviceConfig& config) {
  return config.platform_device_id > 0 && config.device_token.length() > 0;
}

bool shouldRegisterAsFactoryResetTransfer() {
  return hasPendingClaim() &&
         g_config.attach_to_platform_device_id <= 0 &&
         !configHasRuntimeRegistration(g_previous_active_config);
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

String bleProvisioningDeviceName() {
  const String hardware_id = stableHardwareDeviceId();
  const int suffix_length = 6;
  const int start = std::max(0, static_cast<int>(hardware_id.length()) - suffix_length);
  return String("PlantLab-Setup-") + hardware_id.substring(start);
}

String bleProvisioningDeviceIdentityJson(const String& advertised_name) {
  StaticJsonDocument<512> payload;
  const String hardware_id = stableHardwareDeviceId();
  payload["source"] = "esp32-ble";
  payload["schema_version"] = 1;
  payload["device_id"] = hardware_id;
  payload["hardware_device_id"] = hardware_id;
  payload["hardware_model"] = "esp32_master";
  payload["hardware_version"] = BOARD_NAME;
  payload["software_version"] = kSoftwareVersion;
  payload["node_role"] = "master";
  payload["display_name"] = "Master";
  payload["ble_name"] = advertised_name;

  String json;
  serializeJson(payload, json);
  return json;
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
  g_ota_update_manager.reset();
  g_platform_client.reset();
  g_master_node_registered = false;
  g_last_master_node_register_attempt_ms = 0;
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
  g_ota_update_manager.reset(new plantlab::OtaUpdateManager(
      g_platform_client.get(),
      stableHardwareDeviceId().c_str(),
      "master",
      "esp32_master",
      kSoftwareVersion,
      plantlab::kMasterSoftwareVersionCode));
  g_ota_update_manager->begin();
  Serial.printf("[platform] base_url: %s\n", g_platform_client->base_url().c_str());
  Serial.printf("[platform] device_id: %d\n", g_platform_client->device_id());
}

void initReliabilityBootCounter() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[platform] boot counter unavailable");
    return;
  }
  const uint32_t previous = g_preferences.getUInt(kConfigKeyBootCounter, 0);
  g_boot_counter = previous + 1;
  g_preferences.putUInt(kConfigKeyBootCounter, g_boot_counter);
  g_preferences.end();
  Serial.printf("[platform] reliability boot_counter=%lu\n", static_cast<unsigned long>(g_boot_counter));
}

String nextReadingIdempotencyKey() {
  ++g_reading_sequence;
  return stableHardwareDeviceId() + ":" + String(g_boot_counter) + ":" + String(g_reading_sequence);
}

String masterCapabilitiesJson() {
  StaticJsonDocument<2304> capabilities;
  capabilities["sensors"] = true;
  capabilities["actuators"] = true;
  capabilities["esp_now"] = true;
  capabilities["grow_light"] = true;
  capabilities["grow_light_driver"] = "dual_al8860";
  capabilities["grow_light_channel_control"] = true;
  capabilities["grow_light_red_ctrl_gpio"] = PIN_GROW_LIGHT_RED_CTRL;
  capabilities["grow_light_white_ctrl_gpio"] = PIN_GROW_LIGHT_WHITE_CTRL;
  capabilities["grow_light_pwm_frequency_hz"] = g_growing_light.pwm_frequency_hz();
  capabilities["light_control"] = true;
  capabilities["light_intensity_control"] = g_growing_light.supports_intensity_control();
  capabilities["light_intensity_min_percent"] = 0;
  capabilities["light_intensity_max_percent"] = 100;
  JsonArray light_control_modes = capabilities.createNestedArray("light_control_modes");
  light_control_modes.add("on_off");
  if (g_growing_light.supports_intensity_control()) {
    light_control_modes.add("intensity");
  }
  capabilities["moisture_sensor"] = g_moisture.enabled();
  capabilities["water_temperature_sensor"] = g_i2c_environment.mcp9808_present();
  capabilities["water_temperature_sensor_source"] = "mcp9808";
  capabilities["water_level_sensor"] = true;
  capabilities["water_level_sensor_type"] = "esp32s3_touch_three_pad";
  capabilities["water_level_calibrated"] = g_water_level.calibrationReady();
  capabilities["water_level_top_gpio"] = WATER_LEVEL_TOP_GPIO;
  capabilities["water_level_middle_gpio"] = WATER_LEVEL_MIDDLE_GPIO;
  capabilities["water_level_bottom_gpio"] = WATER_LEVEL_BOTTOM_GPIO;
  capabilities["water_level_top_touch_channel"] = WATER_LEVEL_TOP_TOUCH_CHANNEL;
  capabilities["water_level_middle_touch_channel"] = WATER_LEVEL_MIDDLE_TOUCH_CHANNEL;
  capabilities["water_level_bottom_touch_channel"] = WATER_LEVEL_BOTTOM_TOUCH_CHANNEL;
  capabilities["temperature_sensor"] = true;
  capabilities["humidity_sensor"] = true;
  capabilities["i2c_sda_gpio"] = PIN_I2C_SDA;
  capabilities["i2c_scl_gpio"] = PIN_I2C_SCL;
  capabilities["aht20_sensor"] = g_i2c_environment.aht20_present();
  capabilities["mcp9808_sensor"] = g_i2c_environment.mcp9808_present();
  capabilities["temperature_sensor_source"] = "aht20";
  capabilities["humidity_sensor_source"] = "aht20";

  const plantlab::ambient_led_belt::AmbientLedBeltState& belt = g_ambient_led_belt.state();
  capabilities["ambient_led_belt"] = true;
  capabilities["ambient_led_belt_available"] = belt.available;
  capabilities["ambient_led_belt_data_gpio"] = belt.data_gpio;
  capabilities["ambient_led_belt_logical_pixel_count"] = belt.logical_pixel_count;
  capabilities["ambient_led_belt_physical_led_count"] = belt.physical_led_count;
  capabilities["ambient_led_belt_color_order"] = plantlab::ambient_led_belt::colorOrderName(belt.color_order);
  capabilities["ambient_led_belt_max_brightness"] = g_ambient_led_belt.config().maximum_brightness;

  String json;
  serializeJson(capabilities, json);
  return json;
}

bool ambientLedBeltPinConflict(const plantlab::ambient_led_belt::AmbientLedBeltConfig& config, String* error) {
  if (PIN_SOIL_MOISTURE_ADC >= 0 && PIN_SOIL_MOISTURE_ADC == config.data_gpio) {
    if (error != nullptr) {
      *error = "ambient LED belt DIN conflicts with soil moisture ADC GPIO";
    }
    return true;
  }
  return false;
}

bool loadAmbientLedBeltConfig() {
  plantlab::ambient_led_belt::AmbientLedBeltConfig config = plantlab::ambient_led_belt::defaultConfig();
  if (!g_preferences.begin(kPreferencesNamespace, true)) {
    Serial.println("[ambient-led-belt] Preferences unavailable, using defaults");
  } else {
    const int stored_logical_count =
        g_preferences.getInt(kConfigKeyAmbientLedBeltLogicalCount, config.logical_pixel_count);
    const String stored_color_order =
        g_preferences.getString(kConfigKeyAmbientLedBeltColorOrder, plantlab::ambient_led_belt::colorOrderName(config.color_order));
    const int stored_max_brightness =
        g_preferences.getInt(kConfigKeyAmbientLedBeltMaxBrightness, config.maximum_brightness);
    const int stored_default_brightness =
        g_preferences.getInt(kConfigKeyAmbientLedBeltDefaultBrightness, config.default_brightness);
    g_preferences.end();

    if (stored_logical_count > 0 && stored_logical_count <= AMBIENT_LED_BELT_MAX_LOGICAL_PIXELS) {
      config.logical_pixel_count = static_cast<uint16_t>(stored_logical_count);
    } else {
      Serial.printf("[ambient-led-belt] ignoring invalid stored logical_pixel_count=%d\n", stored_logical_count);
    }
    plantlab::ambient_led_belt::ColorOrder order;
    if (plantlab::ambient_led_belt::parseColorOrder(stored_color_order, &order)) {
      config.color_order = order;
    } else {
      Serial.printf("[ambient-led-belt] ignoring invalid stored color_order=%s\n", stored_color_order.c_str());
    }
    if (stored_max_brightness > 0 && stored_max_brightness <= 255) {
      config.maximum_brightness = static_cast<uint8_t>(stored_max_brightness);
      config.diagnostic_max_brightness =
          std::min<uint8_t>(config.diagnostic_max_brightness, config.maximum_brightness);
    } else {
      Serial.printf("[ambient-led-belt] ignoring invalid stored max_brightness=%d\n", stored_max_brightness);
    }
    if (stored_default_brightness >= 0 && stored_default_brightness <= config.maximum_brightness) {
      config.default_brightness = static_cast<uint8_t>(stored_default_brightness);
    } else {
      Serial.printf("[ambient-led-belt] ignoring invalid stored default_brightness=%d\n", stored_default_brightness);
    }
  }

  String error;
  if (ambientLedBeltPinConflict(config, &error)) {
    Serial.printf("[ambient-led-belt] unavailable: %s\n", error.c_str());
    g_ambient_led_belt.configure(config, nullptr);
    g_ambient_led_belt.markUnavailable(error);
    return false;
  }
  if (!g_ambient_led_belt.configure(config, &error)) {
    Serial.printf("[ambient-led-belt] config invalid, using defaults: %s\n", error.c_str());
    plantlab::ambient_led_belt::AmbientLedBeltConfig defaults = plantlab::ambient_led_belt::defaultConfig();
    if (!g_ambient_led_belt.configure(defaults, &error)) {
      Serial.printf("[ambient-led-belt] default config invalid: %s\n", error.c_str());
      return false;
    }
  }
  Serial.printf(
      "[ambient-led-belt] config gpio=GPIO%d logical_pixels=%u physical_leds=%u color_order=%s max_brightness=%u default_brightness=%u startup=off\n",
      g_ambient_led_belt.config().data_gpio,
      static_cast<unsigned int>(g_ambient_led_belt.config().logical_pixel_count),
      static_cast<unsigned int>(g_ambient_led_belt.config().physical_led_count),
      plantlab::ambient_led_belt::colorOrderName(g_ambient_led_belt.config().color_order),
      static_cast<unsigned int>(g_ambient_led_belt.config().maximum_brightness),
      static_cast<unsigned int>(g_ambient_led_belt.config().default_brightness));
  return true;
}

bool saveAmbientLedBeltConfig() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[ambient-led-belt] failed to open Preferences for config save");
    return false;
  }
  const plantlab::ambient_led_belt::AmbientLedBeltConfig& config = g_ambient_led_belt.config();
  const size_t logical_written = g_preferences.putInt(kConfigKeyAmbientLedBeltLogicalCount, config.logical_pixel_count);
  const size_t order_written =
      g_preferences.putString(kConfigKeyAmbientLedBeltColorOrder, plantlab::ambient_led_belt::colorOrderName(config.color_order));
  const size_t max_written = g_preferences.putInt(kConfigKeyAmbientLedBeltMaxBrightness, config.maximum_brightness);
  const size_t default_written = g_preferences.putInt(kConfigKeyAmbientLedBeltDefaultBrightness, config.default_brightness);
  g_preferences.end();
  const bool saved = logical_written > 0 && order_written > 0 && max_written > 0 && default_written > 0;
  Serial.printf("[ambient-led-belt] config save %s\n", saved ? "succeeded" : "failed");
  return saved;
}

void clearAmbientLedBeltConfig() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[ambient-led-belt] failed to open Preferences for config reset");
    return;
  }
  g_preferences.remove(kConfigKeyAmbientLedBeltLogicalCount);
  g_preferences.remove(kConfigKeyAmbientLedBeltColorOrder);
  g_preferences.remove(kConfigKeyAmbientLedBeltMaxBrightness);
  g_preferences.remove(kConfigKeyAmbientLedBeltDefaultBrightness);
  g_preferences.end();
  g_ambient_led_belt.clear();
  Serial.println("[ambient-led-belt] config reset to defaults");
}

bool loadWaterLevelCalibration() {
  if (!g_preferences.begin(kPreferencesNamespace, true)) {
    Serial.println("[water-level] Preferences unavailable, calibration not loaded");
    return false;
  }

  const uint32_t missing = 0xFFFFFFFFUL;
  WaterLevelStoredCalibration stored{};
  stored.version = g_preferences.getUInt(kConfigKeyWaterLevelCalibrationVersion, 0);
  const uint32_t dry_values[kWaterLevelChannelCount] = {
      g_preferences.getUInt(kConfigKeyWaterLevelTopDry, missing),
      g_preferences.getUInt(kConfigKeyWaterLevelMiddleDry, missing),
      g_preferences.getUInt(kConfigKeyWaterLevelBottomDry, missing),
  };
  const uint32_t wet_values[kWaterLevelChannelCount] = {
      g_preferences.getUInt(kConfigKeyWaterLevelTopWet, missing),
      g_preferences.getUInt(kConfigKeyWaterLevelMiddleWet, missing),
      g_preferences.getUInt(kConfigKeyWaterLevelBottomWet, missing),
  };
  g_preferences.end();

  if (stored.version != kWaterLevelCalibrationVersion) {
    Serial.println("[water-level] no compatible calibration in Preferences");
    return false;
  }

  bool complete = true;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    WaterLevelChannelCalibration& calibration = stored.channels[index];
    calibration.dry_baseline = dry_values[index];
    calibration.wet_reference = wet_values[index];
    calibration.dry_valid = dry_values[index] != missing;
    calibration.wet_valid = wet_values[index] != missing;
    complete = complete && calibration.dry_valid && calibration.wet_valid;
  }

  const bool loaded = complete && g_water_level.loadCalibration(stored);
  Serial.printf("[water-level] calibration load %s\n", loaded ? "succeeded" : "incomplete");
  return loaded;
}

bool saveWaterLevelCalibration() {
  WaterLevelStoredCalibration stored{};
  if (!g_water_level.saveCalibration(&stored)) {
    Serial.println("[water-level] calibration save skipped: calibration incomplete");
    return false;
  }
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[water-level] failed to open Preferences for calibration save");
    return false;
  }
  const size_t version_written =
      g_preferences.putUInt(kConfigKeyWaterLevelCalibrationVersion, stored.version);
  const size_t top_dry_written =
      g_preferences.putUInt(kConfigKeyWaterLevelTopDry, stored.channels[0].dry_baseline);
  const size_t top_wet_written =
      g_preferences.putUInt(kConfigKeyWaterLevelTopWet, stored.channels[0].wet_reference);
  const size_t middle_dry_written =
      g_preferences.putUInt(kConfigKeyWaterLevelMiddleDry, stored.channels[1].dry_baseline);
  const size_t middle_wet_written =
      g_preferences.putUInt(kConfigKeyWaterLevelMiddleWet, stored.channels[1].wet_reference);
  const size_t bottom_dry_written =
      g_preferences.putUInt(kConfigKeyWaterLevelBottomDry, stored.channels[2].dry_baseline);
  const size_t bottom_wet_written =
      g_preferences.putUInt(kConfigKeyWaterLevelBottomWet, stored.channels[2].wet_reference);
  g_preferences.end();

  const bool saved =
      version_written > 0 && top_dry_written > 0 && top_wet_written > 0 &&
      middle_dry_written > 0 && middle_wet_written > 0 &&
      bottom_dry_written > 0 && bottom_wet_written > 0;
  Serial.printf("[water-level] calibration save %s\n", saved ? "succeeded" : "failed");
  return saved;
}

void clearWaterLevelCalibration() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[water-level] failed to open Preferences for calibration reset");
    return;
  }
  g_preferences.remove(kConfigKeyWaterLevelCalibrationVersion);
  g_preferences.remove(kConfigKeyWaterLevelTopDry);
  g_preferences.remove(kConfigKeyWaterLevelTopWet);
  g_preferences.remove(kConfigKeyWaterLevelMiddleDry);
  g_preferences.remove(kConfigKeyWaterLevelMiddleWet);
  g_preferences.remove(kConfigKeyWaterLevelBottomDry);
  g_preferences.remove(kConfigKeyWaterLevelBottomWet);
  g_preferences.end();
  g_water_level.resetCalibration();
  Serial.println("[water-level] calibration reset");
}

bool ensureMasterDeviceNodeRegistered(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready) {
    return false;
  }
  if (g_master_node_registered) {
    return true;
  }
  if (now - g_last_master_node_register_attempt_ms < kMasterNodeRegisterRetryMs) {
    return false;
  }
  g_last_master_node_register_attempt_ms = now;

  String error;
  const String capabilities_json = masterCapabilitiesJson();
  const bool registered = g_platform_client->register_device_node(
      stableHardwareDeviceId().c_str(),
      "master",
      "Master",
      "esp32_master",
      BOARD_NAME,
      kSoftwareVersion,
      capabilities_json.c_str(),
      nullptr,
      &error);
  if (registered) {
    g_master_node_registered = true;
    Serial.println("[platform] master node registration succeeded");
    return true;
  }
  Serial.printf("[platform] master node registration failed: %s\n", error.c_str());
  return false;
}

bool platform_enabled() {
  return g_platform_client != nullptr && g_platform_client->configured();
}

bool provisioningPriorityActive() {
  return g_provisioning_requested || g_provisioning_mode || g_ble_provisioning.active();
}

void pauseNormalTasksForProvisioning() {
  if (g_normal_tasks_paused_for_provisioning) {
    return;
  }
  g_normal_tasks_paused_for_provisioning = true;
  Serial.println("[provisioning] normal_tasks_paused");
}

void resumeNormalTasksAfterProvisioning() {
  if (!g_normal_tasks_paused_for_provisioning) {
    return;
  }
  g_normal_tasks_paused_for_provisioning = false;
  g_provisioning_requested = false;
  Serial.println("[provisioning] normal_tasks_resumed");
}

void scheduleRestart(unsigned long delay_ms, const char* reason) {
  g_restart_scheduled = true;
  g_restart_at_ms = millis() + delay_ms;
  g_restart_reason = reason == nullptr || strlen(reason) == 0 ? "unspecified" : reason;
}

const CameraProvisioningSlotConfig& cameraProvisioningSlot(CameraProvisioningSlotId slot_id) {
  switch (slot_id) {
    case CameraProvisioningSlotId::kSide:
      return kCameraProvisioningSlots[1];
    case CameraProvisioningSlotId::kTop:
    default:
      return kCameraProvisioningSlots[0];
  }
}

const CameraProvisioningSlotConfig& activeCameraProvisioningSlot() {
  return cameraProvisioningSlot(g_camera_provisioning_slot_id);
}

bool cameraProvisioningSlotFromName(const String& value, CameraProvisioningSlotId* slot_id) {
  String normalized = value;
  normalized.trim();
  normalized.toLowerCase();
  if (normalized == "top" || normalized == "1") {
    if (slot_id != nullptr) {
      *slot_id = CameraProvisioningSlotId::kTop;
    }
    return true;
  }
  if (normalized == "side" || normalized == "2") {
    if (slot_id != nullptr) {
      *slot_id = CameraProvisioningSlotId::kSide;
    }
    return true;
  }
  return false;
}

bool parseMacAddress(const String& value, uint8_t* mac) {
  if (mac == nullptr) {
    return false;
  }
  int parts[6] = {0, 0, 0, 0, 0, 0};
  char trailing = '\0';
  const int parsed = std::sscanf(
      value.c_str(),
      "%x:%x:%x:%x:%x:%x%c",
      &parts[0],
      &parts[1],
      &parts[2],
      &parts[3],
      &parts[4],
      &parts[5],
      &trailing);
  if (parsed != 6) {
    return false;
  }
  for (int index = 0; index < 6; ++index) {
    if (parts[index] < 0 || parts[index] > 0xFF) {
      return false;
    }
    mac[index] = static_cast<uint8_t>(parts[index]);
  }
  return true;
}

const uint8_t* activeCameraProvisioningTargetMac() {
  return g_camera_provisioning_target_mac_known ? g_camera_provisioning_target_mac : kEspNowBroadcastMac;
}

void requestCameraProvisioningSlot(
    CameraProvisioningSlotId slot_id,
    const uint8_t* target_mac,
    unsigned long now) {
  g_camera_provisioning_slot_id = slot_id;
  g_camera_provisioning_manual_active = true;
  g_camera_auto_provisioning_enabled = false;
  g_camera_provisioning_manual_deadline_ms = now + kManualCameraProvisioningWindowMs;
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_acknowledged = false;
  g_last_camera_provisioning_attempt_ms = 0;
  if (target_mac != nullptr) {
    memcpy(g_camera_provisioning_target_mac, target_mac, sizeof(g_camera_provisioning_target_mac));
    g_camera_provisioning_target_mac_known = true;
  } else {
    memset(g_camera_provisioning_target_mac, 0, sizeof(g_camera_provisioning_target_mac));
    g_camera_provisioning_target_mac_known = false;
  }

  const CameraProvisioningSlotConfig& slot = activeCameraProvisioningSlot();
  Serial.printf(
      "[camera-provisioning] manual slot=%s camera_index=%u role=%s target=%s window_ms=%lu\n",
      slot.name,
      static_cast<unsigned int>(slot.camera_node_index),
      espnow_camera_role_label(static_cast<uint8_t>(slot.camera_role)),
      macToString(activeCameraProvisioningTargetMac()).c_str(),
      static_cast<unsigned long>(kManualCameraProvisioningWindowMs));
  if (slot.id == CameraProvisioningSlotId::kSide && !g_camera_provisioning_target_mac_known) {
    Serial.println("[camera-provisioning] warning: side provisioning is broadcast; power only the intended side camera");
  }
}

void enableAutomaticTopCameraProvisioning(unsigned long now) {
  (void)now;
  g_camera_provisioning_slot_id = CameraProvisioningSlotId::kTop;
  g_camera_provisioning_manual_active = false;
  g_camera_auto_provisioning_enabled = true;
  g_camera_provisioning_manual_deadline_ms = 0;
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_acknowledged = false;
  g_last_camera_provisioning_attempt_ms = 0;
  memset(g_camera_provisioning_target_mac, 0, sizeof(g_camera_provisioning_target_mac));
  g_camera_provisioning_target_mac_known = false;
  Serial.println("[camera-provisioning] automatic top-camera provisioning enabled");
}

void stopCameraProvisioning(const char* reason) {
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_acknowledged = true;
  g_camera_provisioning_manual_active = false;
  g_camera_auto_provisioning_enabled = false;
  g_camera_provisioning_manual_deadline_ms = 0;
  g_camera_provisioning_slot_id = CameraProvisioningSlotId::kTop;
  memset(g_camera_provisioning_target_mac, 0, sizeof(g_camera_provisioning_target_mac));
  g_camera_provisioning_target_mac_known = false;
  Serial.printf(
      "[camera-provisioning] stopped reason=%s\n",
      reason != nullptr && strlen(reason) > 0 ? reason : "manual");
}

void printCameraProvisioningStatus() {
  const CameraProvisioningSlotConfig& slot = activeCameraProvisioningSlot();
  unsigned long remaining_ms = 0;
  if (g_camera_provisioning_manual_active) {
    const unsigned long now = millis();
    remaining_ms =
        static_cast<long>(g_camera_provisioning_manual_deadline_ms - now) > 0
            ? static_cast<unsigned long>(g_camera_provisioning_manual_deadline_ms - now)
            : 0;
  }
  Serial.printf(
      "[camera-provisioning] status slot=%s camera_index=%u role=%s target=%s manual=%u auto=%u remaining_ms=%lu ack=%u session_state=%u runtime_ready=%u\n",
      slot.name,
      static_cast<unsigned int>(slot.camera_node_index),
      espnow_camera_role_label(static_cast<uint8_t>(slot.camera_role)),
      macToString(activeCameraProvisioningTargetMac()).c_str(),
      g_camera_provisioning_manual_active ? 1U : 0U,
      g_camera_auto_provisioning_enabled ? 1U : 0U,
      static_cast<unsigned long>(remaining_ms),
      g_camera_provisioning_acknowledged ? 1U : 0U,
      static_cast<unsigned int>(g_camera_provisioning_session.state),
      g_camera_runtime_ready ? 1U : 0U);
}

bool buildCameraProvisioningPayload(
    CameraProvisioningPayload* payload,
    const CameraProvisioningSlotConfig& slot) {
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
      slot.camera_node_index,
      static_cast<uint32_t>(g_config.platform_device_id),
      slot.camera_role,
      slot.capture_phase_seconds,
      g_config.wifi_ssid.c_str(),
      g_config.wifi_password.c_str(),
      platform_url.c_str(),
      g_config.device_token.c_str());
}

void onEspNowDataSent(const uint8_t* mac_addr, esp_now_send_status_t status) {
  if (status != ESP_NOW_SEND_SUCCESS) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_send_failed", "ESP-NOW delivery failed");
    if (g_camera_capture_in_flight.active) {
      g_camera_capture_in_flight.delivery_failed = true;
      g_camera_capture_in_flight.last_delivery_failure_ms = millis();
    }
    Serial.printf(
        "[camera-schedule] ESP-NOW send failed status=%d command=%s request=%u command_id=%d target=%s age_ms=%lu\n",
        static_cast<int>(status),
        espnowCommandToString(g_last_espnow_send.command),
        static_cast<unsigned int>(g_last_espnow_send.request_id),
        g_last_espnow_send.command_id,
        mac_addr != nullptr ? macToString(mac_addr).c_str() : macToString(g_last_espnow_send.target_mac).c_str(),
        static_cast<unsigned long>(millis() - g_last_espnow_send.sent_at_ms));
  }
}

void noteEspNowSend(
    EspNowCommandType command,
    uint32_t request_id,
    int command_id,
    const uint8_t* target_mac,
    unsigned long now) {
  g_last_espnow_send.valid = true;
  g_last_espnow_send.command = command;
  g_last_espnow_send.request_id = request_id;
  g_last_espnow_send.command_id = command_id;
  g_last_espnow_send.sent_at_ms = now;
  if (target_mac != nullptr) {
    memcpy(g_last_espnow_send.target_mac, target_mac, sizeof(g_last_espnow_send.target_mac));
  } else {
    memset(g_last_espnow_send.target_mac, 0, sizeof(g_last_espnow_send.target_mac));
  }
}

void onEspNowDataReceived(const uint8_t* mac_addr, const uint8_t* data, int len) {
  if (len != static_cast<int>(sizeof(EspNowPacket))) {
    if (!g_provisioning_mode && !g_ble_wifi_scan_active) {
      Serial.printf(
          "[camera-schedule] ignored ESP-NOW packet length=%d from %s\n",
          len,
          mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
    }
    return;
  }

  EspNowPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic != ESPNOW_TEST_MAGIC || packet.version != ESPNOW_TEST_VERSION) {
    if (!g_provisioning_mode && !g_ble_wifi_scan_active) {
      Serial.printf(
          "[camera-schedule] ignored invalid ESP-NOW packet magic=%lu version=%u from %s\n",
          static_cast<unsigned long>(packet.magic),
          static_cast<unsigned int>(packet.version),
          mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
    }
    return;
  }

  const EspNowMessageKind kind = static_cast<EspNowMessageKind>(packet.kind);
  const EspNowCommandType command = static_cast<EspNowCommandType>(packet.command);

  Serial.printf(
      "[camera-schedule] RX kind=%u command=%s request=%u ack=%u from %s\n",
      static_cast<unsigned int>(packet.kind),
      espnowCommandToString(command),
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned int>(packet.ack_status),
      mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");

  if (kind == EspNowMessageKind::kHealthReport) {
    const uint32_t flags = packet.value_u32_1;
    const uint8_t camera_role = static_cast<uint8_t>((packet.value_u32_2 >> 16) & 0xFFu);
    const uint16_t camera_index = static_cast<uint16_t>(packet.value_u32_2 & 0xFFFFu);
    const bool wifi_ready = (flags & ESPNOW_HEALTH_FLAG_WIFI_READY) != 0;
    const bool node_registered = (flags & ESPNOW_HEALTH_FLAG_NODE_REGISTERED) != 0;
    const bool config_ready = (flags & ESPNOW_HEALTH_FLAG_CONFIG_READY) != 0;
    const bool is_camera_capture_health =
        g_camera_capture_in_flight.active && packet.request_id == g_camera_capture_in_flight.request_id;
    const bool is_pending_capture_health = g_pending_capture_command.active &&
                                           g_pending_capture_command.dispatched &&
                                           packet.request_id == g_pending_capture_command.request_id;
    if (mac_addr != nullptr) {
      memcpy(g_camera_target_mac, mac_addr, sizeof(g_camera_target_mac));
      g_camera_target_mac_known = true;
    }
    Serial.printf(
        "[camera-provisioning] health report request=%u flags=%lu camera_role=%s camera_index=%u from %s\n",
        static_cast<unsigned int>(packet.request_id),
        static_cast<unsigned long>(flags),
        camera_role == 0 ? "unknown" : espnow_camera_role_label(camera_role),
        static_cast<unsigned int>(camera_index),
        mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
    if (wifi_ready && node_registered && config_ready && !g_camera_runtime_ready) {
      g_camera_runtime_ready = true;
      Serial.println("[camera-provisioning] camera runtime is ready; first capture will be requested now");
      g_camera_bootstrap_capture_active = false;
      g_camera_capture_schedule.has_sent_initial_request = false;
      g_camera_capture_schedule.last_capture_requested_ms = 0;
      g_side_camera_capture_schedule.has_sent_initial_request = false;
      g_side_camera_capture_schedule.last_capture_requested_ms = 0;
    }
    if (is_camera_capture_health) {
      clearCameraCaptureFlight();
    }
    if (is_pending_capture_health && wifi_ready && node_registered && config_ready) {
      Serial.printf(
          "[platform] capture health fallback command_id=%d request=%u flags=%lu camera_role=%s camera_index=%u\n",
          g_pending_capture_command.command_id,
          static_cast<unsigned int>(packet.request_id),
          static_cast<unsigned long>(flags),
          camera_role == 0 ? "unknown" : espnow_camera_role_label(camera_role),
          static_cast<unsigned int>(camera_index));
      queuePendingCaptureCommandResult("completed", "camera uploaded a new image");
    }
    return;
  }

  if (kind != EspNowMessageKind::kAck) {
    return;
  }

  if (command == EspNowCommandType::kProvisionStart &&
      espnow_handle_provisioning_ack(&g_camera_provisioning_session, mac_addr, packet)) {
    g_camera_provisioning_acknowledged =
        g_camera_provisioning_session.state == MasterProvisioningState::kSucceeded;
    const CameraProvisioningPayload provisioned_payload = g_camera_provisioning_session.payload;
    const bool provisioned_top_camera =
        provisioned_payload.camera_role == static_cast<uint8_t>(CameraRoleCode::kTop);
    if (g_camera_provisioning_acknowledged && mac_addr != nullptr) {
      memcpy(g_camera_target_mac, mac_addr, sizeof(g_camera_target_mac));
      g_camera_target_mac_known = true;
    }
    if (g_camera_provisioning_acknowledged && g_camera_provisioning_manual_active) {
      g_camera_provisioning_manual_active = false;
      g_camera_provisioning_manual_deadline_ms = 0;
      memset(g_camera_provisioning_target_mac, 0, sizeof(g_camera_provisioning_target_mac));
      g_camera_provisioning_target_mac_known = false;
    }
    if (g_camera_provisioning_acknowledged && provisioned_top_camera && !g_camera_runtime_ready &&
        PLANTLAB_CAMERA_CAPTURE_ENABLED != 0) {
      g_camera_bootstrap_capture_active = true;
      g_camera_bootstrap_capture_attempts = 0;
      g_next_camera_bootstrap_capture_ms = millis();
      Serial.println("[camera-schedule] bootstrap capture window armed after provisioning ACK");
    }
    Serial.printf(
        "[camera-provisioning] ACK request=%u command=%s status=%s camera_index=%u role=%s from %s\n",
        static_cast<unsigned int>(packet.request_id),
        espnowCommandToString(command),
        espnowAckToString(static_cast<EspNowAckStatus>(packet.ack_status)),
        static_cast<unsigned int>(provisioned_payload.camera_node_index),
        espnow_camera_role_label(provisioned_payload.camera_role),
        mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
    return;
  }

  if (command != EspNowCommandType::kCaptureImage) {
    return;
  }

  const EspNowAckStatus ack_status = static_cast<EspNowAckStatus>(packet.ack_status);
  const bool is_camera_capture_ack =
      g_camera_capture_in_flight.active && packet.request_id == g_camera_capture_in_flight.request_id;
  const bool is_pending_capture_ack = g_pending_capture_command.active &&
                                      g_pending_capture_command.dispatched &&
                                      packet.request_id == g_pending_capture_command.request_id;
  const unsigned long capture_wait_ms =
      is_pending_capture_ack ? millis() - g_pending_capture_command.started_at_ms : 0;
  if (ack_status == EspNowAckStatus::kOk) {
    if (mac_addr != nullptr) {
      memcpy(g_camera_target_mac, mac_addr, sizeof(g_camera_target_mac));
      g_camera_target_mac_known = true;
    }
    if (!g_camera_runtime_ready) {
      g_camera_runtime_ready = true;
      Serial.println("[camera-schedule] capture ACK confirms camera runtime is ready");
    }
    if (is_camera_capture_ack && g_camera_bootstrap_capture_active) {
      capture_schedule_mark_requested(&g_camera_capture_schedule, millis());
    }
    g_camera_bootstrap_capture_active = false;
  }
  if (is_camera_capture_ack) {
    clearCameraCaptureFlight();
  }

  if (is_pending_capture_ack) {
    Serial.printf(
        "[platform] capture ACK command_id=%d request=%u ack_command_id=%lu upload_ms=%lu status=%s waited_ms=%lu\n",
        g_pending_capture_command.command_id,
        static_cast<unsigned int>(packet.request_id),
        static_cast<unsigned long>(packet.value_u32_1),
        static_cast<unsigned long>(packet.value_u32_2),
        espnowAckToString(ack_status),
        static_cast<unsigned long>(capture_wait_ms));
    queuePendingCaptureCommandResult(
        ack_status == EspNowAckStatus::kOk ? "completed" : "failed",
        manualCaptureAckMessage(ack_status));
  }

  Serial.printf(
      "[camera-schedule] ACK request=%u command=%s status=%s ack_command_id=%lu upload_ms=%lu from %s\n",
      static_cast<unsigned int>(packet.request_id),
      espnowCommandToString(command),
      espnowAckToString(ack_status),
      static_cast<unsigned long>(packet.value_u32_1),
      static_cast<unsigned long>(packet.value_u32_2),
      mac_addr != nullptr ? macToString(mac_addr).c_str() : "<unknown>");
}

bool setupEspNow() {
  if (g_espnow_ready || !hasWifiCredentials() || g_provisioning_mode) {
    return g_espnow_ready;
  }

  if (esp_now_init() != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_init_failed", "ESP-NOW init failed");
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
      ++g_diagnostic_error_counters.espnow_failures;
      recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
      Serial.println("[camera-schedule] failed to add broadcast ESP-NOW peer");
      esp_now_deinit();
      return false;
    }
  }

  g_espnow_ready = true;
  Serial.println("[camera-schedule] ESP-NOW ready");
  return true;
}

void teardownEspNow(const char* reason) {
  if (!g_espnow_ready) {
    return;
  }
  g_espnow_ready = false;
  g_last_espnow_send = EspNowSendContext{};
  esp_now_deinit();
  Serial.printf(
      "[camera-schedule] ESP-NOW stopped reason=%s\n",
      reason != nullptr && strlen(reason) > 0 ? reason : "unspecified");
}

bool ensureEspNowPeer(const uint8_t* peer_mac) {
  if (peer_mac == nullptr) {
    return false;
  }
  if (esp_now_is_peer_exist(peer_mac)) {
    return true;
  }

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, peer_mac, 6);
  peer.channel = 0;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
    Serial.printf("[camera-schedule] failed to add ESP-NOW peer %s\n", macToString(peer_mac).c_str());
    return false;
  }
  return true;
}

bool sendCameraProvisioningPacket(unsigned long now) {
  if (!g_espnow_ready || !espnow_should_send_provisioning_packet(g_camera_provisioning_session)) {
    return false;
  }
  if (!ensureEspNowPeer(g_camera_provisioning_session.target_mac)) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "camera provisioning peer add failed");
    return false;
  }

  EspNowPacket packet{};
  espnow_build_provisioning_packet(g_camera_provisioning_session, now, &packet);
  const esp_err_t err = esp_now_send(
      g_camera_provisioning_session.target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_provision_send_failed", "camera provisioning delivery failed");
    Serial.printf("[camera-provisioning] provisioning send failed err=%d\n", static_cast<int>(err));
    return false;
  }

  noteEspNowSend(
      EspNowCommandType::kProvisionStart,
      packet.request_id,
      0,
      g_camera_provisioning_session.target_mac,
      now);
  espnow_mark_provisioning_packet_sent(&g_camera_provisioning_session, now);
  Serial.printf(
      "[camera-provisioning] request=%u sent camera_index=%u role=%s target=%s\n",
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned int>(g_camera_provisioning_session.payload.camera_node_index),
      espnow_camera_role_label(g_camera_provisioning_session.payload.camera_role),
      macToString(g_camera_provisioning_session.target_mac).c_str());
  return true;
}

void serviceCameraProvisioning(unsigned long now) {
  const bool runtime_ready =
      g_espnow_ready && g_wifi_ready && platform_enabled() && !g_provisioning_mode;
  if (!runtime_ready || g_camera_provisioning_acknowledged) {
    return;
  }
  if (g_camera_provisioning_manual_active &&
      static_cast<long>(now - g_camera_provisioning_manual_deadline_ms) >= 0) {
    Serial.println("[camera-provisioning] manual provisioning window expired; provisioning stopped");
    stopCameraProvisioning("manual window expired");
    return;
  }
  if (!g_camera_provisioning_manual_active && !g_camera_auto_provisioning_enabled) {
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
    const CameraProvisioningSlotConfig& slot = activeCameraProvisioningSlot();
    if (!buildCameraProvisioningPayload(&payload, slot)) {
      return;
    }
    espnow_start_provisioning_session(
        &g_camera_provisioning_session,
        activeCameraProvisioningTargetMac(),
        g_next_espnow_request_id++,
        payload,
        now,
        1500UL,
        3);
    g_last_camera_provisioning_attempt_ms = now;
  }

  sendCameraProvisioningPacket(now);
}

bool sendEspNowCaptureCommand(
    uint32_t now,
    bool retry_available = true,
    bool mark_schedule = true,
    uint8_t camera_role = static_cast<uint8_t>(CameraRoleCode::kTop)) {
  if (!g_espnow_ready || g_camera_capture_in_flight.active) {
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
  packet.value_u32_1 = 0;
  packet.value_u32_2 = camera_role;

  const uint8_t* target_mac = kEspNowBroadcastMac;
  if (!ensureEspNowPeer(target_mac)) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
    return false;
  }
  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_send_failed", "camera request delivery failed");
    Serial.printf("[camera-schedule] capture send failed err=%d\n", static_cast<int>(err));
    return false;
  }

  noteEspNowSend(EspNowCommandType::kCaptureImage, packet.request_id, 0, target_mac, now);
  MasterCaptureScheduleState* schedule = captureScheduleForRole(camera_role);
  if (mark_schedule) {
    capture_schedule_mark_requested(schedule, now);
  }
  markCameraCaptureInFlight(packet.request_id, 0, now, retry_available && !g_scheduled_capture_retry_pending, camera_role);
  Serial.printf(
      "[camera-schedule] capture request=%u sent interval_ms=%lu camera_role=%s target=%s\n",
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned long>(schedule->interval_ms),
      camera_role == 0 ? "any" : espnow_camera_role_label(camera_role),
      macToString(target_mac).c_str());
  return true;
}

bool sendEspNowCaptureCommand(
    uint32_t now,
    uint32_t* request_id_out,
    int command_id = 0,
    uint8_t camera_role = static_cast<uint8_t>(CameraRoleCode::kTop)) {
  if (!g_espnow_ready || g_camera_capture_in_flight.active) {
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
  packet.value_u32_1 = command_id > 0 ? static_cast<uint32_t>(command_id) : 0;
  packet.value_u32_2 = camera_role;

  const uint8_t* target_mac = kEspNowBroadcastMac;
  if (!ensureEspNowPeer(target_mac)) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
    return false;
  }
  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_send_failed", "camera request delivery failed");
    Serial.printf("[camera-schedule] capture send failed err=%d\n", static_cast<int>(err));
    return false;
  }

  noteEspNowSend(EspNowCommandType::kCaptureImage, packet.request_id, command_id, target_mac, now);
  if (request_id_out != nullptr) {
    *request_id_out = packet.request_id;
  }
  markCameraCaptureInFlight(packet.request_id, command_id, now, false, camera_role);

  Serial.printf(
      "[camera-schedule] capture request=%u command_id=%lu interval_ms=%lu camera_role=%s target=%s\n",
      static_cast<unsigned int>(packet.request_id),
      static_cast<unsigned long>(packet.value_u32_1),
      static_cast<unsigned long>(captureScheduleForRole(camera_role)->interval_ms),
      camera_role == 0 ? "any" : espnow_camera_role_label(camera_role),
      macToString(target_mac).c_str());
  return true;
}

bool sendEspNowPauseCaptureCommand(bool paused) {
  if (!g_espnow_ready) {
    return false;
  }

  EspNowPacket packet{};
  packet.magic = ESPNOW_TEST_MAGIC;
  packet.version = ESPNOW_TEST_VERSION;
  packet.kind = static_cast<uint8_t>(EspNowMessageKind::kCommand);
  packet.command = static_cast<uint8_t>(EspNowCommandType::kPauseCapture);
  packet.ack_status = static_cast<uint8_t>(EspNowAckStatus::kOk);
  packet.request_id = g_next_espnow_request_id++;
  packet.timestamp_ms = millis();
  packet.value_u32_1 = paused ? 1u : 0u;
  packet.value_u32_2 = 0u;

  const uint8_t* target_mac = g_camera_target_mac_known ? g_camera_target_mac : kEspNowBroadcastMac;
  if (!ensureEspNowPeer(target_mac)) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_peer_failed", "ESP-NOW peer add failed");
    return false;
  }

  const esp_err_t err = esp_now_send(
      target_mac,
      reinterpret_cast<const uint8_t*>(&packet),
      sizeof(packet));
  if (err != ESP_OK) {
    ++g_diagnostic_error_counters.espnow_failures;
    recordDiagnosticError("espnow_send_failed", "camera pause delivery failed");
    Serial.printf("[camera-schedule] pause command send failed err=%d paused=%u\n", static_cast<int>(err), paused ? 1u : 0u);
    return false;
  }

  noteEspNowSend(
      EspNowCommandType::kPauseCapture,
      packet.request_id,
      0,
      target_mac,
      packet.timestamp_ms);
  Serial.printf(
      "[camera-schedule] pause command sent request=%u paused=%u target=%s\n",
      static_cast<unsigned int>(packet.request_id),
      paused ? 1u : 0u,
      macToString(target_mac).c_str());
  return true;
}

void setCameraSchedulePausedForManual(bool paused) {
  if (g_camera_schedule_paused_for_manual == paused) {
    return;
  }
  g_camera_schedule_paused_for_manual = paused;
  if (!sendEspNowPauseCaptureCommand(paused)) {
    Serial.printf(
        "[camera-schedule] failed to notify camera about paused=%u; local schedule state still updated\n",
        paused ? 1u : 0u);
  }
}

const char* manualCaptureAckMessage(EspNowAckStatus ack_status) {
  switch (ack_status) {
    case EspNowAckStatus::kOk:
      return "camera uploaded a new image";
    case EspNowAckStatus::kBusy:
      return "camera is busy capturing another image";
    case EspNowAckStatus::kUnsupported:
      return "camera firmware does not support manual capture";
    case EspNowAckStatus::kInvalid:
      return "camera rejected the capture request";
    case EspNowAckStatus::kFailed:
    default:
      return "camera capture failed";
  }
}

MasterCaptureScheduleState* captureScheduleForRole(uint8_t camera_role) {
  if (camera_role == static_cast<uint8_t>(CameraRoleCode::kSide)) {
    return &g_side_camera_capture_schedule;
  }
  return &g_camera_capture_schedule;
}

void clearPendingCaptureCommand() {
  g_pending_capture_command = PendingCaptureCommand{};
}

void clearCameraCaptureFlight() {
  g_camera_capture_in_flight = CameraCaptureFlight{};
  g_ambient_led_belt.resumeAfterCameraCapture(millis());
}

void markCameraCaptureInFlight(
    uint32_t request_id,
    int command_id,
    unsigned long now,
    bool retry_available,
    uint8_t camera_role) {
  g_ambient_led_belt.suspendForCameraCapture(now);
  g_camera_capture_in_flight.active = true;
  g_camera_capture_in_flight.delivery_failed = false;
  g_camera_capture_in_flight.retry_available = retry_available;
  g_camera_capture_in_flight.request_id = request_id;
  g_camera_capture_in_flight.command_id = command_id;
  g_camera_capture_in_flight.camera_role = camera_role;
  g_camera_capture_in_flight.started_at_ms = now;
  g_camera_capture_in_flight.last_delivery_failure_ms = 0;
}

void scheduleScheduledCaptureRetry(unsigned long now, uint8_t camera_role, const char* reason) {
  if (g_scheduled_capture_retry_pending) {
    return;
  }
  g_scheduled_capture_retry_pending = true;
  g_scheduled_capture_retry_at_ms = now + kScheduledCaptureRetryDelayMs;
  g_scheduled_capture_retry_camera_role = camera_role == 0 ? static_cast<uint8_t>(CameraRoleCode::kTop) : camera_role;
  Serial.printf(
      "[camera-schedule] scheduled capture retry queued role=%s reason=%s delay_ms=%lu\n",
      espnow_camera_role_label(g_scheduled_capture_retry_camera_role),
      reason == nullptr ? "unknown" : reason,
      static_cast<unsigned long>(kScheduledCaptureRetryDelayMs));
}

void queuePendingCaptureCommandResult(const char* status, const String& message) {
  if (!g_pending_capture_command.active) {
    return;
  }

  const String next_status = status == nullptr ? "failed" : String(status);
  recordLastCommandResult(
      g_pending_capture_command.command_id,
      next_status.c_str(),
      message,
      next_status == "completed" ? "ok" : "camera_capture_failed");
  if (next_status != "completed") {
    recordDiagnosticError("camera_capture_failed", message);
  }
  if (g_pending_capture_command.result_ready &&
      g_pending_capture_command.result_status == next_status &&
      g_pending_capture_command.result_message == message) {
    return;
  }

  g_pending_capture_command.result_ready = true;
  g_pending_capture_command.result_status = next_status;
  g_pending_capture_command.result_message = message;
  g_pending_capture_command.last_result_attempt_ms = 0;
}

void flushPendingCaptureCommandResult() {
  if (!g_pending_capture_command.active) {
    return;
  }
  if (!platform_enabled()) {
    clearPendingCaptureCommand();
    return;
  }

  setCameraSchedulePausedForManual(false);

  const char* error_code =
      g_pending_capture_command.result_status == "completed" ? nullptr : PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR;
  if (!reportPendingCaptureCommandResult(
          g_pending_capture_command.result_status.c_str(),
          g_pending_capture_command.result_message.c_str(),
          error_code)) {
    g_pending_capture_command.last_result_attempt_ms = millis();
    Serial.printf(
        "[platform] capture command result update failed: %s (will retry %s: %s)\n",
        g_pending_capture_command.contract_native ? "contract result upload failed" : "legacy result upload failed",
        g_pending_capture_command.result_status.c_str(),
        g_pending_capture_command.result_message.c_str());
    return;
  }
  Serial.printf(
      "[platform] capture command %d marked %s: %s\n",
      g_pending_capture_command.command_id,
      g_pending_capture_command.result_status.c_str(),
      g_pending_capture_command.result_message.c_str());
  clearPendingCaptureCommand();
}

void markPendingCaptureCommandInProgress(int command_id) {
  if (!platform_enabled()) {
    return;
  }

  Serial.printf("[platform] capture command %d marked in_progress\n", command_id);
  recordLastCommandResult(command_id, "in_progress", "waiting for camera upload", "camera_capture_started");

  if (g_pending_capture_command.active &&
      g_pending_capture_command.command_id == command_id &&
      !reportPendingCaptureCommandResult(
          PLANTLAB_COMMAND_STATUS_IN_PROGRESS,
          "waiting for camera upload")) {
    Serial.println("[platform] capture command progress update failed");
  }
}

uint8_t cameraRoleCodeFromString(const String& value) {
  String normalized = value;
  normalized.trim();
  normalized.toLowerCase();
  if (normalized == "top") {
    return static_cast<uint8_t>(CameraRoleCode::kTop);
  }
  if (normalized == "side") {
    return static_cast<uint8_t>(CameraRoleCode::kSide);
  }
  return 0;
}

bool startPendingCaptureCommand(const PlatformCommand& command, unsigned long now) {
  if (g_pending_capture_command.active) {
    Serial.printf(
        "[platform] capture command %d cannot start while command %d is still pending\n",
        command.id,
        g_pending_capture_command.command_id);
    if (!reportPlatformCommandResult(
            command,
            PLANTLAB_COMMAND_STATUS_FAILED,
            "capture already in progress",
            PLANTLAB_COMMAND_ERROR_DEVICE_BUSY)) {
      Serial.println("[platform] overlapping capture command update failed");
    }
    return false;
  }

  setCameraSchedulePausedForManual(true);

  g_pending_capture_command.active = true;
  g_pending_capture_command.dispatched = false;
  g_pending_capture_command.result_ready = false;
  g_pending_capture_command.dispatch_attempts = 0;
  g_pending_capture_command.command_id = command.id;
  g_pending_capture_command.contract_native = command.contract_native;
  g_pending_capture_command.contract_command_id = command.command_id;
  g_pending_capture_command.contract_command_type = command.command_type;
  g_pending_capture_command.camera_role = cameraRoleCodeFromString(
      command.target_camera_role.length() > 0 ? command.target_camera_role : command.value);
  g_pending_capture_command.request_id = 0;
  g_pending_capture_command.started_at_ms = now;
  g_pending_capture_command.last_result_attempt_ms = 0;
  g_pending_capture_command.result_status = "";
  g_pending_capture_command.result_message = "";
  markPendingCaptureCommandInProgress(command.id);

  if (g_camera_capture_in_flight.active) {
    Serial.printf(
        "[platform] capture command %d waiting for in-flight camera request=%u command_id=%d\n",
        command.id,
        static_cast<unsigned int>(g_camera_capture_in_flight.request_id),
        g_camera_capture_in_flight.command_id);
    return true;
  }

  return dispatchPendingCaptureCommand(now);
}

bool dispatchPendingCaptureCommand(unsigned long now) {
  if (!g_pending_capture_command.active || g_pending_capture_command.dispatched) {
    return false;
  }

  uint32_t request_id = 0;
  if (!sendEspNowCaptureCommand(
          now,
          &request_id,
          g_pending_capture_command.command_id,
          g_pending_capture_command.camera_role)) {
    const String message =
        g_camera_target_mac_known ? "failed to send capture request to camera" : "camera node is not reachable";
    if (!reportPendingCaptureCommandResult(
            PLANTLAB_COMMAND_STATUS_FAILED,
            message.c_str(),
            PLANTLAB_COMMAND_ERROR_TRANSPORT_ERROR)) {
      Serial.println("[platform] capture command failure update failed");
    }
    Serial.printf(
        "[platform] capture command %d failed to start: %s\n",
        g_pending_capture_command.command_id,
        message.c_str());
    setCameraSchedulePausedForManual(false);
    clearPendingCaptureCommand();
    return false;
  }

  g_pending_capture_command.dispatch_attempts =
      static_cast<uint8_t>(g_pending_capture_command.dispatch_attempts + 1);
  g_pending_capture_command.dispatched = true;
  g_pending_capture_command.request_id = request_id;
  Serial.printf(
      "[platform] capture command %d forwarded to camera request=%u camera_role=%s target=%s at_ms=%lu\n",
      g_pending_capture_command.command_id,
      static_cast<unsigned int>(request_id),
      g_pending_capture_command.camera_role == 0 ? "any" : espnow_camera_role_label(g_pending_capture_command.camera_role),
      "broadcast",
      static_cast<unsigned long>(now));
  return true;
}

void serviceCameraCaptureFlight(unsigned long now) {
  if (!g_camera_capture_in_flight.active) {
    return;
  }
  if (g_camera_capture_in_flight.delivery_failed &&
      now - g_camera_capture_in_flight.last_delivery_failure_ms >= 500UL) {
    const bool is_pending_backend_capture = g_pending_capture_command.active &&
                                            g_pending_capture_command.dispatched &&
                                            g_pending_capture_command.request_id ==
                                                g_camera_capture_in_flight.request_id;
    const int failed_command_id = g_camera_capture_in_flight.command_id;
    const uint32_t failed_request_id = g_camera_capture_in_flight.request_id;
    const bool retry_available = g_camera_capture_in_flight.retry_available;
    const uint8_t failed_camera_role = g_camera_capture_in_flight.camera_role;
    clearCameraCaptureFlight();
    if (is_pending_backend_capture && g_pending_capture_command.dispatch_attempts < kManualCaptureMaxDispatchAttempts) {
      Serial.printf(
          "[platform] capture command %d request=%u send failed, retrying attempt=%u\n",
          g_pending_capture_command.command_id,
          static_cast<unsigned int>(failed_request_id),
          static_cast<unsigned int>(g_pending_capture_command.dispatch_attempts + 1));
      g_pending_capture_command.dispatched = false;
      g_pending_capture_command.request_id = 0;
      return;
    }
    if (is_pending_backend_capture) {
      queuePendingCaptureCommandResult("failed", "camera request delivery failed");
      return;
    }
    Serial.printf(
        "[camera-schedule] capture request=%u command_id=%d delivery failed, clearing in-flight state\n",
        static_cast<unsigned int>(failed_request_id),
        failed_command_id);
    if (failed_command_id == 0 && retry_available) {
      scheduleScheduledCaptureRetry(now, failed_camera_role, "delivery_failed");
    }
    return;
  }
  const uint32_t capture_timeout_ms =
      g_camera_capture_in_flight.command_id > 0 ? kManualCaptureAttemptTimeoutMs : kCameraCaptureFlightTimeoutMs;
  if (now - g_camera_capture_in_flight.started_at_ms < capture_timeout_ms) {
    return;
  }
  Serial.printf(
      "[camera-schedule] capture request=%u command_id=%d timed out after %lu ms without ACK/health\n",
      static_cast<unsigned int>(g_camera_capture_in_flight.request_id),
      g_camera_capture_in_flight.command_id,
      static_cast<unsigned long>(now - g_camera_capture_in_flight.started_at_ms));

  const bool is_pending_backend_capture = g_pending_capture_command.active &&
                                          g_pending_capture_command.dispatched &&
                                          g_pending_capture_command.request_id ==
                                              g_camera_capture_in_flight.request_id;
  const int timed_out_command_id = g_camera_capture_in_flight.command_id;
  const uint32_t timed_out_request_id = g_camera_capture_in_flight.request_id;
  const bool retry_available = g_camera_capture_in_flight.retry_available;
  const uint8_t timed_out_camera_role = g_camera_capture_in_flight.camera_role;
  clearCameraCaptureFlight();
  if (is_pending_backend_capture) {
    if (g_pending_capture_command.dispatch_attempts < kManualCaptureMaxDispatchAttempts) {
      Serial.printf(
          "[platform] capture command %d request=%u had no response, retrying attempt=%u\n",
          g_pending_capture_command.command_id,
          static_cast<unsigned int>(timed_out_request_id),
          static_cast<unsigned int>(g_pending_capture_command.dispatch_attempts + 1));
      g_pending_capture_command.dispatched = false;
      g_pending_capture_command.request_id = 0;
      return;
    }
    queuePendingCaptureCommandResult("failed", "timed out waiting for camera acknowledgement");
    return;
  }
  if (timed_out_command_id > 0) {
    Serial.printf(
        "[camera-schedule] manual capture request=%u exhausted retry window without backend command match\n",
        static_cast<unsigned int>(timed_out_request_id));
  }
  if (timed_out_command_id == 0 && retry_available) {
    scheduleScheduledCaptureRetry(now, timed_out_camera_role, "timeout");
  }
}

void servicePendingCaptureCommand(unsigned long now) {
  if (!g_pending_capture_command.active) {
    return;
  }
  if (g_pending_capture_command.result_ready) {
    if (g_pending_capture_command.last_result_attempt_ms == 0 ||
        now - g_pending_capture_command.last_result_attempt_ms >= kCaptureResultRetryMs) {
      flushPendingCaptureCommandResult();
    }
    return;
  }
  if (!g_pending_capture_command.dispatched) {
    if (!g_camera_capture_in_flight.active) {
      dispatchPendingCaptureCommand(now);
    }
    if (g_pending_capture_command.dispatched) {
      return;
    }
    if (now - g_pending_capture_command.started_at_ms < kManualCaptureAckTimeoutMs) {
      return;
    }
    Serial.printf(
        "[platform] capture command %d timed out after %lu ms waiting for camera availability\n",
        g_pending_capture_command.command_id,
        static_cast<unsigned long>(now - g_pending_capture_command.started_at_ms));
    queuePendingCaptureCommandResult("failed", "timed out waiting for camera availability");
    return;
  }
  if (now - g_pending_capture_command.started_at_ms < kManualCaptureAckTimeoutMs) {
    return;
  }
  Serial.printf(
      "[platform] capture command %d request=%u timed out after %lu ms waiting for camera ACK/upload\n",
      g_pending_capture_command.command_id,
      static_cast<unsigned int>(g_pending_capture_command.request_id),
      static_cast<unsigned long>(now - g_pending_capture_command.started_at_ms));
  queuePendingCaptureCommandResult("failed", "timed out waiting for camera upload acknowledgement");
}

void maybeSendBootstrapCapture(unsigned long now) {
  if (!kCameraScheduledCaptureEnabled) {
    return;
  }
  if (!g_camera_bootstrap_capture_active || g_provisioning_mode || !g_espnow_ready || !g_wifi_ready ||
      !platform_enabled() || g_pending_capture_command.active || g_camera_capture_in_flight.active) {
    return;
  }
  if (g_camera_runtime_ready) {
    g_camera_bootstrap_capture_active = false;
    return;
  }
  if (g_camera_bootstrap_capture_attempts >= kCameraBootstrapCaptureMaxAttempts) {
    g_camera_bootstrap_capture_active = false;
    Serial.println("[camera-schedule] bootstrap capture window expired");
    return;
  }
  if (now < g_next_camera_bootstrap_capture_ms) {
    return;
  }
  if (sendEspNowCaptureCommand(now, false, false)) {
    g_camera_bootstrap_capture_attempts =
        static_cast<uint8_t>(g_camera_bootstrap_capture_attempts + 1);
    g_next_camera_bootstrap_capture_ms = now + kCameraBootstrapCaptureRetryMs;
    Serial.printf(
        "[camera-schedule] bootstrap capture attempt=%u/%u\n",
        static_cast<unsigned int>(g_camera_bootstrap_capture_attempts),
        static_cast<unsigned int>(kCameraBootstrapCaptureMaxAttempts));
  }
}

bool sendScheduledCaptureForRole(unsigned long now, uint8_t camera_role, const char* retry_reason) {
  if (sendEspNowCaptureCommand(now, true, true, camera_role)) {
    return true;
  }
  scheduleScheduledCaptureRetry(now, camera_role, retry_reason);
  return false;
}

void pollCameraCaptureSchedule(unsigned long now) {
  if (!kCameraScheduledCaptureEnabled) {
    return;
  }
  if (g_camera_schedule_paused_for_manual || g_pending_capture_command.active ||
      g_camera_capture_in_flight.active) {
    return;
  }
  maybeSendBootstrapCapture(now);

  const bool runtime_ready =
      g_espnow_ready && g_wifi_ready && platform_enabled() && !g_provisioning_mode &&
      g_camera_runtime_ready;
  const uint8_t side_camera_role = static_cast<uint8_t>(CameraRoleCode::kSide);
  if (capture_schedule_should_request(g_side_camera_capture_schedule, now, runtime_ready)) {
    sendScheduledCaptureForRole(now, side_camera_role, "side_send_failed");
    return;
  }

  if (g_scheduled_capture_retry_pending) {
    if (now < g_scheduled_capture_retry_at_ms) {
      return;
    }
    const uint8_t retry_camera_role = g_scheduled_capture_retry_camera_role;
    if (sendEspNowCaptureCommand(now, true, true, retry_camera_role)) {
      g_scheduled_capture_retry_pending = false;
      Serial.printf(
          "[camera-schedule] scheduled capture retry sent role=%s\n",
          espnow_camera_role_label(retry_camera_role));
    } else {
      g_scheduled_capture_retry_pending = false;
      Serial.printf(
          "[camera-schedule] scheduled capture retry send failed role=%s, waiting for next interval\n",
          espnow_camera_role_label(retry_camera_role));
    }
    return;
  }

  if (!capture_schedule_should_request(g_camera_capture_schedule, now, runtime_ready)) {
    return;
  }
  sendScheduledCaptureForRole(now, static_cast<uint8_t>(CameraRoleCode::kTop), "top_send_failed");
}

void updateStatusLed() {
  if (g_provisioning_state == plantlab::ProvisioningState::PROVISIONING_BLE) {
    g_status_led.set_mode(StatusLedMode::kProvisioning);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::PROVISIONING_COMMITTING) {
    g_status_led.set_mode(StatusLedMode::kBooting);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::WIFI_CONNECTING) {
    g_status_led.set_mode(StatusLedMode::kBooting);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::BACKEND_REGISTERING) {
    g_status_led.set_mode(g_wifi_ready ? StatusLedMode::kNormal : StatusLedMode::kBooting);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::PROVISIONING_FAILED) {
    g_status_led.set_mode(StatusLedMode::kError);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::PROVISIONING_SUCCESS) {
    g_status_led.set_mode(StatusLedMode::kNormal);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::FALLBACK_SOFTAP) {
    g_status_led.set_mode(StatusLedMode::kFallback);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::FACTORY_RESET_PENDING) {
    g_status_led.set_mode(StatusLedMode::kFactoryReset);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::PROVISIONING_FAILED) {
    g_status_led.set_mode(StatusLedMode::kError);
    return;
  }
  if (g_provisioning_state == plantlab::ProvisioningState::FALLBACK_SOFTAP) {
    g_status_led.set_mode(StatusLedMode::kFallback);
    return;
  }

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
      g_status_led.set_mode(StatusLedMode::kError);
      break;
    case DeviceMode::kBooting:
    default:
      g_status_led.set_mode(StatusLedMode::kBooting);
      break;
  }
}

const char* wifiStatusLabel(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS:
      return "idle";
    case WL_NO_SSID_AVAIL:
      return "no_ssid";
    case WL_SCAN_COMPLETED:
      return "scan_completed";
    case WL_CONNECTED:
      return "connected";
    case WL_CONNECT_FAILED:
      return "connect_failed";
    case WL_CONNECTION_LOST:
      return "connection_lost";
    case WL_DISCONNECTED:
      return "disconnected";
    default:
      return "unknown";
  }
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

void recordLastCommandResult(int command_id, const char* status, const String& message, const char* code) {
  g_last_command_id = command_id;
  g_last_command_status = status == nullptr ? "" : String(status);
  g_last_command_code = code == nullptr ? "" : String(code);
  g_last_command_message = message;
  if (g_last_command_message.length() > 120) {
    g_last_command_message = g_last_command_message.substring(0, 120);
  }
  g_last_command_result_ms = millis();
}

void recordCommandPollResult(
    const char* status,
    const String& error,
    unsigned long started_at_ms,
    unsigned long finished_at_ms) {
  g_last_command_poll_completed_ms = finished_at_ms;
  g_last_command_poll_latency_ms =
      finished_at_ms >= started_at_ms ? static_cast<uint32_t>(finished_at_ms - started_at_ms) : 0;
  g_last_command_poll_status = status == nullptr || strlen(status) == 0 ? "unknown" : String(status);
  g_last_command_poll_error = error;
  if (g_last_command_poll_error.length() > 120) {
    g_last_command_poll_error = g_last_command_poll_error.substring(0, 120);
  }
  char timestamp[32]{};
  plantlab::time_sync::currentUtcIso8601(timestamp, sizeof(timestamp));
  g_last_command_poll_at_iso = timestamp;
}

plantlab::ProvisioningParseError bleWifiValidationErrorForStatus(wl_status_t status) {
  if (status == WL_NO_SSID_AVAIL) {
    return plantlab::ProvisioningParseError::kWifiNetworkNotFound;
  }
  if (status == WL_CONNECT_FAILED) {
    return plantlab::ProvisioningParseError::kWifiConnectFailed;
  }
  return plantlab::ProvisioningParseError::kWifiConnectTimeout;
}

bool validateBleWifiCredentials(const plantlab::BleProvisioningPayload& payload, plantlab::ProvisioningParseError* error) {
  if (error != nullptr) {
    *error = plantlab::ProvisioningParseError::kNone;
  }
  if (g_ble_wifi_scan_active) {
    resetBleWifiScanRuntime();
    stopBleWifiScanRadio();
  }

  const String ssid(payload.ssid.c_str());
  const String password(payload.password.c_str());
  Serial.printf(
      "[provisioning] validating Wi-Fi credentials over BLE ssid=%s password_len=%u\n",
      ssid.c_str(),
      static_cast<unsigned>(password.length()));
  Serial.printf("[provisioning] wifi_connecting ssid=%s\n", ssid.c_str());

  WiFi.disconnect(false, false);
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), password.c_str());

  const unsigned long started_at = millis();
  wl_status_t final_status = WiFi.status();
  while (millis() - started_at < PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    final_status = WiFi.status();
    if (final_status == WL_CONNECTED) {
      Serial.printf(
          "[provisioning] BLE Wi-Fi validation succeeded ip=%s elapsed_ms=%lu\n",
          WiFi.localIP().toString().c_str(),
          static_cast<unsigned long>(millis() - started_at));
      Serial.println("[provisioning] wifi_connected");
      return true;
    }
    checkProvisioningButton();
    g_status_led.update(millis());
    delay(250);
  }

  final_status = WiFi.status();
  WiFi.disconnect(false, false);
  WiFi.mode(WIFI_OFF);
  const plantlab::ProvisioningParseError validation_error = bleWifiValidationErrorForStatus(final_status);
  ++g_diagnostic_error_counters.ble_provisioning_failures;
  recordDiagnosticError("ble_wifi_validation_failed", plantlab::provisioningParseErrorCode(validation_error));
  if (error != nullptr) {
    *error = validation_error;
  }
  Serial.printf(
      "[provisioning] BLE Wi-Fi validation failed status=%s error=%s elapsed_ms=%lu\n",
      wifiStatusLabel(final_status),
      plantlab::provisioningParseErrorCode(validation_error),
      static_cast<unsigned long>(millis() - started_at));
  Serial.printf(
      "[provisioning] provisioning_failed reason=%s\n",
      plantlab::provisioningParseErrorCode(validation_error));
  return false;
}

void rejectBleProvisioningForRetry(plantlab::ProvisioningParseError error) {
  g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_BLE;
  g_device_mode = DeviceMode::kProvisioning;
  g_wifi_ready = false;
  g_ble_provisioning.setAcceptingWrites(true);
  g_ble_provisioning.setStatus(g_provisioning_state, error);
  updateStatusLed();
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

  DeviceConfig pending_config;
  g_previous_active_config = g_config;
  g_pending_provisioning_config_active = loadPendingConfig(&pending_config);
  if (g_pending_provisioning_config_active) {
    g_config = pending_config;
    Serial.println("[provisioning] pending provisioning config loaded for retry");
  }

  Serial.printf(
      "[provisioning] config loaded: ssid=%s password_len=%u claim_present=%u device_token_present=%u platform_id=%d backend=%s platform=%s pending=%u attach_target=%d\n",
      g_config.wifi_ssid.length() > 0 ? g_config.wifi_ssid.c_str() : "<empty>",
      static_cast<unsigned>(g_config.wifi_password.length()),
      g_config.claim_token.length() > 0 ? 1U : 0U,
      g_config.device_token.length() > 0 ? 1U : 0U,
      g_config.platform_device_id,
      g_config.backend_url.length() > 0 ? g_config.backend_url.c_str() : "<empty>",
      g_config.platform_url.length() > 0 ? g_config.platform_url.c_str() : "<empty>",
      g_pending_provisioning_config_active ? 1U : 0U,
      g_config.attach_to_platform_device_id);

  rebuildPlatformClient();
  return hasWifiCredentials();
}

void resetCameraProvisioningRuntime() {
  g_camera_provisioning_session = MasterProvisioningSession{};
  g_camera_provisioning_acknowledged = false;
  g_camera_provisioning_slot_id = CameraProvisioningSlotId::kTop;
  g_camera_provisioning_manual_active = false;
  g_camera_auto_provisioning_enabled = false;
  g_camera_provisioning_manual_deadline_ms = 0;
  memset(g_camera_provisioning_target_mac, 0, sizeof(g_camera_provisioning_target_mac));
  g_camera_provisioning_target_mac_known = false;
  g_camera_runtime_ready = false;
  g_last_camera_provisioning_attempt_ms = 0;
  g_camera_target_mac_known = false;
  memset(g_camera_target_mac, 0, sizeof(g_camera_target_mac));
  g_camera_bootstrap_capture_active = false;
  g_camera_bootstrap_capture_attempts = 0;
  g_next_camera_bootstrap_capture_ms = 0;
  g_scheduled_capture_retry_pending = false;
  g_scheduled_capture_retry_at_ms = 0;
  g_scheduled_capture_retry_camera_role = static_cast<uint8_t>(CameraRoleCode::kTop);
  capture_schedule_init(
      &g_camera_capture_schedule,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0,
      PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS,
      static_cast<uint32_t>(kTopCameraCapturePhaseSeconds) * 1000UL,
      millis());
  capture_schedule_init(
      &g_side_camera_capture_schedule,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0,
      PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS,
      static_cast<uint32_t>(kSideCameraCapturePhaseSeconds) * 1000UL,
      millis());
}

DeviceConfig normalizedConfig(DeviceConfig config) {
  config.wifi_ssid.trim();
  config.claim_token.trim();
  config.device_token.trim();
  config.backend_url.trim();
  config.platform_url.trim();
  return config;
}

bool loadPendingConfig(DeviceConfig* pending) {
  if (pending == nullptr) {
    return false;
  }
  if (!g_preferences.begin(kPreferencesNamespace, true)) {
    return false;
  }
  DeviceConfig candidate;
  candidate.wifi_ssid = g_preferences.getString(kConfigKeyPendingSsid, "");
  candidate.wifi_password = g_preferences.getString(kConfigKeyPendingPassword, "");
  candidate.claim_token = g_preferences.getString(kConfigKeyPendingClaimToken, "");
  candidate.backend_url = g_preferences.getString(kConfigKeyPendingBackendUrl, "");
  candidate.platform_url = g_preferences.getString(kConfigKeyPendingPlatformUrl, "");
  candidate.attach_to_platform_device_id = g_preferences.getInt(kConfigKeyPendingAttachDeviceId, 0);
  g_preferences.end();
  candidate = normalizedConfig(candidate);
  if (candidate.wifi_ssid.length() == 0 || candidate.claim_token.length() == 0) {
    return false;
  }
  *pending = candidate;
  return true;
}

bool stringPreferenceWriteOk(const String& value, size_t written) {
  return value.isEmpty() || written > 0;
}

bool saveConfigCandidate(const DeviceConfig& candidate) {
  const DeviceConfig normalized = normalizedConfig(candidate);

  Serial.println("[provisioning] saving config to Preferences");
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[provisioning] failed to open Preferences for write");
    return false;
  }
  const size_t ssid_written = g_preferences.putString(kConfigKeySsid, normalized.wifi_ssid);
  const size_t password_written =
      g_preferences.putString(kConfigKeyPassword, normalized.wifi_password);
  const size_t claim_token_written =
      g_preferences.putString(kConfigKeyClaimToken, normalized.claim_token);
  const size_t device_token_written =
      g_preferences.putString(kConfigKeyDeviceToken, normalized.device_token);
  const size_t backend_url_written =
      g_preferences.putString(kConfigKeyBackendUrl, normalized.backend_url);
  const size_t platform_url_written =
      g_preferences.putString(kConfigKeyPlatformUrl, normalized.platform_url);
  const size_t platform_id_written =
      g_preferences.putInt(kConfigKeyPlatformDeviceId, normalized.platform_device_id);
  g_preferences.end();

  const bool saved =
      stringPreferenceWriteOk(normalized.wifi_ssid, ssid_written) &&
      stringPreferenceWriteOk(normalized.wifi_password, password_written) &&
      stringPreferenceWriteOk(normalized.claim_token, claim_token_written) &&
      stringPreferenceWriteOk(normalized.device_token, device_token_written) &&
      stringPreferenceWriteOk(normalized.backend_url, backend_url_written) &&
      stringPreferenceWriteOk(normalized.platform_url, platform_url_written) &&
      platform_id_written == sizeof(normalized.platform_device_id);
  if (saved) {
    Serial.println("[provisioning] config saved");
    return true;
  }
  Serial.println("[provisioning] failed to save config");
  return false;
}

bool savePendingConfigCandidate(const DeviceConfig& candidate) {
  const DeviceConfig normalized = normalizedConfig(candidate);

  Serial.println("[provisioning] saving pending config to Preferences");
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    Serial.println("[provisioning] failed to open Preferences for pending write");
    return false;
  }
  const size_t ssid_written = g_preferences.putString(kConfigKeyPendingSsid, normalized.wifi_ssid);
  const size_t password_written = g_preferences.putString(kConfigKeyPendingPassword, normalized.wifi_password);
  const size_t claim_token_written = g_preferences.putString(kConfigKeyPendingClaimToken, normalized.claim_token);
  const size_t backend_url_written = g_preferences.putString(kConfigKeyPendingBackendUrl, normalized.backend_url);
  const size_t platform_url_written = g_preferences.putString(kConfigKeyPendingPlatformUrl, normalized.platform_url);
  const size_t attach_written = g_preferences.putInt(kConfigKeyPendingAttachDeviceId, normalized.attach_to_platform_device_id);
  g_preferences.end();

  const bool saved =
      stringPreferenceWriteOk(normalized.wifi_ssid, ssid_written) &&
      stringPreferenceWriteOk(normalized.wifi_password, password_written) &&
      stringPreferenceWriteOk(normalized.claim_token, claim_token_written) &&
      stringPreferenceWriteOk(normalized.backend_url, backend_url_written) &&
      stringPreferenceWriteOk(normalized.platform_url, platform_url_written) &&
      attach_written == sizeof(normalized.attach_to_platform_device_id);
  if (saved) {
    Serial.println("[provisioning] pending config saved");
    return true;
  }
  Serial.println("[provisioning] failed to save pending config");
  return false;
}

void clearPendingConfig() {
  if (!g_preferences.begin(kPreferencesNamespace, false)) {
    return;
  }
  g_preferences.remove(kConfigKeyPendingSsid);
  g_preferences.remove(kConfigKeyPendingPassword);
  g_preferences.remove(kConfigKeyPendingClaimToken);
  g_preferences.remove(kConfigKeyPendingBackendUrl);
  g_preferences.remove(kConfigKeyPendingPlatformUrl);
  g_preferences.remove(kConfigKeyPendingAttachDeviceId);
  g_preferences.end();
  g_pending_provisioning_config_active = false;
  g_previous_active_config = DeviceConfig{};
}

bool restorePreviousActiveConfigAfterPendingFailure(const char* reason) {
  if (!g_pending_provisioning_config_active) {
    return false;
  }
  if (g_previous_active_config.wifi_ssid.length() == 0) {
    Serial.printf("[provisioning] pending provisioning failed reason=%s; returning to BLE recovery\n", reason);
    g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_FAILED;
    updateStatusLed();
    requestBleProvisioningMode(millis());
    return true;
  }
  Serial.printf("[provisioning] pending provisioning failed reason=%s; restoring previous active config\n", reason);
  const DeviceConfig previous = g_previous_active_config;
  clearPendingConfig();
  g_config = previous;
  rebuildPlatformClient();
  g_device_mode = DeviceMode::kConnecting;
  g_provisioning_state = plantlab::ProvisioningState::WIFI_CONNECTING;
  g_last_wifi_attempt_ms = 0;
  updateStatusLed();
  return true;
}

bool saveConfig() {
  const DeviceConfig normalized = normalizedConfig(g_config);
  if (!saveConfigCandidate(normalized)) {
    return false;
  }
  g_config = normalized;
  rebuildPlatformClient();
  return true;
}

void clearConfig() {
  Serial.println("[provisioning] clearing config from Preferences");
  g_preferences.begin(kPreferencesNamespace, false);
  g_preferences.clear();
  g_preferences.end();
  g_config = DeviceConfig{};
  g_platform_client.reset();
  resetCameraProvisioningRuntime();
}

void addWifiNetworkOption(std::vector<WiFiNetworkOption>* networks, String ssid, int rssi) {
  ssid.trim();
  if (ssid.length() == 0) {
    return;
  }
  auto existing = std::find_if(
      networks->begin(),
      networks->end(),
      [&ssid](const WiFiNetworkOption& network) { return network.ssid == ssid; });
  if (existing == networks->end()) {
    WiFiNetworkOption network;
    network.ssid = ssid;
    network.rssi = rssi;
    networks->push_back(network);
  } else if (rssi > existing->rssi) {
    existing->rssi = rssi;
  }
}

void sortWifiNetworksBySignal(std::vector<WiFiNetworkOption>* networks) {
  std::sort(
      networks->begin(),
      networks->end(),
      [](const WiFiNetworkOption& left, const WiFiNetworkOption& right) {
        if (left.rssi == right.rssi) {
          return left.ssid < right.ssid;
        }
        return left.rssi > right.rssi;
      });
}

std::vector<WiFiNetworkOption> collectWifiScanResults(int network_count) {
  std::vector<WiFiNetworkOption> networks;
  for (int index = 0; index < network_count; ++index) {
    addWifiNetworkOption(&networks, WiFi.SSID(index), WiFi.RSSI(index));
  }
  sortWifiNetworksBySignal(&networks);
  return networks;
}

std::vector<WiFiNetworkOption> scanNearbyWifiNetworks() {
  std::vector<WiFiNetworkOption> networks;
  Serial.println("[provisioning] scanning nearby Wi-Fi for SoftAP setup");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, false);
  delay(200);

  const int network_count = WiFi.scanNetworks(false, true);
  if (network_count < 0) {
    Serial.printf("[provisioning] Wi-Fi scan failed: %d\n", network_count);
    WiFi.scanDelete();
    return networks;
  }

  networks = collectWifiScanResults(network_count);
  WiFi.scanDelete();
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

void handleWifiNetworksJson() {
  JsonDocument payload;
  JsonArray networks = payload["networks"].to<JsonArray>();
  for (const WiFiNetworkOption& network : g_cached_wifi_networks) {
    JsonObject item = networks.add<JsonObject>();
    item["ssid"] = network.ssid;
    item["rssi"] = network.rssi;
  }
  payload["count"] = networks.size();
  payload["source"] = "esp32-softap";

  String body;
  serializeJson(payload, body);
  g_web_server.sendHeader("Access-Control-Allow-Origin", "*");
  g_web_server.send(200, "application/json", body);
}

std::string buildBleWifiNetworksPayload(const std::vector<WiFiNetworkOption>& networks) {
  std::vector<plantlab::WifiNetworkOption> options;
  options.reserve(networks.size());
  for (const WiFiNetworkOption& network : networks) {
    options.push_back(plantlab::WifiNetworkOption{network.ssid.c_str(), network.rssi});
  }
  return plantlab::buildBleWifiNetworksJson(options, g_ble_wifi_scan_id, 0);
}

std::string buildBleWifiNetworksPayloadPage(const std::vector<WiFiNetworkOption>& networks, size_t cursor) {
  std::vector<plantlab::WifiNetworkOption> options;
  options.reserve(networks.size());
  for (const WiFiNetworkOption& network : networks) {
    options.push_back(plantlab::WifiNetworkOption{network.ssid.c_str(), network.rssi});
  }
  return plantlab::buildBleWifiNetworksJson(options, g_ble_wifi_scan_id, cursor);
}

void logBleWifiScanNetworks() {
  for (size_t index = 0; index < g_cached_wifi_networks.size(); ++index) {
    const WiFiNetworkOption& network = g_cached_wifi_networks[index];
    Serial.printf(
        "[provisioning] BLE Wi-Fi network[%u] rssi=%d ssid=%s\n",
        static_cast<unsigned>(index + 1),
        network.rssi,
        network.ssid.c_str());
  }
}

void publishBleWifiScanStatus(const char* status) {
  g_ble_provisioning.setWifiNetworksJson(
      plantlab::buildBleWifiNetworksStatusJson(status, g_ble_wifi_scan_id, g_cached_wifi_networks.size()));
}

void publishBleWifiScanPage(size_t cursor = 0) {
  const std::string payload = buildBleWifiNetworksPayloadPage(g_cached_wifi_networks, cursor);
  Serial.printf(
      "[provisioning] BLE Wi-Fi payload scan_id=%u cursor=%u bytes=%u\n",
      static_cast<unsigned>(g_ble_wifi_scan_id),
      static_cast<unsigned>(cursor),
      static_cast<unsigned>(payload.size()));
  g_ble_provisioning.setWifiNetworksJson(payload);
}

void stopBleWifiScanRadio() {
  WiFi.scanDelete();
  WiFi.disconnect(false, false);
}

void resetBleWifiScanRuntime() {
  g_ble_wifi_scan_active = false;
  g_ble_wifi_scan_retry_at_ms = 0;
  g_ble_wifi_scan_retry_count = 0;
}

void finishBleWifiScan(int network_count) {
  g_cached_wifi_networks = collectWifiScanResults(network_count);
  resetBleWifiScanRuntime();
  stopBleWifiScanRadio();
  if (g_cached_wifi_networks.empty()) {
    Serial.println("[provisioning] BLE Wi-Fi scan completed with no visible 2.4 GHz networks");
    publishBleWifiScanStatus(plantlab::kBleWifiScanStatusEmpty);
    return;
  }
  Serial.printf(
      "[provisioning] BLE Wi-Fi scan completed: %u network(s)\n",
      static_cast<unsigned>(g_cached_wifi_networks.size()));
  logBleWifiScanNetworks();
  publishBleWifiScanPage(0);
}

void failBleWifiScan(const char* status, const char* log_message) {
  resetBleWifiScanRuntime();
  stopBleWifiScanRadio();
  Serial.println(log_message);
  publishBleWifiScanStatus(status);
}

void retryBleWifiScan(const char* reason, unsigned long now) {
  WiFi.scanDelete();
  if (g_ble_wifi_scan_retry_count >= kBleWifiScanMaxRetries) {
    failBleWifiScan(plantlab::kBleWifiScanStatusError, "[provisioning] BLE Wi-Fi scan failed");
    return;
  }
  ++g_ble_wifi_scan_retry_count;
  g_ble_wifi_scan_retry_at_ms = now + kBleWifiScanRetryDelayMs;
  Serial.printf(
      "[provisioning] BLE Wi-Fi scan transient failure: %s, retrying %u/%u\n",
      reason,
      static_cast<unsigned>(g_ble_wifi_scan_retry_count),
      static_cast<unsigned>(kBleWifiScanMaxRetries));
  publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning);
}

void startBleWifiScanAttempt(unsigned long now) {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, false);
  WiFi.scanDelete();
  const int scan_result = WiFi.scanNetworks(true, true);
  publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning);

  if (scan_result >= 0) {
    finishBleWifiScan(scan_result);
    return;
  }
  if (scan_result != WIFI_SCAN_RUNNING) {
    retryBleWifiScan("start failed", now);
  }
}

void startBleWifiScan(unsigned long now) {
  if (g_ble_wifi_scan_active) {
    publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning);
    return;
  }

  ++g_ble_wifi_scan_id;
  g_ble_wifi_scan_started_at_ms = now;
  g_ble_wifi_scan_active = true;
  g_ble_wifi_scan_retry_count = 0;
  g_ble_wifi_scan_retry_at_ms = 0;
  startBleWifiScanAttempt(now);
}

void serviceBleWifiScan(unsigned long now) {
  if (g_ble_provisioning.hasPendingWifiScanRequest()) {
    const plantlab::BleWifiScanRequest request = g_ble_provisioning.takePendingWifiScanRequest();
    if (request.command == plantlab::BleWifiScanCommand::kStart) {
      startBleWifiScan(now);
    } else if (request.command == plantlab::BleWifiScanCommand::kPage) {
      if (g_ble_wifi_scan_active) {
        publishBleWifiScanStatus(plantlab::kBleWifiScanStatusScanning);
      } else {
        publishBleWifiScanPage(request.cursor);
      }
    }
  }

  if (!g_ble_wifi_scan_active) {
    return;
  }
  if (g_ble_wifi_scan_retry_at_ms != 0) {
    if (now >= g_ble_wifi_scan_retry_at_ms) {
      g_ble_wifi_scan_retry_at_ms = 0;
      startBleWifiScanAttempt(now);
    }
    return;
  }
  if (now - g_ble_wifi_scan_started_at_ms >= kBleWifiScanTimeoutMs) {
    failBleWifiScan(plantlab::kBleWifiScanStatusTimeout, "[provisioning] BLE Wi-Fi scan timed out");
    return;
  }
  const int scan_result = WiFi.scanComplete();
  if (scan_result == WIFI_SCAN_RUNNING) {
    return;
  }
  if (scan_result < 0) {
    retryBleWifiScan("scan complete failed", now);
    return;
  }
  finishBleWifiScan(scan_result);
}

String connectingPageHtml(const String& return_url) {
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
  html.replace("__RETURN_URL__", js_string_escape(return_url));
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
            <input name="setup_code" type="hidden" value="__CLAIM_TOKEN__">
            <input name="backend_url" type="hidden" value="__BACKEND_URL__">
            <input name="platform_url" type="hidden" value="__PLATFORM_URL__">
            <input name="return_url" type="hidden" value="__RETURN_URL__">
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
  const String form_claim_token = g_web_server.arg("setup_code");
  const String form_backend_url = g_web_server.arg("backend_url");
  const String form_platform_url = g_web_server.arg("platform_url");
  const String form_return_url = g_web_server.arg("return_url");
  const String claim_token = form_claim_token.length() > 0 ? form_claim_token : g_pending_claim_token;
  const String backend_url = form_backend_url.length() > 0 ? form_backend_url : g_pending_backend_url;
  const String platform_url = form_platform_url.length() > 0 ? form_platform_url : g_pending_platform_url;
  const String return_url = withExpectedImageSetting(
      form_return_url.length() > 0 ? form_return_url : g_pending_return_url,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0);

  if (claim_token.length() > 0) {
    g_pending_claim_token = claim_token;
  }
  if (backend_url.length() > 0) {
    g_pending_backend_url = backend_url;
  }
  if (platform_url.length() > 0) {
    g_pending_platform_url = platform_url;
  }
  if (return_url.length() > 0) {
    g_pending_return_url = return_url;
  }

  if (ssid.length() == 0 || claim_token.length() == 0 || platform_url.length() == 0) {
    Serial.println("[provisioning] submission rejected: Wi-Fi SSID, setup code, or platform URL missing");
    g_web_server.send(400, "text/plain", "Wi-Fi SSID, setup code, and platform URL are required.");
    return;
  }

  DeviceConfig pending;
  pending.wifi_ssid = ssid;
  pending.wifi_password = password;
  pending.claim_token = claim_token;
  pending.backend_url = backend_url;
  pending.platform_url = platform_url;
  pending.device_token = "";
  pending.platform_device_id = 0;

  if (!savePendingConfigCandidate(pending)) {
    g_web_server.send(500, "text/plain", "Failed to save configuration.");
    return;
  }
  g_pending_provisioning_config_active = true;
  g_web_server.send(200, "text/html", connectingPageHtml(return_url));
  scheduleRestart(5000UL, "softap_credentials_saved");
  Serial.println("[provisioning] saved Wi-Fi and setup code, reboot scheduled");
}

DeviceConfig makeConfigFromBlePayload(const plantlab::BleProvisioningPayload& payload) {
  DeviceConfig candidate;
  candidate.wifi_ssid = String(payload.ssid.c_str());
  candidate.wifi_password = String(payload.password.c_str());
  candidate.claim_token = String(payload.plantlab_token.c_str());
  candidate.backend_url = String(payload.backend_url.c_str());
  candidate.platform_url = String(payload.platform_url.c_str());
  candidate.device_token = "";
  candidate.platform_device_id = 0;
  candidate.attach_to_platform_device_id = payload.attach_to_platform_device_id;
  return normalizedConfig(candidate);
}

bool commitBleProvisioningPayload(const plantlab::BleProvisioningPayload& payload) {
  const DeviceConfig candidate = makeConfigFromBlePayload(payload);
  if (!savePendingConfigCandidate(candidate)) {
    return false;
  }

  g_pending_provisioning_config_active = true;
  return true;
}

void stopBleProvisioningMode() {
  if (g_ble_wifi_scan_active) {
    resetBleWifiScanRuntime();
    stopBleWifiScanRadio();
  }
  if (g_ble_provisioning.active()) {
    g_ble_provisioning.stop();
  }
  if (!g_softap_provisioning_active) {
    g_provisioning_mode = false;
  }
  resumeNormalTasksAfterProvisioning();
}

bool startBleProvisioningMode() {
  if (g_ble_provisioning.active()) {
    pauseNormalTasksForProvisioning();
    return true;
  }

  g_provisioning_requested = true;
  pauseNormalTasksForProvisioning();
  g_ble_had_previous_config = hasWifiCredentials();
  g_ble_provisioning_started_at_ms = millis();
  g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_BLE;
  g_provisioning_mode = true;
  g_softap_provisioning_active = false;
  g_wifi_ready = false;
  g_device_mode = DeviceMode::kProvisioning;
  updateStatusLed();

  g_cached_wifi_networks.clear();
  resetBleWifiScanRuntime();
  teardownEspNow("ble_provisioning");
  WiFi.disconnect(false, false);
  WiFi.mode(WIFI_OFF);
  delay(50);

  const String advertised_name = bleProvisioningDeviceName();
  const String fallback_platform_url = runtimePlatformUrl();
  const String device_identity_json = bleProvisioningDeviceIdentityJson(advertised_name);
  if (!g_ble_provisioning.begin(
      advertised_name.c_str(),
      fallback_platform_url.c_str(),
      device_identity_json.c_str())) {
    Serial.println("[provisioning] BLE setup failed");
    ++g_diagnostic_error_counters.ble_provisioning_failures;
    recordDiagnosticError("ble_init_failed", "BLE provisioning setup failed");
    Serial.println("[provisioning] provisioning_failed reason=ble_init_failed");
    g_ble_provisioning.stop();
    g_provisioning_mode = false;
    if (g_ble_had_previous_config) {
      Serial.println("[provisioning] resuming saved Wi-Fi after BLE setup failure");
      g_provisioning_state = plantlab::ProvisioningState::WIFI_CONNECTING;
      g_device_mode = DeviceMode::kConnecting;
      g_last_wifi_attempt_ms = 0;
    } else {
      g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_FAILED;
      g_device_mode = DeviceMode::kWifiFailed;
    }
    resumeNormalTasksAfterProvisioning();
    updateStatusLed();
    return false;
  }
  publishBleWifiScanStatus(plantlab::kBleWifiScanStatusIdle);

  g_provisioning_requested = false;
  Serial.println("[provisioning] ble_advertising_started");
  Serial.printf(
      "[provisioning] BLE provisioning started: name=%s service=%s write=%s status=%s wifi_networks=%s wifi_scan_control=%s device_identity=%s hardware_id=%s\n",
      advertised_name.c_str(),
      plantlab::kBleProvisioningServiceUuid,
      plantlab::kBleProvisioningWriteCharacteristicUuid,
      plantlab::kBleProvisioningStatusCharacteristicUuid,
      plantlab::kBleProvisioningWifiNetworksCharacteristicUuid,
      plantlab::kBleProvisioningWifiScanControlCharacteristicUuid,
      plantlab::kBleProvisioningDeviceIdentityCharacteristicUuid,
      stableHardwareDeviceId().c_str());
  return true;
}

bool requestBleProvisioningMode(unsigned long now) {
  (void)now;
  if (!g_provisioning_requested && !g_ble_provisioning.active()) {
    Serial.println("[provisioning] provisioning_requested");
  }
  g_provisioning_requested = true;
  pauseNormalTasksForProvisioning();
  return startBleProvisioningMode();
}

void serviceBleProvisioning(unsigned long now) {
  if (!g_ble_provisioning.active()) {
    return;
  }

  serviceBleWifiScan(now);

  if (g_ble_provisioning.hasPendingResult()) {
    const plantlab::ProvisioningParseResult result = g_ble_provisioning.takePendingResult();
    if (!result.ok) {
      ++g_diagnostic_error_counters.ble_provisioning_failures;
      recordDiagnosticError("ble_payload_rejected", plantlab::provisioningParseErrorCode(result.error));
      Serial.printf(
          "[provisioning] BLE payload rejected: %s\n",
          plantlab::provisioningParseErrorCode(result.error));
      Serial.printf(
          "[provisioning] provisioning_failed reason=%s\n",
          plantlab::provisioningParseErrorCode(result.error));
      return;
    }

    Serial.println("[provisioning] credentials_received");
    Serial.printf(
        "[provisioning] BLE payload accepted: ssid=%s password_len=%u platform=%s backend=%s\n",
        result.payload.ssid.c_str(),
        static_cast<unsigned>(result.payload.password.length()),
        result.payload.platform_url.empty() ? "<empty>" : result.payload.platform_url.c_str(),
        result.payload.backend_url.empty() ? "<empty>" : result.payload.backend_url.c_str());

    g_provisioning_state = plantlab::provisioningStateAfterValidPayload();
    g_ble_provisioning.setAcceptingWrites(false);
    g_ble_provisioning.setStatus(g_provisioning_state);
    updateStatusLed();

    g_provisioning_state = plantlab::ProvisioningState::WIFI_CONNECTING;
    g_ble_provisioning.setStatus(g_provisioning_state);
    updateStatusLed();

    plantlab::ProvisioningParseError wifi_error = plantlab::ProvisioningParseError::kNone;
    if (!validateBleWifiCredentials(result.payload, &wifi_error)) {
      rejectBleProvisioningForRetry(wifi_error);
      return;
    }

    g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_COMMITTING;
    g_ble_provisioning.setStatus(g_provisioning_state);
    updateStatusLed();

    if (!commitBleProvisioningPayload(result.payload)) {
      ++g_diagnostic_error_counters.ble_provisioning_failures;
      recordDiagnosticError("ble_save_failed", "BLE config save failed");
      rejectBleProvisioningForRetry(plantlab::ProvisioningParseError::kSaveFailed);
      Serial.println("[provisioning] BLE config save failed");
      Serial.println("[provisioning] provisioning_failed reason=save_failed");
      return;
    }

    g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_SUCCESS;
    g_ble_provisioning.setStatus(g_provisioning_state);
    scheduleRestart(2500UL, "ble_credentials_saved");
    updateStatusLed();
    Serial.println("[provisioning] provisioning_success");
    Serial.println("[provisioning] BLE credentials saved, reboot scheduled");
    return;
  }

  if (!g_restart_scheduled && now - g_ble_provisioning_started_at_ms >= kBleProvisioningTimeoutMs) {
    ++g_diagnostic_error_counters.ble_provisioning_failures;
    recordDiagnosticError("ble_provisioning_timeout", "BLE provisioning timed out");
    g_provisioning_state = plantlab::provisioningStateAfterTimeout(g_ble_had_previous_config);
    g_ble_provisioning.setStatus(g_provisioning_state, plantlab::ProvisioningParseError::kTimeout);
    Serial.println("[provisioning] provisioning_timeout");
    Serial.printf(
        "[provisioning] BLE provisioning timed out, next_state=%s\n",
        plantlab::provisioningStateName(g_provisioning_state));
    stopBleProvisioningMode();
    if (g_ble_had_previous_config) {
      g_device_mode = DeviceMode::kConnecting;
      g_last_wifi_attempt_ms = 0;
    } else {
      g_device_mode = DeviceMode::kWifiFailed;
    }
    updateStatusLed();
  }
}

void startProvisioningMode() {
  if (g_softap_provisioning_active) {
    return;
  }

  Serial.println("[provisioning] entering SoftAP provisioning mode");
  g_provisioning_mode = true;
  g_softap_provisioning_active = true;
  g_provisioning_state = plantlab::ProvisioningState::FALLBACK_SOFTAP;
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
      const String return_url = g_web_server.arg("return_url");
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
    g_web_server.on("/wifi/networks", HTTP_GET, handleWifiNetworksJson);
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
  if (!hasWifiCredentials() || provisioningPriorityActive()) {
    return false;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!g_wifi_ready) {
      g_wifi_ready = true;
      g_device_mode = DeviceMode::kConnected;
      g_provisioning_state = plantlab::ProvisioningState::NORMAL;
      updateStatusLed();
      if (hasPendingClaim()) {
        Serial.println("[provisioning] wifi_connected");
      }
      Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    return true;
  }

  const unsigned long now = millis();
  if (now - g_last_wifi_attempt_ms < kReconnectRetryMs) {
    return false;
  }

  if (g_last_wifi_attempt_ms != 0 || g_wifi_ready) {
    ++g_diagnostic_error_counters.wifi_reconnects;
  }
  g_last_wifi_attempt_ms = now;
  g_wifi_ready = false;
  g_device_mode = DeviceMode::kConnecting;
  g_provisioning_state = plantlab::ProvisioningState::WIFI_CONNECTING;
  updateStatusLed();

  if (hasPendingClaim()) {
    Serial.printf("[provisioning] wifi_connecting ssid=%s\n", g_config.wifi_ssid.c_str());
  }
  Serial.printf(
      "[wifi] connecting to %s password_len=%u status=%s\n",
      g_config.wifi_ssid.c_str(),
      static_cast<unsigned>(g_config.wifi_password.length()),
      wifiStatusLabel(WiFi.status()));
  WiFi.mode(WIFI_STA);
  WiFi.begin(g_config.wifi_ssid.c_str(), g_config.wifi_password.c_str());

  const unsigned long started_at = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started_at < PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    const unsigned long loop_now = millis();
    checkProvisioningButton();
    if (provisioningPriorityActive()) {
      WiFi.disconnect(false, false);
      return false;
    }
    g_status_led.update(loop_now);
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    g_wifi_ready = true;
    g_device_mode = DeviceMode::kConnected;
    g_provisioning_state = plantlab::ProvisioningState::NORMAL;
    updateStatusLed();
    if (hasPendingClaim()) {
      Serial.println("[provisioning] wifi_connected");
    }
    Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
    return true;
  }

  const wl_status_t final_status = WiFi.status();
  WiFi.disconnect();
  recordDiagnosticError("wifi_connect_timeout", wifiStatusLabel(final_status));
  if (restorePreviousActiveConfigAfterPendingFailure("wifi_connect_timeout")) {
    return false;
  }
  g_device_mode = DeviceMode::kWifiFailed;
  g_provisioning_state = plantlab::ProvisioningState::PROVISIONING_FAILED;
  updateStatusLed();
  if (hasPendingClaim()) {
    Serial.println("[provisioning] provisioning_failed reason=wifi_connect_timeout");
  }
  Serial.printf("[wifi] connect timed out status=%s\n", wifiStatusLabel(final_status));
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
    Serial.println("[provisioning] provisioning_failed reason=missing_platform_url");
    restorePreviousActiveConfigAfterPendingFailure("missing_platform_url");
    return false;
  }

  g_provisioning_state = plantlab::ProvisioningState::BACKEND_REGISTERING;
  updateStatusLed();
  Serial.println("[provisioning] backend_confirming");
  Serial.println("[provisioning] registering device with setup code");
  StaticJsonDocument<2304> payload;
  payload["device_id"] = stableHardwareDeviceId();
  payload["claim_token"] = g_config.claim_token;
  payload["node_role"] = "master";
  payload["display_name"] = "Master";
  payload["hardware_model"] = "esp32_master";
  payload["hardware_version"] = BOARD_NAME;
  payload["software_version"] = kSoftwareVersion;
  if (shouldRegisterAsFactoryResetTransfer()) {
    payload["factory_reset"] = true;
    Serial.println("[provisioning] registration includes factory_reset transfer flag");
  }
  if (g_config.attach_to_platform_device_id > 0) {
    payload["attach_to_platform_device_id"] = g_config.attach_to_platform_device_id;
  }
  JsonObject capabilities = payload.createNestedObject("capabilities");
  capabilities["camera"] = false;
  capabilities["pump"] = true;
  capabilities["grow_light"] = true;
  capabilities["grow_light_driver"] = "dual_al8860";
  capabilities["grow_light_channel_control"] = true;
  capabilities["grow_light_red_ctrl_gpio"] = PIN_GROW_LIGHT_RED_CTRL;
  capabilities["grow_light_white_ctrl_gpio"] = PIN_GROW_LIGHT_WHITE_CTRL;
  capabilities["grow_light_pwm_frequency_hz"] = g_growing_light.pwm_frequency_hz();
  capabilities["moisture_sensor"] = g_moisture.enabled();
  capabilities["water_temperature_sensor"] = g_i2c_environment.mcp9808_present();
  capabilities["water_temperature_sensor_source"] = "mcp9808";
  capabilities["water_level_sensor"] = true;
  capabilities["water_level_sensor_type"] = "esp32s3_touch_three_pad";
  capabilities["water_level_calibrated"] = g_water_level.calibrationReady();
  capabilities["water_level_top_gpio"] = WATER_LEVEL_TOP_GPIO;
  capabilities["water_level_middle_gpio"] = WATER_LEVEL_MIDDLE_GPIO;
  capabilities["water_level_bottom_gpio"] = WATER_LEVEL_BOTTOM_GPIO;
  capabilities["water_level_top_touch_channel"] = WATER_LEVEL_TOP_TOUCH_CHANNEL;
  capabilities["water_level_middle_touch_channel"] = WATER_LEVEL_MIDDLE_TOUCH_CHANNEL;
  capabilities["water_level_bottom_touch_channel"] = WATER_LEVEL_BOTTOM_TOUCH_CHANNEL;
  capabilities["temperature_sensor"] = true;
  capabilities["humidity_sensor"] = true;
  capabilities["i2c_sda_gpio"] = PIN_I2C_SDA;
  capabilities["i2c_scl_gpio"] = PIN_I2C_SCL;
  capabilities["aht20_sensor"] = g_i2c_environment.aht20_present();
  capabilities["mcp9808_sensor"] = g_i2c_environment.mcp9808_present();
  capabilities["temperature_sensor_source"] = "aht20";
  capabilities["humidity_sensor_source"] = "aht20";
  capabilities["light_control"] = true;
  capabilities["light_intensity_control"] = g_growing_light.supports_intensity_control();
  capabilities["light_intensity_min_percent"] = 0;
  capabilities["light_intensity_max_percent"] = 100;
  JsonArray light_control_modes = capabilities.createNestedArray("light_control_modes");
  light_control_modes.add("on_off");
  if (g_growing_light.supports_intensity_control()) {
    light_control_modes.add("intensity");
  }
  capabilities["ambient_led_belt"] = true;
  capabilities["ambient_led_belt_available"] = g_ambient_led_belt.state().available;
  capabilities["ambient_led_belt_data_gpio"] = g_ambient_led_belt.state().data_gpio;
  capabilities["ambient_led_belt_logical_pixel_count"] = g_ambient_led_belt.state().logical_pixel_count;
  capabilities["ambient_led_belt_physical_led_count"] = g_ambient_led_belt.state().physical_led_count;
  capabilities["ambient_led_belt_color_order"] = plantlab::ambient_led_belt::colorOrderName(g_ambient_led_belt.state().color_order);
  capabilities["ambient_led_belt_max_brightness"] = g_ambient_led_belt.config().maximum_brightness;

  String body;
  serializeJson(payload, body);

  HTTPClient http;
  http.setTimeout(kHttpTimeoutMs);
  const String url = platform_url + "/api/devices/register-provisioned";
  if (!http.begin(url)) {
    Serial.println("[provisioning] register request setup failed");
    Serial.println("[provisioning] provisioning_failed reason=register_request_setup_failed");
    restorePreviousActiveConfigAfterPendingFailure("register_request_setup_failed");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  const int status_code = http.POST(body);
  const String response_body = status_code > 0 ? http.getString() : http.errorToString(status_code);
  http.end();

  if (status_code < 200 || status_code >= 300) {
    Serial.printf("[provisioning] registration failed HTTP %d\n", status_code);
    Serial.println("[provisioning] provisioning_failed reason=backend_register_failed");
    restorePreviousActiveConfigAfterPendingFailure("backend_register_failed");
    return false;
  }

  DynamicJsonDocument response(1024);
  const DeserializationError json_error = deserializeJson(response, response_body);
  if (json_error) {
    Serial.println("[provisioning] registration response JSON parse failed");
    Serial.println("[provisioning] provisioning_failed reason=backend_response_invalid_json");
    restorePreviousActiveConfigAfterPendingFailure("backend_response_invalid_json");
    return false;
  }

  const int platform_device_id = response["platform_device_id"] | 0;
  const char* device_access_token = response["device_access_token"] | "";
  if (platform_device_id <= 0 || String(device_access_token).length() == 0) {
    Serial.println("[provisioning] registration response missing platform device id or device token");
    Serial.println("[provisioning] provisioning_failed reason=backend_response_missing_fields");
    restorePreviousActiveConfigAfterPendingFailure("backend_response_missing_fields");
    return false;
  }

  g_config.platform_device_id = platform_device_id;
  g_config.device_token = String(device_access_token);
  g_config.claim_token = "";
  g_config.attach_to_platform_device_id = 0;
  if (!saveConfig()) {
    Serial.println("[provisioning] provisioning_failed reason=save_registered_config_failed");
    return false;
  }
  clearPendingConfig();
  resetCameraProvisioningRuntime();
  g_provisioning_state = plantlab::ProvisioningState::NORMAL;
  updateStatusLed();
  Serial.println("[provisioning] device_online_confirmed");
  Serial.println("[provisioning] provisioning_success");
  Serial.printf("[provisioning] registration complete, platform_device_id=%d\n", g_config.platform_device_id);
  return true;
}

void startFactoryReset() {
  if (g_restart_scheduled && g_provisioning_state == plantlab::ProvisioningState::FACTORY_RESET_PENDING) {
    return;
  }

  Serial.println("[button] factory reset hold detected -> clearing credentials");
  g_provisioning_state = plantlab::ProvisioningState::FACTORY_RESET_PENDING;
  g_provisioning_mode = true;
  g_softap_provisioning_active = false;
  g_wifi_ready = false;
  g_device_mode = DeviceMode::kProvisioning;
  updateStatusLed();

  stopBleProvisioningMode();
  g_provisioning_mode = true;
  g_provisioning_state = plantlab::ProvisioningState::FACTORY_RESET_PENDING;
  updateStatusLed();
  g_web_server.stop();
  teardownEspNow("factory_reset");
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  clearAmbientLedBeltConfig();
  clearConfig();
  scheduleRestart(2000UL, "factory_reset");
  Serial.println("[provisioning] credentials cleared, reboot scheduled");
}

void checkProvisioningButton() {
  const unsigned long now = millis();
  const PowerButtonEvent event = g_power_button.update(now);
  if (g_power_button.is_pressed()) {
    if (g_factory_reset_pressed_since_ms == 0) {
      g_factory_reset_pressed_since_ms = now;
      g_factory_reset_fired = false;
    } else if (!g_factory_reset_fired &&
               now - g_factory_reset_pressed_since_ms >= kFactoryResetHoldMs) {
      g_factory_reset_fired = true;
      startFactoryReset();
      return;
    }
  } else {
    g_factory_reset_pressed_since_ms = 0;
    g_factory_reset_fired = false;
  }

  if (event == PowerButtonEvent::kLongPress && !g_provisioning_mode) {
    Serial.println("[button] long press detected -> BLE provisioning mode");
    requestBleProvisioningMode(now);
    return;
  }
  if (event == PowerButtonEvent::kLongPress && g_ble_provisioning.active()) {
    Serial.println("[button] long press detected while BLE provisioning is already active");
    g_ble_provisioning.setStatus(g_provisioning_state);
    return;
  }
}

void applyWaterLevelStatus(PlatformStatus* status) {
  if (status == nullptr) {
    return;
  }
  const WaterLevelReading water_level = g_water_level.reading();
  status->has_water_level_state = true;
  status->water_level.available = water_level.sensor_present;
  status->water_level.calibrated = water_level.calibrated;
  status->water_level.stable = water_level.stable;
  status->water_level.state = waterLevelStateName(water_level.state);
  status->water_level.instantaneous_state = waterLevelStateName(water_level.instantaneous_state);
  status->water_level.quality = waterLevelQualityName(water_level.quality);
  status->water_level.reason = water_level.diagnostic_reason == nullptr ? "" : water_level.diagnostic_reason;
  status->water_level.percent = water_level.percent;
  status->water_level.representative_raw = water_level.representative_raw;
  for (size_t index = 0; index < kWaterLevelChannelCount && index < 3; ++index) {
    const WaterLevelChannelReading& source = water_level.channels[index];
    PlatformWaterLevelPadState& target = status->water_level.pads[index];
    target.name = waterLevelPadName(source.pad);
    target.gpio = source.gpio;
    target.touch_channel = source.touch_channel;
    target.available = source.available;
    target.calibrated = source.calibrated;
    target.wet = source.wet;
    target.stable = source.stable;
    target.raw = source.raw;
    target.filtered = source.filtered;
    target.threshold = source.threshold;
    target.hysteresis = source.hysteresis;
    target.dry_baseline = source.calibration.dry_baseline;
    target.wet_reference = source.calibration.wet_reference;
    target.margin = source.margin;
    target.read_failures = source.read_failures;
  }
}

void printWaterLevelStatus() {
  const WaterLevelReading reading = g_water_level.reading();
  Serial.printf(
      "[water-level] state=%s instantaneous=%s quality=%s percent=%u calibrated=%u stable=%u available=%u raw=%lu reason=%s\n",
      waterLevelStateName(reading.state),
      waterLevelStateName(reading.instantaneous_state),
      waterLevelQualityName(reading.quality),
      static_cast<unsigned int>(reading.percent),
      reading.calibrated ? 1U : 0U,
      reading.stable ? 1U : 0U,
      reading.sensor_present ? 1U : 0U,
      static_cast<unsigned long>(reading.representative_raw),
      reading.diagnostic_reason == nullptr ? "" : reading.diagnostic_reason);
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    const WaterLevelChannelReading& channel = reading.channels[index];
    Serial.printf(
        "[water-level] pad=%s gpio=%d touch=%d raw=%lu filtered=%lu wet=%u stable=%u available=%u calibrated=%u threshold=%lu hyst=%lu dry=%lu wet_ref=%lu margin=%ld failures=%u\n",
        waterLevelPadName(channel.pad),
        channel.gpio,
        channel.touch_channel,
        static_cast<unsigned long>(channel.raw),
        static_cast<unsigned long>(channel.filtered),
        channel.wet ? 1U : 0U,
        channel.stable ? 1U : 0U,
        channel.available ? 1U : 0U,
        channel.calibrated ? 1U : 0U,
        static_cast<unsigned long>(channel.threshold),
        static_cast<unsigned long>(channel.hysteresis),
        static_cast<unsigned long>(channel.calibration.dry_baseline),
        static_cast<unsigned long>(channel.calibration.wet_reference),
        static_cast<long>(channel.margin),
        static_cast<unsigned int>(channel.read_failures));
  }
}

bool handleCameraProvisioningCommandLine(const String& input, String* message, bool* success) {
  String line = input;
  line.trim();
  line.toLowerCase();
  if (line.length() == 0 || !line.startsWith("camera")) {
    return false;
  }

  const char* help_text =
      "[camera-provisioning] commands: camera provision status | camera provision top [mac] | camera provision side [mac] | camera provision auto | camera provision off";
  if (line == "camera help") {
    Serial.println(help_text);
    if (message != nullptr) {
      *message = "camera provisioning help printed";
    }
    if (success != nullptr) {
      *success = true;
    }
    return true;
  }
  if (line == "camera status" || line == "camera provision status") {
    printCameraProvisioningStatus();
    if (message != nullptr) {
      *message = "camera provisioning status printed";
    }
    if (success != nullptr) {
      *success = true;
    }
    return true;
  }
  if (!line.startsWith("camera provision")) {
    Serial.println("[camera-provisioning] unknown command; send 'camera help'");
    if (message != nullptr) {
      *message = "unknown camera provisioning command";
    }
    if (success != nullptr) {
      *success = false;
    }
    return true;
  }

  String args = line.substring(strlen("camera provision"));
  args.trim();
  if (args == "auto") {
    enableAutomaticTopCameraProvisioning(millis());
    if (message != nullptr) {
      *message = "automatic top-camera provisioning enabled";
    }
    if (success != nullptr) {
      *success = true;
    }
    return true;
  }
  if (args == "off") {
    stopCameraProvisioning("command");
    if (message != nullptr) {
      *message = "camera provisioning stopped";
    }
    if (success != nullptr) {
      *success = true;
    }
    return true;
  }
  if (args.length() == 0) {
    Serial.println(help_text);
    if (message != nullptr) {
      *message = "camera provisioning slot is required";
    }
    if (success != nullptr) {
      *success = false;
    }
    return true;
  }

  const int separator = args.indexOf(' ');
  String slot_token = separator >= 0 ? args.substring(0, separator) : args;
  String target_token = separator >= 0 ? args.substring(separator + 1) : "";
  slot_token.trim();
  target_token.trim();

  CameraProvisioningSlotId slot_id = CameraProvisioningSlotId::kTop;
  if (!cameraProvisioningSlotFromName(slot_token, &slot_id)) {
    Serial.println("[camera-provisioning] unknown slot; use top or side");
    if (message != nullptr) {
      *message = "unknown camera provisioning slot";
    }
    if (success != nullptr) {
      *success = false;
    }
    return true;
  }

  uint8_t target_mac[6] = {0};
  const uint8_t* target_mac_ptr = nullptr;
  if (target_token.length() > 0) {
    if (!parseMacAddress(target_token, target_mac)) {
      Serial.println("[camera-provisioning] invalid target MAC; expected aa:bb:cc:dd:ee:ff");
      if (message != nullptr) {
        *message = "invalid camera provisioning target MAC";
      }
      if (success != nullptr) {
        *success = false;
      }
      return true;
    }
    target_mac_ptr = target_mac;
  }

  requestCameraProvisioningSlot(slot_id, target_mac_ptr, millis());
  printCameraProvisioningStatus();
  const CameraProvisioningSlotConfig& slot = cameraProvisioningSlot(slot_id);
  if (message != nullptr) {
    *message = "camera provisioning requested for " + String(slot.name) + " camera";
  }
  if (success != nullptr) {
    *success = true;
  }
  return true;
}

void handleSerialDiagnosticLine(const String& input) {
  String line = input;
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) {
    return;
  }
  bool command_success = true;
  String command_message;
  if (handleCameraProvisioningCommandLine(line, &command_message, &command_success)) {
    (void)command_success;
    return;
  }
  if (line == "water help") {
    Serial.println("[water-level] commands: water status | water diag on|off | water calibrate dry | water calibrate wet top|middle|bottom | water calibrate save | water calibrate reset");
    return;
  }
  if (line == "water status") {
    printWaterLevelStatus();
    return;
  }
  if (line == "water diag on") {
    g_water_level.setDiagnosticMode(true);
    Serial.println("[water-level] diagnostics enabled");
    printWaterLevelStatus();
    return;
  }
  if (line == "water diag off") {
    g_water_level.setDiagnosticMode(false);
    Serial.println("[water-level] diagnostics disabled");
    return;
  }
  if (line == "water calibrate dry") {
    if (g_water_level.captureDryCalibration()) {
      Serial.println("[water-level] dry calibration captured for all pads");
    } else {
      Serial.println("[water-level] dry calibration failed: wait for stable raw values");
    }
    printWaterLevelStatus();
    return;
  }
  if (line == "water calibrate wet top" ||
      line == "water calibrate wet middle" ||
      line == "water calibrate wet bottom") {
    WaterLevelPad pad = WaterLevelPad::kTop;
    if (line.endsWith("middle")) {
      pad = WaterLevelPad::kMiddle;
    } else if (line.endsWith("bottom")) {
      pad = WaterLevelPad::kBottom;
    }
    if (g_water_level.captureWetReference(pad)) {
      Serial.printf("[water-level] wet calibration captured for %s pad\n", waterLevelPadName(pad));
    } else {
      Serial.printf("[water-level] wet calibration failed for %s pad: capture dry first and wait for stable raw values\n", waterLevelPadName(pad));
    }
    printWaterLevelStatus();
    return;
  }
  if (line == "water calibrate save") {
    saveWaterLevelCalibration();
    printWaterLevelStatus();
    return;
  }
  if (line == "water calibrate reset") {
    clearWaterLevelCalibration();
    printWaterLevelStatus();
    return;
  }
  if (line.startsWith("water")) {
    Serial.println("[water-level] unknown command; send 'water help'");
  }
}

void serviceSerialDiagnostics(unsigned long now) {
  (void)now;
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r' || c == '\n') {
      handleSerialDiagnosticLine(g_serial_command_buffer);
      g_serial_command_buffer = "";
      continue;
    }
    if (g_serial_command_buffer.length() < 120) {
      g_serial_command_buffer += c;
    }
  }
}

void serviceWaterLevelDiagnostics(unsigned long now) {
  if (!g_water_level.diagnosticMode()) {
    return;
  }
  if (now - g_last_water_level_diagnostic_ms < WATER_LEVEL_DIAGNOSTIC_INTERVAL_MS) {
    return;
  }
  g_last_water_level_diagnostic_ms = now;
  printWaterLevelStatus();
}
}  // namespace

PlatformReading read_platform_reading() {
  const unsigned long now = millis();
  g_last_sensor_reading_ms = now;
  g_water_level.update(now);
  const I2cEnvironmentReading i2c_environment = g_i2c_environment.read();
  const MoistureReading moisture = g_moisture.read();
  const WaterLevelReading water_level = g_water_level.reading();

  float air_temperature_c = 0.0f;
  bool air_temperature_valid = false;
  const char* air_temperature_source = "none";
  if (i2c_environment.aht20_valid) {
    air_temperature_c = i2c_environment.aht20_temperature_c;
    air_temperature_valid = true;
    air_temperature_source = "aht20";
  }

  float humidity_percent = 0.0f;
  bool humidity_valid = false;
  const char* humidity_source = "none";
  if (i2c_environment.aht20_valid) {
    humidity_percent = i2c_environment.aht20_humidity_percent;
    humidity_valid = true;
    humidity_source = "aht20";
  }

  if (!air_temperature_valid || !humidity_valid) {
    Serial.println("[env] air temperature/humidity read failed");
  } else if (kVerboseSensorPollingLogs) {
    Serial.printf(
        "[env] temp_c=%.1f source=%s humidity=%.1f%% source=%s\n",
        air_temperature_c,
        air_temperature_source,
        humidity_percent,
        humidity_source);
  }

  if (i2c_environment.aht20_valid && kVerboseSensorPollingLogs) {
    Serial.printf(
        "[aht20] temp_c=%.1f humidity=%.1f%%\n",
        i2c_environment.aht20_temperature_c,
        i2c_environment.aht20_humidity_percent);
  } else if (!i2c_environment.aht20_valid && g_i2c_environment.aht20_present()) {
    Serial.println("[aht20] read failed");
  }

  if (i2c_environment.mcp9808_valid && kVerboseSensorPollingLogs) {
    Serial.printf("[mcp9808] temp_c=%.1f\n", i2c_environment.mcp9808_temperature_c);
  } else if (!i2c_environment.mcp9808_valid && g_i2c_environment.mcp9808_present()) {
    Serial.println("[mcp9808] read failed");
  }

  if (g_moisture.enabled() && !moisture.valid) {
    Serial.println("[moisture] read failed");
  } else {
    if (kVerboseSensorPollingLogs) {
      Serial.printf(
          "[moisture] raw=%d percent=%.1f%%\n",
          moisture.raw_adc,
          moisture.moisture_percent);
    }
  }

  if (!i2c_environment.mcp9808_valid) {
    Serial.println("[water-temp] MCP9808 read failed");
  } else if (kVerboseSensorPollingLogs) {
    Serial.printf("[water-temp] temp_c=%.1f source=mcp9808\n", i2c_environment.mcp9808_temperature_c);
  }

  if (!water_level.valid && kVerboseSensorPollingLogs) {
    Serial.printf(
        "[water-level] state=%s quality=%s reason=%s\n",
        waterLevelStateName(water_level.state),
        waterLevelQualityName(water_level.quality),
        water_level.diagnostic_reason == nullptr ? "" : water_level.diagnostic_reason);
  } else if (kVerboseSensorPollingLogs) {
    Serial.printf(
        "[water-level] raw=%lu state=%s quality=%s percent=%u\n",
        static_cast<unsigned long>(water_level.representative_raw),
        waterLevelStateName(water_level.state),
        waterLevelQualityName(water_level.quality),
        static_cast<unsigned int>(water_level.percent));
  }

  if (kVerboseSensorPollingLogs) {
    Serial.printf(
        "[actuators] growing_light=%s intensity=%d%% pump=%s\n",
        g_growing_light.is_on() ? "on" : "off",
        g_growing_light.intensity_percent(),
        g_pump.is_on() ? "on" : "off");
  }

  PlatformReading platform_reading{};
  platform_reading.hardware_device_id = stableHardwareDeviceId();
  platform_reading.temperature_c = air_temperature_c;
  platform_reading.humidity_percent = humidity_percent;
  platform_reading.moisture_percent = moisture.moisture_percent;
  platform_reading.water_temperature_c = i2c_environment.mcp9808_temperature_c;
  platform_reading.water_level_raw = static_cast<int>(water_level.representative_raw);
  platform_reading.temperature_valid = air_temperature_valid;
  platform_reading.humidity_valid = humidity_valid;
  platform_reading.moisture_valid = moisture.valid;
  platform_reading.water_temperature_valid = i2c_environment.mcp9808_valid;
  platform_reading.water_level_valid = water_level.valid;
  platform_reading.water_level_state = waterLevelStateName(water_level.state);
  platform_reading.light_on = g_growing_light.is_on();
  if (g_growing_light.supports_intensity_control()) {
    platform_reading.light_intensity_percent = g_growing_light.intensity_percent();
  }
  platform_reading.pump_on = g_pump.is_on();
  platform_reading.pump_status = g_pump.is_on() ? "running" : "idle";
  return platform_reading;
}

PlatformStatus platform_status(const String& message) {
  PlatformStatus status{};
  const unsigned long now = millis();
  status.hardware_device_id = stableHardwareDeviceId();
  status.node_role = PLANTLAB_NODE_ROLE_MASTER;
  status.status = PLANTLAB_DEVICE_STATUS_ONLINE;
  status.hardware_model = "esp32_master";
  status.hardware_version = BOARD_NAME;
  status.has_free_heap_bytes = true;
  status.free_heap_bytes = ESP.getFreeHeap();
  if (WiFi.status() == WL_CONNECTED) {
    status.ip_address = WiFi.localIP().toString();
  }
  status.has_light_state = true;
  status.light_on = g_growing_light.is_on();
  if (g_growing_light.supports_intensity_control()) {
    status.light_intensity_percent = g_growing_light.intensity_percent();
  }
  status.pump_on = g_pump.is_on();
  status.message = message;
  status.software_version = kSoftwareVersion;
  status.has_capture_interval_seconds = true;
  status.capture_interval_seconds = static_cast<uint32_t>(PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS / 1000UL);
  status.ota_status = g_ota_update_manager ? g_ota_update_manager->current_status() : PLANTLAB_OTA_STATUS_IDLE;
  status.provisioning_status = plantlab::provisioningStateName(g_provisioning_state);
  if (g_camera_runtime_ready) {
    status.camera_node_status = PLANTLAB_DEVICE_STATUS_ONLINE;
  } else if (g_camera_target_mac_known) {
    status.camera_node_status = PLANTLAB_DEVICE_STATUS_DEGRADED;
  }
  if (g_last_command_result_ms > 0 && g_last_command_id > 0) {
    status.last_command_contract_id = "cmd_" + String(g_last_command_id);
    status.last_command_status = g_last_command_status;
  }
  if (g_last_command_poll_at_iso.length() > 0) {
    status.last_command_poll_at = g_last_command_poll_at_iso;
  }
  status.last_command_poll_status = g_last_command_poll_status;
  status.last_command_poll_error = g_last_command_poll_error;
  status.has_last_command_poll_latency_ms = g_last_command_poll_completed_ms > 0;
  status.last_command_poll_latency_ms = g_last_command_poll_latency_ms;
  status.has_command_poll_stale_seconds = true;
  status.command_poll_stale_seconds = g_last_command_poll_completed_ms > 0
                                          ? ageSecondsSince(now, g_last_command_poll_completed_ms)
                                          : static_cast<uint32_t>(now / 1000UL);
  const plantlab::ambient_led_belt::AmbientLedBeltState& belt = g_ambient_led_belt.state();
  status.has_ambient_led_belt_state = true;
  status.ambient_led_belt.available = belt.available;
  status.ambient_led_belt.enabled = belt.enabled;
  status.ambient_led_belt.mode = plantlab::ambient_led_belt::modeName(belt.mode);
  status.ambient_led_belt.brightness = belt.effective_brightness;
  status.ambient_led_belt.max_brightness = g_ambient_led_belt.config().maximum_brightness;
  status.ambient_led_belt.color_r = belt.requested_color.r;
  status.ambient_led_belt.color_g = belt.requested_color.g;
  status.ambient_led_belt.color_b = belt.requested_color.b;
  status.ambient_led_belt.logical_pixel_count = belt.logical_pixel_count;
  status.ambient_led_belt.physical_led_count = belt.physical_led_count;
  status.ambient_led_belt.color_order = plantlab::ambient_led_belt::colorOrderName(belt.color_order);
  status.ambient_led_belt.data_gpio = belt.data_gpio;
  status.ambient_led_belt.diagnostic_active = belt.diagnostic_active;
  status.ambient_led_belt.last_error = belt.last_error;
  applyWaterLevelStatus(&status);
  status.diagnostics.valid = true;
  status.diagnostics.has_uptime_seconds = true;
  status.diagnostics.uptime_seconds = static_cast<uint32_t>(now / 1000UL);
  if (WiFi.status() == WL_CONNECTED) {
    status.diagnostics.has_wifi_rssi_dbm = true;
    status.diagnostics.wifi_rssi_dbm = WiFi.RSSI();
  }
  status.diagnostics.reboot_reason = resetReasonLabel(esp_reset_reason());
  status.diagnostics.provisioning_state = plantlab::provisioningStateName(g_provisioning_state);
  if (g_last_sensor_reading_ms > 0) {
    status.diagnostics.has_last_sensor_reading_age_seconds = true;
    status.diagnostics.last_sensor_reading_age_seconds = ageSecondsSince(now, g_last_sensor_reading_ms);
  }
  if (g_last_command_result_ms > 0) {
    status.diagnostics.has_last_command = true;
    status.diagnostics.last_command_id = g_last_command_id;
    status.diagnostics.last_command_status = g_last_command_status;
    status.diagnostics.last_command_code = g_last_command_code;
    status.diagnostics.last_command_message = g_last_command_message;
    status.diagnostics.has_last_command_age_seconds = true;
    status.diagnostics.last_command_age_seconds = ageSecondsSince(now, g_last_command_result_ms);
  }
  status.diagnostics.has_error_counters = true;
  status.diagnostics.error_counters = g_diagnostic_error_counters;
  status.diagnostics.last_error_code = g_last_diagnostic_error_code;
  status.diagnostics.last_error_message = g_last_diagnostic_error_message;
  return status;
}

void dropOldestQueuedReading() {
  int oldest_index = -1;
  unsigned long oldest_at = 0;
  for (uint8_t i = 0; i < kReadingRetryQueueSize; ++i) {
    if (!g_reading_retry_queue[i].active) {
      continue;
    }
    if (oldest_index < 0 || g_reading_retry_queue[i].queued_at_ms < oldest_at) {
      oldest_index = i;
      oldest_at = g_reading_retry_queue[i].queued_at_ms;
    }
  }
  if (oldest_index >= 0) {
    Serial.printf(
        "[platform] reading retry queue full, dropping oldest idempotency_key=%s\n",
        g_reading_retry_queue[oldest_index].reading.idempotency_key.c_str());
    g_reading_retry_queue[oldest_index] = QueuedPlatformReading{};
  }
}

void enqueuePlatformReading(const PlatformReading& reading, unsigned long now) {
  int free_index = -1;
  for (uint8_t i = 0; i < kReadingRetryQueueSize; ++i) {
    if (!g_reading_retry_queue[i].active) {
      free_index = i;
      break;
    }
  }
  if (free_index < 0) {
    dropOldestQueuedReading();
    for (uint8_t i = 0; i < kReadingRetryQueueSize; ++i) {
      if (!g_reading_retry_queue[i].active) {
        free_index = i;
        break;
      }
    }
  }
  if (free_index < 0) {
    return;
  }

  g_reading_retry_queue[free_index].active = true;
  g_reading_retry_queue[free_index].reading = reading;
  g_reading_retry_queue[free_index].attempts = 0;
  g_reading_retry_queue[free_index].next_retry_ms = now;
  g_reading_retry_queue[free_index].queued_at_ms = now;
}

uint32_t readingRetryDelayMs(uint8_t attempts) {
  uint32_t delay_ms = kReadingRetryBaseDelayMs;
  for (uint8_t i = 1; i < attempts && delay_ms < kReadingRetryMaxDelayMs; ++i) {
    delay_ms = std::min<uint32_t>(delay_ms * 2UL, kReadingRetryMaxDelayMs);
  }
  return std::min<uint32_t>(delay_ms + static_cast<uint32_t>(random(0, 750)), kReadingRetryMaxDelayMs);
}

void servicePlatformReadingQueue(unsigned long now) {
  if (!platform_enabled() || !g_wifi_ready || !g_master_node_registered) {
    return;
  }

  for (uint8_t i = 0; i < kReadingRetryQueueSize; ++i) {
    QueuedPlatformReading& queued = g_reading_retry_queue[i];
    if (!queued.active || now < queued.next_retry_ms) {
      continue;
    }

    String error;
    if (g_platform_client->send_hardware_reading(queued.reading, &error)) {
      if (kVerboseSensorPollingLogs) {
        Serial.printf(
            "[platform] reading sent idempotency_key=%s to %s/api/hardware/readings (device_id=%d)\n",
            queued.reading.idempotency_key.c_str(),
            g_platform_client->base_url().c_str(),
            g_platform_client->device_id());
      }
      queued = QueuedPlatformReading{};
      return;
    }

    queued.attempts = static_cast<uint8_t>(queued.attempts + 1);
    queued.next_retry_ms = now + readingRetryDelayMs(queued.attempts);
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("reading_upload_failed", "sensor reading upload failed");
    Serial.printf(
        "[platform] reading upload failed idempotency_key=%s attempt=%u next_retry_ms=%lu error=%s\n",
        queued.reading.idempotency_key.c_str(),
        static_cast<unsigned int>(queued.attempts),
        static_cast<unsigned long>(queued.next_retry_ms - now),
        error.c_str());
    return;
  }
}

void send_platform_reading(unsigned long now) {
  if (!platform_enabled()) {
    return;
  }
  if (now - g_last_platform_send_ms >= PLANTLAB_SENSOR_SEND_INTERVAL_MS) {
    g_last_platform_send_ms = now;
    PlatformReading reading = read_platform_reading();
    reading.idempotency_key = nextReadingIdempotencyKey();
    enqueuePlatformReading(reading, now);
  }

  servicePlatformReadingQueue(now);
}

void send_platform_status(unsigned long now, const String& message = "online") {
  if (!platform_enabled() || !g_wifi_ready || !g_master_node_registered ||
      now - g_last_platform_status_ms < PLANTLAB_STATUS_INTERVAL_MS) {
    return;
  }
  g_last_platform_status_ms = now;

  String error;
  if (g_platform_client->send_hardware_heartbeat(platform_status(message), &error)) {
    if (g_consecutive_heartbeat_failures > 0) {
      Serial.printf(
          "[platform] heartbeat recovered after %lu failures\n",
          static_cast<unsigned long>(g_consecutive_heartbeat_failures));
    }
    g_consecutive_heartbeat_failures = 0;
  } else {
    ++g_consecutive_heartbeat_failures;
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("heartbeat_upload_failed", "heartbeat upload failed");
    Serial.printf(
        "[platform] heartbeat upload failed consecutive=%lu error=%s\n",
        static_cast<unsigned long>(g_consecutive_heartbeat_failures),
        error.c_str());
  }
}

bool parseLightIntensityPercent(const String& value, int* percent) {
  String normalized = value;
  normalized.trim();
  if (normalized.length() == 0) {
    return false;
  }
  for (size_t index = 0; index < normalized.length(); ++index) {
    if (!isDigit(normalized.charAt(index))) {
      return false;
    }
  }
  const int parsed = normalized.toInt();
  if (parsed < 0 || parsed > 100) {
    return false;
  }
  if (percent != nullptr) {
    *percent = parsed;
  }
  return true;
}

bool parseGrowLightChannelIntensityCommand(const String& value, String* channel, int* percent) {
  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, value);
  if (error) {
    return false;
  }
  const char* parsed_channel = doc["channel"] | "";
  const String normalized_channel(parsed_channel);
  if (normalized_channel != "red" && normalized_channel != "white") {
    return false;
  }
  if (!doc["brightness_percent"].is<int>()) {
    return false;
  }
  const int parsed_percent = doc["brightness_percent"].as<int>();
  if (parsed_percent < 0 || parsed_percent > 100) {
    return false;
  }
  if (channel != nullptr) {
    *channel = normalized_channel;
  }
  if (percent != nullptr) {
    *percent = parsed_percent;
  }
  return true;
}

int reportedLightIntensityPercent() {
  return g_growing_light.supports_intensity_control() ? g_growing_light.intensity_percent() : -1;
}

bool reportPlatformCommandResult(
    const PlatformCommand& command,
    const char* status,
    const char* message,
    const char* error_code) {
  if (!platform_enabled()) {
    return false;
  }

  String ack_error;
  bool reported = false;
  if (command.contract_native) {
    const String hardware_id = stableHardwareDeviceId();
    reported = g_platform_client->report_contract_command_result(
        command,
        hardware_id.c_str(),
        PLANTLAB_NODE_ROLE_MASTER,
        status,
        message,
        g_growing_light.is_on(),
        g_pump.is_on(),
        &ack_error,
        reportedLightIntensityPercent(),
        error_code);
  } else {
    reported = g_platform_client->report_hardware_command_result(
        command.id,
        status,
        message,
        g_growing_light.is_on(),
        g_pump.is_on(),
        &ack_error,
        reportedLightIntensityPercent());
  }

  if (!reported) {
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("command_result_upload_failed", "command result update failed");
    Serial.printf("[platform] command result update failed: %s\n", ack_error.c_str());
    return false;
  }
  return true;
}

bool reportPendingCaptureCommandResult(const char* status, const char* message, const char* error_code) {
  PlatformCommand command{};
  command.id = g_pending_capture_command.command_id;
  command.target = "camera";
  command.action = "capture";
  command.valid = command.id > 0;
  command.contract_native = g_pending_capture_command.contract_native;
  command.command_id = g_pending_capture_command.contract_command_id;
  command.command_type = g_pending_capture_command.contract_command_type;
  return reportPlatformCommandResult(command, status, message, error_code);
}

bool handleAmbientLedBeltCommand(const PlatformCommand& command, String* message, const char** error_code) {
  plantlab::ambient_led_belt::AmbientLedBeltCommand led_command;
  String parse_error;
  const String payload = command.ambient_led_belt_payload_json.length() > 0 ? command.ambient_led_belt_payload_json : command.value;
  if (payload.length() == 0 || !plantlab::ambient_led_belt::parseCommandJson(payload, &led_command, &parse_error)) {
    if (message != nullptr) {
      *message = parse_error.length() > 0 ? parse_error : "invalid ambient LED belt command";
    }
    if (error_code != nullptr) {
      *error_code = PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
    }
    return false;
  }

  String apply_message;
  String apply_error;
  if (!g_ambient_led_belt.applyCommand(led_command, &apply_message, &apply_error)) {
    if (message != nullptr) {
      *message = apply_error.length() > 0 ? apply_error : "ambient LED belt command failed";
    }
    if (error_code != nullptr) {
      *error_code = apply_error.indexOf("invalid") >= 0 ? PLANTLAB_COMMAND_ERROR_INVALID_PARAMS
                                                        : PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR;
    }
    return false;
  }
  if (led_command.save_config && !saveAmbientLedBeltConfig()) {
    if (message != nullptr) {
      *message = "ambient LED belt command applied but config save failed";
    }
    if (error_code != nullptr) {
      *error_code = PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR;
    }
    return false;
  }
  if (message != nullptr) {
    *message = apply_message.length() > 0 ? apply_message : "ambient LED belt command applied";
  }
  if (error_code != nullptr) {
    *error_code = nullptr;
  }
  Serial.printf(
      "[ambient-led-belt] command applied mode=%s enabled=%u brightness=%u logical_pixels=%u color_order=%s\n",
      plantlab::ambient_led_belt::modeName(g_ambient_led_belt.state().mode),
      g_ambient_led_belt.state().enabled ? 1U : 0U,
      static_cast<unsigned int>(g_ambient_led_belt.state().requested_brightness),
      static_cast<unsigned int>(g_ambient_led_belt.state().logical_pixel_count),
      plantlab::ambient_led_belt::colorOrderName(g_ambient_led_belt.state().color_order));
  return true;
}

void execute_platform_command(const PlatformCommand& command) {
  String message;
  bool success = true;
  const char* command_error_code = nullptr;

  if (command.contract_native) {
    Serial.printf(
        "[platform] contract command received id=%s type=%s legacy_id=%d\n",
        command.command_id.c_str(),
        command.command_type.c_str(),
        command.id);
    reportPlatformCommandResult(command, PLANTLAB_COMMAND_STATUS_ACKED, "command accepted");
    if (!plantlab::contracts::isSupportedMasterCommand(command)) {
      message = "contract command is not supported by this firmware build";
      recordLastCommandResult(command.id, "rejected", message, "command_rejected");
      recordDiagnosticError("command_rejected", message);
      reportPlatformCommandResult(
          command,
          PLANTLAB_COMMAND_STATUS_REJECTED,
          message.c_str(),
          plantlab::contracts::unsupportedCommandErrorCode(command));
      return;
    }
  }

  if (command.target == "grow_light" || command.target == "light") {
    if (command.action == "on") {
      g_growing_light.set_on(true);
      message = "grow light turned on";
    } else if (command.action == "off") {
      g_growing_light.set_on(false);
      message = "grow light turned off";
    } else if (command.action == "set_intensity") {
      int intensity_percent = 0;
      if (!g_growing_light.supports_intensity_control()) {
        success = false;
        message = "grow light intensity control is not supported";
      } else if (!parseLightIntensityPercent(command.value, &intensity_percent)) {
        success = false;
        message = "invalid grow light intensity";
      } else {
        g_growing_light.set_intensity_percent(intensity_percent);
        message = "grow light intensity set to " + String(intensity_percent) + "%";
      }
    } else if (command.action == "set_channel_intensity") {
      String channel;
      int intensity_percent = 0;
      if (!g_growing_light.supports_intensity_control()) {
        success = false;
        message = "grow light channel intensity control is not supported";
      } else if (!parseGrowLightChannelIntensityCommand(command.value, &channel, &intensity_percent)) {
        success = false;
        command_error_code = PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
        message = "invalid grow light channel intensity";
      } else if (channel == "red") {
        g_growing_light.set_primary_intensity_percent(intensity_percent);
        message = "grow light red intensity set to " + String(intensity_percent) + "%";
      } else if (channel == "white") {
        g_growing_light.set_secondary_intensity_percent(intensity_percent);
        message = "grow light white intensity set to " + String(intensity_percent) + "%";
      } else {
        success = false;
        command_error_code = PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
        message = "unsupported grow light channel";
      }
    } else {
      success = false;
      message = "unsupported grow light command";
    }
  } else if (command.target == "ambient_led_belt") {
    if (command.action == "set") {
      success = handleAmbientLedBeltCommand(command, &message, &command_error_code);
    } else {
      success = false;
      command_error_code = PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
      message = "unsupported ambient LED belt command";
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
  } else if (command.target == "camera" && command.action == "capture") {
    Serial.printf("[platform] received backend capture command id=%d value=%s\n", command.id, command.value.c_str());
    startPendingCaptureCommand(command, millis());
    return;
  } else if (command.target == "ota" && command.action == "start") {
    if (!g_ota_update_manager) {
      message = "OTA manager is not available";
      recordLastCommandResult(command.id, "rejected", message, "ota_unavailable");
      recordDiagnosticError("ota_unavailable", message);
      reportPlatformCommandResult(
          command,
          PLANTLAB_COMMAND_STATUS_REJECTED,
          message.c_str(),
          PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR);
      return;
    }

    plantlab::OtaStartRequest ota_request;
    ota_request.legacy_command_id = command.id;
    ota_request.command_id = command.command_id;
    ota_request.command_type = command.command_type;
    ota_request.target_version = command.ota_target_version;
    ota_request.download_url = command.ota_download_url;
    ota_request.checksum_sha256 = command.ota_checksum_sha256;
    ota_request.hardware_model = command.ota_hardware_model;
    ota_request.firmware_channel = command.ota_firmware_channel;
    ota_request.release_id = command.ota_release_id;
    ota_request.artifact_size_bytes = command.ota_artifact_size_bytes;

    String ota_error;
    if (!g_ota_update_manager->startContractUpdate(ota_request, &ota_error)) {
      const bool rejected = ota_error.startsWith("START_OTA missing") ||
                            ota_error.startsWith("START_OTA hardware_model") ||
                            ota_error.startsWith("START_OTA checksum") ||
                            ota_error.startsWith("START_OTA download_url") ||
                            ota_error == "OTA update already in progress";
      recordLastCommandResult(
          command.id,
          rejected ? "rejected" : "failed",
          ota_error,
          rejected ? "ota_command_rejected" : "ota_command_failed");
      recordDiagnosticError(rejected ? "ota_command_rejected" : "ota_command_failed", ota_error);
      if (rejected || ota_error != "OTA install failed") {
        reportPlatformCommandResult(
            command,
            rejected ? PLANTLAB_COMMAND_STATUS_REJECTED : PLANTLAB_COMMAND_STATUS_FAILED,
            ota_error.c_str(),
            rejected ? PLANTLAB_COMMAND_ERROR_INVALID_PARAMS : PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR);
      }
    }
    return;
  } else if (command.target == "system" && command.action == "reboot") {
    message = "device reboot scheduled";
    scheduleRestart(1500, "contract_reboot_command");
  } else if (command.target == "diagnostics" && command.action == "request") {
    if (command.value.length() > 0 && handleCameraProvisioningCommandLine(command.value, &message, &success)) {
      command_error_code = success ? nullptr : PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
    } else {
      message = "diagnostics heartbeat sent";
    }
  } else {
    success = false;
    message = "unsupported command target";
  }

  String status_error;
  if (!g_platform_client->send_hardware_heartbeat(platform_status(message), &status_error)) {
    ++g_diagnostic_error_counters.upload_failures;
    recordDiagnosticError("heartbeat_upload_failed", "heartbeat upload failed");
  }
  const bool rejected = !success && command_error_code == PLANTLAB_COMMAND_ERROR_INVALID_PARAMS;
  recordLastCommandResult(command.id, success ? "completed" : rejected ? "rejected" : "failed", message, success ? "ok" : "command_failed");
  if (!success) {
    recordDiagnosticError("command_failed", message);
  }
  if (!reportPlatformCommandResult(
          command,
          success ? PLANTLAB_COMMAND_STATUS_COMPLETED : rejected ? PLANTLAB_COMMAND_STATUS_REJECTED : PLANTLAB_COMMAND_STATUS_FAILED,
          message.c_str(),
          success ? nullptr : command_error_code != nullptr ? command_error_code : PLANTLAB_COMMAND_ERROR_INTERNAL_ERROR)) {
    Serial.println("[platform] command result update failed");
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
  const String hardware_id = stableHardwareDeviceId();
  const unsigned long poll_started_at = millis();
  int count = g_platform_client->poll_contract_commands(
      hardware_id.c_str(),
      PLANTLAB_NODE_ROLE_MASTER,
      kSoftwareVersion,
      "esp32_master",
      commands,
      4,
      &error);
  if (count < 0) {
    const String contract_error = error;
    Serial.printf("[platform] contract command poll failed, falling back to legacy: %s\n", contract_error.c_str());
    error = "";
    count = g_platform_client->poll_hardware_pending_commands(commands, 4, &error);
    if (count < 0) {
      Serial.printf("[platform] command poll failed: %s\n", error.c_str());
      recordCommandPollResult("error", error, poll_started_at, millis());
      return;
    }
    recordCommandPollResult("legacy_ok", contract_error, poll_started_at, millis());
  } else {
    recordCommandPollResult("ok", "", poll_started_at, millis());
  }

  for (int i = 0; i < count; ++i) {
    if (!commands[i].valid) {
      continue;
    }
    execute_platform_command(commands[i]);
  }
}

void setup() {
  pinMode(AMBIENT_LED_BELT_DATA_GPIO, OUTPUT);
  digitalWrite(AMBIENT_LED_BELT_DATA_GPIO, LOW);

  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== PlantLab ESP32 Master Node ===");
  Serial.printf("Board: %s\n", BOARD_NAME);
  Serial.printf(
      "Firmware version: %s (%d)\n",
      kSoftwareVersion,
      plantlab::kMasterSoftwareVersionCode);
  Serial.printf("Provisioning env: %s\n", PLANTLAB_ENV_LABEL);
  Serial.printf("I2C environmental sensor bus: SDA GPIO%d SCL GPIO%d (AHT20 air, MCP9808 water)\n", PIN_I2C_SDA, PIN_I2C_SCL);
  Serial.printf(
      "Water level pads: top GPIO%d TOUCH%d middle GPIO%d TOUCH%d bottom GPIO%d TOUCH%d\n",
      WATER_LEVEL_TOP_GPIO,
      WATER_LEVEL_TOP_TOUCH_CHANNEL,
      WATER_LEVEL_MIDDLE_GPIO,
      WATER_LEVEL_MIDDLE_TOUCH_CHANNEL,
      WATER_LEVEL_BOTTOM_GPIO,
      WATER_LEVEL_BOTTOM_TOUCH_CHANNEL);
  Serial.printf("Moisture ADC pin: GPIO%d\n", PIN_SOIL_MOISTURE_ADC);
  Serial.printf("WS2811 ambient LED belt DIN pin: GPIO%d\n", AMBIENT_LED_BELT_DATA_GPIO);
  Serial.printf(
      "PCB grow LED red CTRL pin: GPIO%d white CTRL pin: GPIO%d\n",
      PIN_GROW_LIGHT_RED_CTRL,
      PIN_GROW_LIGHT_WHITE_CTRL);
  Serial.printf("Legacy pump gate pin: GPIO%d\n", PIN_PUMP_MOSFET_GATE);
  Serial.printf("Provisioning button pin: GPIO%d\n", PIN_POWER_BUTTON);
  Serial.printf("Status LED pin: GPIO%d\n", PIN_STATUS_LED);
  if (String(PLANTLAB_PLATFORM_URL).length() > 0) {
    Serial.printf("Fallback platform URL: %s\n", PLANTLAB_PLATFORM_URL);
  }
  if (String(PLANTLAB_PROVISIONING_API_URL).length() > 0) {
    Serial.printf("Fallback provisioning URL: %s\n", PLANTLAB_PROVISIONING_API_URL);
  }
  Serial.printf(
      "Camera capture schedule: %s (%lu ms top phase=%us side phase=%us)\n",
      PLANTLAB_CAMERA_CAPTURE_ENABLED ? "enabled" : "disabled",
      static_cast<unsigned long>(PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS),
      static_cast<unsigned int>(kTopCameraCapturePhaseSeconds),
      static_cast<unsigned int>(kSideCameraCapturePhaseSeconds));
  initReliabilityBootCounter();
  const bool ambient_led_belt_config_ok = loadAmbientLedBeltConfig();

  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_POWER_BUTTON, INPUT_PULLUP);

  g_status_led.begin();
  g_power_button.begin();
  g_status_led.set_mode(StatusLedMode::kBooting);
  g_i2c_environment.begin();
  g_moisture.begin();
  g_water_level.begin(millis());
  loadWaterLevelCalibration();
  g_growing_light.begin();
  g_pump.begin();
  if (ambient_led_belt_config_ok) {
    String led_error;
    if (g_ambient_led_belt.begin(&led_error)) {
      Serial.println("[ambient-led-belt] initialized OFF");
    } else {
      Serial.printf("[ambient-led-belt] unavailable after init: %s\n", led_error.c_str());
    }
  }

  Serial.printf(
      "[i2c] environmental sensors SDA GPIO%d SCL GPIO%d AHT20=%s MCP9808=%s\n",
      g_i2c_environment.sda_pin(),
      g_i2c_environment.scl_pin(),
      g_i2c_environment.aht20_present() ? "present" : "not found",
      g_i2c_environment.mcp9808_present() ? "present" : "not found");
  if (g_moisture.enabled()) {
    Serial.println("[moisture] sensor initialized");
  } else {
    Serial.println("[moisture] sensor disabled: GPIO1 reserved for WS2811 ambient LED belt DIN");
  }
  Serial.println("[water-temp] MCP9808 sensor path initialized");
  Serial.println("[water-level] three-pad touch sensor initialized");
  Serial.println("[grow-light] initialized OFF");
  Serial.println("[pump] initialized OFF");
  plantlab::time_sync::begin();
  capture_schedule_init(
      &g_camera_capture_schedule,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0,
      PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS,
      static_cast<uint32_t>(kTopCameraCapturePhaseSeconds) * 1000UL,
      millis());
  capture_schedule_init(
      &g_side_camera_capture_schedule,
      PLANTLAB_CAMERA_CAPTURE_ENABLED != 0,
      PLANTLAB_CAMERA_CAPTURE_INTERVAL_MS,
      static_cast<uint32_t>(kSideCameraCapturePhaseSeconds) * 1000UL,
      millis());

  loadConfig();
  if (hasWifiCredentials()) {
    Serial.println("[provisioning] saved Wi-Fi config found, connecting to Wi-Fi");
    connectToWiFi();
  } else {
    Serial.println("[provisioning] no saved Wi-Fi config, starting BLE provisioning mode");
    startBleProvisioningMode();
  }
}

void loop() {
  const unsigned long now = millis();
  checkProvisioningButton();
  g_status_led.update(now);
  g_pump.update();
  g_ambient_led_belt.tick(now);
  g_water_level.update(now);
  serviceSerialDiagnostics(now);
  serviceWaterLevelDiagnostics(now);

  if (g_provisioning_mode) {
    serviceBleProvisioning(now);
    if (g_softap_provisioning_active) {
      g_web_server.handleClient();
    }
    if (g_restart_scheduled && static_cast<long>(now - g_restart_at_ms) >= 0) {
      Serial.printf(
          "[provisioning] rebooting ESP32 reason=%s\n",
          g_restart_reason.length() > 0 ? g_restart_reason.c_str() : "unspecified");
      stopBleProvisioningMode();
      delay(100);
      ESP.restart();
    }
    if (g_provisioning_mode) {
      return;
    }
  }

  if (g_restart_scheduled && static_cast<long>(now - g_restart_at_ms) >= 0) {
    Serial.printf(
        "[system] rebooting ESP32 reason=%s\n",
        g_restart_reason.length() > 0 ? g_restart_reason.c_str() : "unspecified");
    delay(100);
    ESP.restart();
  }

  if (provisioningPriorityActive()) {
    return;
  }

  connectToWiFi();
  plantlab::time_sync::service(g_wifi_ready, now);
  if (g_wifi_ready) {
    setupEspNow();
  }

  if (g_wifi_ready && hasPendingClaim()) {
    if (registerProvisionedDevice()) {
      rebuildPlatformClient();
    }
  }

  if (platform_enabled()) {
    ensureMasterDeviceNodeRegistered(now);
    serviceCameraProvisioning(now);
    serviceCameraCaptureFlight(now);
    servicePendingCaptureCommand(now);
    poll_platform_commands(now);
    pollCameraCaptureSchedule(now);
    send_platform_status(now);
    send_platform_reading(now);
    if (g_ota_update_manager && !hasPendingClaim() && !provisioningPriorityActive()) {
      g_ota_update_manager->service(now);
    }
  }

  if (now - g_last_local_sensor_read_ms >= PLANTLAB_LOCAL_SENSOR_READ_INTERVAL_MS) {
    g_last_local_sensor_read_ms = now;
    if (!platform_enabled()) {
      read_platform_reading();
    }
  }
}
