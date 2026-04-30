#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>

#include "camera/xiao_camera.h"
#include "config.h"
#include "platform/platform_client.h"

namespace {
XiaoCamera g_camera;
PlatformClient g_platform_client(
    PLANTLAB_PLATFORM_URL,
    PLANTLAB_DEVICE_ID,
    PLANTLAB_DEVICE_TOKEN);
unsigned long g_last_capture_ms = 0;
unsigned long g_last_wifi_attempt_ms = 0;
bool g_wifi_ready = false;
}

bool platform_enabled() {
  return g_platform_client.configured() && String(PLANTLAB_WIFI_SSID).length() > 0;
}

void ensure_wifi_connected() {
  if (!platform_enabled()) {
    return;
  }
  if (WiFi.status() == WL_CONNECTED) {
    if (!g_wifi_ready) {
      g_wifi_ready = true;
      Serial.printf("[camera-platform] wifi connected ip=%s\n", WiFi.localIP().toString().c_str());
    }
    return;
  }
  g_wifi_ready = false;
  if (millis() - g_last_wifi_attempt_ms < 5000) {
    return;
  }
  g_last_wifi_attempt_ms = millis();
  Serial.printf("[camera-platform] connecting to %s\n", PLANTLAB_WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.disconnect(true, true);
  delay(200);
  WiFi.begin(PLANTLAB_WIFI_SSID, PLANTLAB_WIFI_PASSWORD);

  const unsigned long started_at = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started_at < PLANTLAB_WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
  }
  if (WiFi.status() == WL_CONNECTED) {
    g_wifi_ready = true;
    Serial.printf("[camera-platform] wifi connected ip=%s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[camera-platform] wifi connect timed out");
    WiFi.disconnect();
  }
}

void capture_and_upload() {
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    Serial.println("[camera-platform] capture failed");
    return;
  }

  String error;
  const bool ok = g_platform_client.upload_jpeg(
      frame->buf,
      frame->len,
      "esp32-camera.jpg",
      &error);
  esp_camera_fb_return(frame);

  if (ok) {
    Serial.println("[camera-platform] image uploaded");
  } else {
    Serial.printf("[camera-platform] image upload failed: %s\n", error.c_str());
  }
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println();
  Serial.println("=== PlantLab ESP32 Camera Platform Test ===");
  if (platform_enabled()) {
    Serial.printf("[camera-platform] base_url: %s\n", g_platform_client.base_url().c_str());
    Serial.printf("[camera-platform] device_id: %d\n", g_platform_client.device_id());
    ensure_wifi_connected();
  } else {
    Serial.println("[camera-platform] disabled (missing Wi-Fi or platform credentials)");
  }

  if (!g_camera.begin()) {
    Serial.println("[camera-platform] camera init failed");
    return;
  }
  Serial.println("[camera-platform] camera initialized");
}

void loop() {
  ensure_wifi_connected();
  if (!platform_enabled() || !g_wifi_ready) {
    delay(100);
    return;
  }
  if (millis() - g_last_capture_ms >= PLANTLAB_IMAGE_INTERVAL_MS) {
    g_last_capture_ms = millis();
    capture_and_upload();
  }
}
