#include <Arduino.h>
#include <WiFi.h>

#include "config.h"

namespace {
unsigned long g_last_connect_attempt_ms = 0;
unsigned long g_last_status_log_ms = 0;
bool g_reported_connected = false;
}

const char* wifi_event_label(arduino_event_id_t event) {
  switch (event) {
    case ARDUINO_EVENT_WIFI_STA_START:
      return "sta_start";
    case ARDUINO_EVENT_WIFI_STA_CONNECTED:
      return "sta_connected";
    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      return "sta_disconnected";
    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      return "got_ip";
    case ARDUINO_EVENT_WIFI_SCAN_DONE:
      return "scan_done";
    default:
      return "other";
  }
}

const char* wifi_status_label(wl_status_t status) {
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

bool wifi_test_enabled() {
  return String(PLANTLAB_WIFI_SSID).length() > 0;
}

void print_scan_results() {
  Serial.println("[wifi-test] scanning nearby networks...");
  const int network_count = WiFi.scanNetworks();
  if (network_count <= 0) {
    Serial.println("[wifi-test] no networks found");
    return;
  }

  bool found_target = false;
  for (int i = 0; i < network_count; ++i) {
    const String ssid = WiFi.SSID(i);
    const int32_t rssi = WiFi.RSSI(i);
    const wifi_auth_mode_t auth = WiFi.encryptionType(i);
    Serial.printf(
        "[wifi-test] network[%d] ssid=%s rssi=%d auth=%d channel=%d\n",
        i,
        ssid.c_str(),
        static_cast<int>(rssi),
        static_cast<int>(auth),
        WiFi.channel(i));
    if (ssid == String(PLANTLAB_WIFI_SSID)) {
      found_target = true;
    }
  }
  Serial.printf(
      "[wifi-test] target %s %s visible in scan\n",
      PLANTLAB_WIFI_SSID,
      found_target ? "is" : "is NOT");
  WiFi.scanDelete();
}

void on_wifi_event(arduino_event_id_t event, arduino_event_info_t info) {
  Serial.printf("[wifi-test] event=%s(%d)\n", wifi_event_label(event), static_cast<int>(event));
  if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    Serial.printf(
        "[wifi-test] disconnect reason=%d\n",
        static_cast<int>(info.wifi_sta_disconnected.reason));
  }
  if (event == ARDUINO_EVENT_WIFI_STA_GOT_IP) {
    Serial.printf(
        "[wifi-test] got_ip=%s\n",
        IPAddress(info.got_ip.ip_info.ip.addr).toString().c_str());
  }
}

void log_status(bool force = false) {
  const unsigned long now = millis();
  if (!force && now - g_last_status_log_ms < 3000) {
    return;
  }
  g_last_status_log_ms = now;

  const wl_status_t status = WiFi.status();
  if (status == WL_CONNECTED) {
    Serial.printf(
        "[wifi-test] status=%s ip=%s rssi=%d dBm ssid=%s\n",
        wifi_status_label(status),
        WiFi.localIP().toString().c_str(),
        WiFi.RSSI(),
        WiFi.SSID().c_str());
  } else {
    Serial.printf("[wifi-test] status=%s\n", wifi_status_label(status));
  }
}

void begin_wifi_attempt() {
  print_scan_results();
  Serial.printf("[wifi-test] connecting to %s\n", PLANTLAB_WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.disconnect(true, true);
  delay(300);
  WiFi.begin(PLANTLAB_WIFI_SSID, PLANTLAB_WIFI_PASSWORD);
  g_last_connect_attempt_ms = millis();
  g_reported_connected = false;
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println();
  Serial.println("=== PlantLab XIAO Wi-Fi Test ===");

  if (!wifi_test_enabled()) {
    Serial.println("[wifi-test] missing PLANTLAB_WIFI_SSID in platform_secrets.h");
    return;
  }

  Serial.printf("[wifi-test] target ssid: %s\n", PLANTLAB_WIFI_SSID);
  WiFi.onEvent(on_wifi_event);
  begin_wifi_attempt();
}

void loop() {
  if (!wifi_test_enabled()) {
    delay(1000);
    return;
  }

  const wl_status_t status = WiFi.status();
  if (status == WL_CONNECTED) {
    if (!g_reported_connected) {
      g_reported_connected = true;
      Serial.printf(
          "[wifi-test] connected ip=%s gateway=%s rssi=%d dBm\n",
          WiFi.localIP().toString().c_str(),
          WiFi.gatewayIP().toString().c_str(),
          WiFi.RSSI());
    }
    log_status();
    delay(250);
    return;
  }

  log_status();

  const unsigned long now = millis();
  if (now - g_last_connect_attempt_ms >= PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    Serial.printf(
        "[wifi-test] connect attempt timed out after %lu ms; retrying\n",
        static_cast<unsigned long>(PLANTLAB_WIFI_CONNECT_TIMEOUT_MS));
    begin_wifi_attempt();
  }

  delay(250);
}
