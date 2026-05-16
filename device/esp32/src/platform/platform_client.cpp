#include "platform/platform_client.h"

#include <memory>

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

namespace {
constexpr uint32_t kHttpTimeoutMs = 10000;
constexpr uint32_t kOtaDownloadTimeoutMs = 30000;
constexpr uint32_t kImageUploadTimeoutMs = 15000;
constexpr uint32_t kImageUploadWriteIdleTimeoutMs = 5000;
constexpr size_t kImageUploadChunkSize = 1024;
constexpr char kDeviceTokenHeader[] = "X-Device-Token";
constexpr char kJsonContentType[] = "application/json";
constexpr char kMultipartContentType[] = "multipart/form-data; boundary=";

bool write_all(Client& client, const uint8_t* bytes, size_t length, uint32_t idle_timeout_ms) {
  size_t written_total = 0;
  uint32_t last_progress_at = millis();
  while (written_total < length) {
    if (!client.connected()) {
      return false;
    }
    if (millis() - last_progress_at >= idle_timeout_ms) {
      return false;
    }

    const size_t remaining = length - written_total;
    const size_t chunk_size = remaining > kImageUploadChunkSize ? kImageUploadChunkSize : remaining;
    const size_t written = client.write(bytes + written_total, chunk_size);
    if (written == 0) {
      delay(10);
      continue;
    }

    written_total += written;
    last_progress_at = millis();
  }
  return true;
}

bool write_string(Client& client, const String& value, uint32_t idle_timeout_ms) {
  return write_all(
      client,
      reinterpret_cast<const uint8_t*>(value.c_str()),
      value.length(),
      idle_timeout_ms);
}
}

PlatformClient::PlatformClient(const char* base_url, int device_id, const char* device_token)
    : base_url_(base_url == nullptr ? "" : String(base_url)),
      device_id_(device_id),
      device_token_(device_token == nullptr ? "" : String(device_token)) {
  base_url_.trim();
  if (base_url_.endsWith("/")) {
    base_url_.remove(base_url_.length() - 1);
  }
  device_token_.trim();
}

bool PlatformClient::configured() const {
  return base_url_.length() > 0 && device_id_ > 0 && device_token_.length() > 0;
}

const String& PlatformClient::base_url() const {
  return base_url_;
}

int PlatformClient::device_id() const {
  return device_id_;
}

bool PlatformClient::send_reading(const PlatformReading& reading, String* error) {
  StaticJsonDocument<512> doc;
  doc["device_id"] = device_id_;
  if (reading.hardware_device_id.length() > 0) {
    doc["hardware_device_id"] = reading.hardware_device_id;
  }
  if (reading.temperature_valid) {
    doc["temperature"] = reading.temperature_c;
  }
  if (reading.humidity_valid) {
    doc["humidity"] = reading.humidity_percent;
  }
  if (reading.moisture_valid) {
    doc["moisture"] = reading.moisture_percent;
  }
  doc["light_on"] = reading.light_on;
  doc["pump_on"] = reading.pump_on;
  doc["pump_status"] = reading.pump_status;
  if (reading.idempotency_key.length() > 0) {
    doc["idempotency_key"] = reading.idempotency_key;
  }

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/data", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "reading upload failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::send_hardware_reading(const PlatformReading& reading, String* error) {
  StaticJsonDocument<512> doc;
  if (reading.hardware_device_id.length() > 0) {
    doc["hardware_device_id"] = reading.hardware_device_id;
  }
  if (reading.temperature_valid) {
    doc["temperature"] = reading.temperature_c;
  }
  if (reading.humidity_valid) {
    doc["humidity"] = reading.humidity_percent;
  }
  if (reading.moisture_valid) {
    doc["moisture"] = reading.moisture_percent;
  }
  doc["light_on"] = reading.light_on;
  doc["pump_on"] = reading.pump_on;
  doc["pump_status"] = reading.pump_status;
  if (reading.idempotency_key.length() > 0) {
    doc["idempotency_key"] = reading.idempotency_key;
  }

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/hardware/readings", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "hardware reading upload failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::send_status(const PlatformStatus& status, String* error) {
  StaticJsonDocument<192> doc;
  doc["light_on"] = status.light_on;
  doc["pump_on"] = status.pump_on;
  doc["message"] = status.message;
  if (status.software_version.length() > 0) {
    doc["software_version"] = status.software_version;
  }

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/devices/" + String(device_id_) + "/status", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "status upload failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::send_hardware_heartbeat(const PlatformStatus& status, String* error) {
  StaticJsonDocument<1024> doc;
  if (status.hardware_device_id.length() > 0) {
    doc["hardware_device_id"] = status.hardware_device_id;
  }
  if (status.node_role.length() > 0) {
    doc["node_role"] = status.node_role;
  }
  doc["status"] = status.status.length() > 0 ? status.status : "online";
  doc["light_on"] = status.light_on;
  doc["pump_on"] = status.pump_on;
  doc["message"] = status.message;
  if (status.software_version.length() > 0) {
    doc["software_version"] = status.software_version;
  }
  if (status.diagnostics.valid) {
    JsonObject diagnostics = doc.createNestedObject("diagnostics");
    diagnostics["schema_version"] = 1;
    if (status.diagnostics.has_uptime_seconds) {
      diagnostics["uptime_seconds"] = status.diagnostics.uptime_seconds;
    }
    if (status.diagnostics.has_wifi_rssi_dbm) {
      diagnostics["wifi_rssi_dbm"] = status.diagnostics.wifi_rssi_dbm;
    }
    if (status.diagnostics.reboot_reason.length() > 0) {
      diagnostics["reboot_reason"] = status.diagnostics.reboot_reason;
    }
    if (status.diagnostics.provisioning_state.length() > 0) {
      diagnostics["provisioning_state"] = status.diagnostics.provisioning_state;
    }
    if (status.diagnostics.has_last_sensor_reading_age_seconds) {
      diagnostics["last_sensor_reading_age_seconds"] = status.diagnostics.last_sensor_reading_age_seconds;
    }
    if (status.diagnostics.has_last_camera_image_upload_age_seconds) {
      diagnostics["last_camera_image_upload_age_seconds"] = status.diagnostics.last_camera_image_upload_age_seconds;
    }
    if (status.diagnostics.has_last_command) {
      JsonObject last_command = diagnostics.createNestedObject("last_command");
      if (status.diagnostics.last_command_id > 0) {
        last_command["id"] = status.diagnostics.last_command_id;
      }
      if (status.diagnostics.last_command_status.length() > 0) {
        last_command["status"] = status.diagnostics.last_command_status;
      }
      if (status.diagnostics.last_command_code.length() > 0) {
        last_command["code"] = status.diagnostics.last_command_code;
      }
      if (status.diagnostics.last_command_message.length() > 0) {
        last_command["message"] = status.diagnostics.last_command_message;
      }
      if (status.diagnostics.has_last_command_age_seconds) {
        last_command["age_seconds"] = status.diagnostics.last_command_age_seconds;
      }
    }
    if (status.diagnostics.has_error_counters) {
      JsonObject counters = diagnostics.createNestedObject("error_counters");
      counters["wifi_reconnects"] = status.diagnostics.error_counters.wifi_reconnects;
      counters["upload_failures"] = status.diagnostics.error_counters.upload_failures;
      counters["ble_provisioning_failures"] = status.diagnostics.error_counters.ble_provisioning_failures;
      counters["espnow_failures"] = status.diagnostics.error_counters.espnow_failures;
    }
    if (status.diagnostics.last_error_code.length() > 0 || status.diagnostics.last_error_message.length() > 0) {
      JsonObject last_error = diagnostics.createNestedObject("last_error");
      if (status.diagnostics.last_error_code.length() > 0) {
        last_error["code"] = status.diagnostics.last_error_code;
      }
      if (status.diagnostics.last_error_message.length() > 0) {
        last_error["message"] = status.diagnostics.last_error_message;
      }
    }
  }

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/hardware/heartbeat", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "hardware heartbeat failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

int PlatformClient::poll_pending_commands(PlatformCommand* commands, size_t max_commands, String* error) {
  int status_code = 0;
  String response_body;
  if (!json_get("/api/devices/" + String(device_id_) + "/commands/pending", &status_code, &response_body)) {
    set_error(error, response_body);
    return -1;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "command poll failed with HTTP " + String(status_code) + ": " + response_body);
    return -1;
  }

  DynamicJsonDocument doc(4096);
  DeserializationError json_error = deserializeJson(doc, response_body);
  if (json_error) {
    set_error(error, "command poll JSON parse failed");
    return -1;
  }

  JsonArray array = doc.as<JsonArray>();
  size_t count = 0;
  for (JsonVariant item : array) {
    if (count >= max_commands) {
      break;
    }
    const char* target = item["target"] | "";
    const char* action = item["action"] | "";
    const char* value = item["value"] | "";
    commands[count].id = item["id"] | 0;
    commands[count].target = String(target);
    commands[count].action = String(action);
    commands[count].value = String(value);
    commands[count].valid = commands[count].id > 0;
    ++count;
  }
  return static_cast<int>(count);
}

int PlatformClient::poll_hardware_pending_commands(PlatformCommand* commands, size_t max_commands, String* error) {
  int status_code = 0;
  String response_body;
  if (!json_get("/api/hardware/commands/pending", &status_code, &response_body)) {
    set_error(error, response_body);
    return -1;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "hardware command poll failed with HTTP " + String(status_code) + ": " + response_body);
    return -1;
  }

  DynamicJsonDocument doc(4096);
  DeserializationError json_error = deserializeJson(doc, response_body);
  if (json_error) {
    set_error(error, "hardware command poll JSON parse failed");
    return -1;
  }

  JsonArray array = doc.as<JsonArray>();
  size_t count = 0;
  for (JsonVariant item : array) {
    if (count >= max_commands) {
      break;
    }
    const char* target = item["target"] | "";
    const char* action = item["action"] | "";
    const char* value = item["value"] | "";
    commands[count].id = item["id"] | 0;
    commands[count].target = String(target);
    commands[count].action = String(action);
    commands[count].value = String(value);
    commands[count].valid = commands[count].id > 0;
    ++count;
  }
  return static_cast<int>(count);
}

bool PlatformClient::acknowledge_command(
    int command_id,
    const char* status,
    const char* message,
    bool light_on,
    bool pump_on,
    String* error) {
  StaticJsonDocument<256> doc;
  doc["status"] = status == nullptr ? "failed" : status;
  doc["message"] = message == nullptr ? "" : message;
  doc["light_on"] = light_on;
  doc["pump_on"] = pump_on;

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post(
          "/api/devices/" + String(device_id_) + "/commands/" + String(command_id) + "/ack",
          body,
          &status_code,
          &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "command ack failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::report_hardware_command_result(
    int command_id,
    const char* status,
    const char* message,
    bool light_on,
    bool pump_on,
    String* error) {
  StaticJsonDocument<256> doc;
  doc["status"] = status == nullptr ? "failed" : status;
  doc["message"] = message == nullptr ? "" : message;
  doc["light_on"] = light_on;
  doc["pump_on"] = pump_on;

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post(
          "/api/hardware/commands/" + String(command_id) + "/result",
          body,
          &status_code,
          &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(
        error,
        "hardware command result failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::upload_jpeg(
    const uint8_t* bytes,
    size_t length,
    const char* filename,
    const char* source_hardware_device_id,
    const char* idempotency_key,
    int* http_status_code,
    String* error) {
  if (bytes == nullptr || length == 0) {
    set_error(error, "image upload skipped: empty buffer");
    return false;
  }

  String host;
  String base_path;
  uint16_t port = 0;
  bool secure = false;
  if (!parse_url(&host, &port, &base_path, &secure)) {
    set_error(error, "invalid platform URL");
    return false;
  }

  String request_path = base_path + "/api/image";
  String boundary = "----PlantLabESP32Boundary7MA4YWxkTrZu0gW";
  String file_name = filename == nullptr ? "esp32.jpg" : String(filename);

  String prefix =
      "--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n" +
      String(device_id_) + "\r\n";
  if (source_hardware_device_id != nullptr && String(source_hardware_device_id).length() > 0) {
    prefix +=
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"source_hardware_device_id\"\r\n\r\n" +
        String(source_hardware_device_id) + "\r\n";
  }
  if (idempotency_key != nullptr && String(idempotency_key).length() > 0) {
    prefix +=
        "--" + boundary + "\r\n"
        "Content-Disposition: form-data; name=\"idempotency_key\"\r\n\r\n" +
        String(idempotency_key) + "\r\n";
  }
  prefix +=
      "--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"file\"; filename=\"" + file_name + "\"\r\n"
      "Content-Type: image/jpeg\r\n\r\n";
  String suffix = "\r\n--" + boundary + "--\r\n";
  const size_t content_length = prefix.length() + length + suffix.length();

  std::unique_ptr<Client> client;
  if (secure) {
    auto* secure_client = new WiFiClientSecure();
    secure_client->setInsecure();
    client.reset(secure_client);
  } else {
    client.reset(new WiFiClient());
  }

  if (!client->connect(host.c_str(), port)) {
    set_error(error, "image upload connect failed");
    return false;
  }
  client->setTimeout(kImageUploadTimeoutMs);

  const String headers =
      "POST " + request_path + " HTTP/1.1\r\n"
      "Host: " + host + "\r\n" +
      String(kDeviceTokenHeader) + ": " + auth_header_value() + "\r\n"
      "Connection: close\r\n"
      "Content-Type: " + String(kMultipartContentType) + boundary + "\r\n"
      "Content-Length: " + String(content_length) + "\r\n\r\n";
  if (!write_string(*client, headers, kImageUploadWriteIdleTimeoutMs) ||
      !write_string(*client, prefix, kImageUploadWriteIdleTimeoutMs) ||
      !write_all(*client, bytes, length, kImageUploadWriteIdleTimeoutMs) ||
      !write_string(*client, suffix, kImageUploadWriteIdleTimeoutMs)) {
      set_error(error, "image upload write failed before response");
    client->stop();
    return false;
  }

  String status_line = client->readStringUntil('\n');
  status_line.trim();
  if (status_line.length() == 0) {
    set_error(error, "image upload timed out waiting for response");
    client->stop();
    return false;
  }

  int status_code = 0;
  int first_space = status_line.indexOf(' ');
  if (first_space >= 0) {
    int second_space = status_line.indexOf(' ', first_space + 1);
    String code = second_space > first_space ? status_line.substring(first_space + 1, second_space)
                                             : status_line.substring(first_space + 1);
    status_code = code.toInt();
  }
  if (http_status_code != nullptr) {
    *http_status_code = status_code;
  }
  if (status_code >= 200 && status_code < 300) {
    client->stop();
    return true;
  }

  bool headers_done = false;
  while (client->connected() && client->available()) {
    String line = client->readStringUntil('\n');
    if (line == "\r" || line.length() == 1) {
      headers_done = true;
      break;
    }
  }

  String response_body;
  if (headers_done) {
    response_body = client->readString();
  }
  client->stop();

  set_error(error, "image upload failed with HTTP " + String(status_code) + ": " + response_body);
  return false;
}

bool PlatformClient::register_device_node(
    const char* hardware_device_id,
    const char* node_role,
    const char* display_name,
    const char* hardware_model,
    const char* hardware_version,
    const char* software_version,
    const char* capabilities_json,
    String* error) {
  if (hardware_device_id == nullptr || String(hardware_device_id).length() == 0) {
    set_error(error, "device node registration skipped: missing hardware id");
    return false;
  }
  if (node_role == nullptr || String(node_role).length() == 0) {
    set_error(error, "device node registration skipped: missing node role");
    return false;
  }

  StaticJsonDocument<768> doc;
  doc["device_id"] = device_id_;
  doc["hardware_device_id"] = hardware_device_id;
  doc["node_role"] = node_role;
  if (display_name != nullptr && String(display_name).length() > 0) {
    doc["display_name"] = display_name;
  }
  if (hardware_model != nullptr && String(hardware_model).length() > 0) {
    doc["hardware_model"] = hardware_model;
  }
  if (hardware_version != nullptr && String(hardware_version).length() > 0) {
    doc["hardware_version"] = hardware_version;
  }
  if (software_version != nullptr && String(software_version).length() > 0) {
    doc["software_version"] = software_version;
  }
  if (capabilities_json != nullptr && String(capabilities_json).length() > 0) {
    StaticJsonDocument<256> capabilities_doc;
    DeserializationError capabilities_error = deserializeJson(capabilities_doc, capabilities_json);
    if (capabilities_error) {
      set_error(error, "device node registration capabilities JSON parse failed");
      return false;
    }
    doc["capabilities"] = capabilities_doc.as<JsonObject>();
  }
  doc["status"] = "online";

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/device-nodes/register", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "device node registration failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::fetch_ota_manifest(
    const char* hardware_device_id,
    const char* node_role,
    const char* current_version,
    String* response_body,
    String* error) {
  String path = "/api/hardware/ota/manifest?hardware_device_id=" +
      url_encode(String(hardware_device_id == nullptr ? "" : hardware_device_id)) +
      "&node_role=" + url_encode(String(node_role == nullptr ? "" : node_role));
  if (current_version != nullptr && String(current_version).length() > 0) {
    path += "&current_version=" + url_encode(String(current_version));
  }

  int status_code = 0;
  String body;
  if (!json_get(path, &status_code, &body)) {
    set_error(error, body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "OTA manifest failed with HTTP " + String(status_code) + ": " + body);
    return false;
  }
  if (response_body != nullptr) {
    *response_body = body;
  }
  return true;
}

bool PlatformClient::report_ota_status(
    const char* hardware_device_id,
    const char* status,
    const char* release_id,
    const char* target_version,
    const char* installed_version,
    int progress,
    const char* error_message,
    String* error) {
  StaticJsonDocument<512> doc;
  doc["hardware_device_id"] = hardware_device_id == nullptr ? "" : hardware_device_id;
  doc["status"] = status == nullptr ? "failed" : status;
  if (release_id != nullptr && String(release_id).length() > 0) {
    doc["release_id"] = release_id;
  }
  if (target_version != nullptr && String(target_version).length() > 0) {
    doc["target_version"] = target_version;
  }
  if (installed_version != nullptr && String(installed_version).length() > 0) {
    doc["installed_version"] = installed_version;
  }
  if (progress >= 0) {
    doc["progress"] = progress;
  }
  if (error_message != nullptr && String(error_message).length() > 0) {
    doc["error"] = error_message;
  }

  String body;
  serializeJson(doc, body);

  int status_code = 0;
  String response_body;
  if (!json_post("/api/hardware/ota/status", body, &status_code, &response_body)) {
    set_error(error, response_body);
    return false;
  }
  if (status_code < 200 || status_code >= 300) {
    set_error(error, "OTA status failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
}

bool PlatformClient::download_ota_artifact(
    const String& artifact_path,
    OtaChunkCallback callback,
    void* callback_context,
    String* error) {
  if (!artifact_path.startsWith("/api/hardware/ota/artifacts/")) {
    set_error(error, "OTA artifact path rejected");
    return false;
  }
  if (callback == nullptr) {
    set_error(error, "OTA callback missing");
    return false;
  }

  HTTPClient http;
  http.setTimeout(kOtaDownloadTimeoutMs);
  if (!http.begin(join_url(artifact_path))) {
    set_error(error, "OTA artifact request setup failed");
    return false;
  }
  http.addHeader(kDeviceTokenHeader, auth_header_value());
  const int status_code = http.GET();
  if (status_code < 200 || status_code >= 300) {
    const String body = status_code > 0 ? http.getString() : http.errorToString(status_code);
    http.end();
    set_error(error, "OTA artifact failed with HTTP " + String(status_code) + ": " + body);
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();
  uint8_t buffer[kImageUploadChunkSize];
  int remaining = http.getSize();
  uint32_t last_progress_at = millis();
  while (http.connected() && (remaining > 0 || remaining == -1)) {
    const size_t available = stream->available();
    if (available == 0) {
      if (millis() - last_progress_at >= kOtaDownloadTimeoutMs) {
        http.end();
        set_error(error, "OTA artifact download timed out");
        return false;
      }
      delay(10);
      continue;
    }
    const size_t read_size = available > sizeof(buffer) ? sizeof(buffer) : available;
    const int read = stream->readBytes(buffer, read_size);
    if (read <= 0) {
      continue;
    }
    if (!callback(buffer, static_cast<size_t>(read), callback_context)) {
      http.end();
      set_error(error, "OTA artifact write failed");
      return false;
    }
    if (remaining > 0) {
      remaining -= read;
    }
    last_progress_at = millis();
  }
  http.end();
  return remaining <= 0;
}

bool PlatformClient::json_post(
    const String& path,
    const String& json_body,
    int* status_code,
    String* response_body) {
  HTTPClient http;
  http.setTimeout(kHttpTimeoutMs);
  if (!http.begin(join_url(path))) {
    if (response_body != nullptr) {
      *response_body = "request setup failed";
    }
    return false;
  }
  http.addHeader("Content-Type", kJsonContentType);
  http.addHeader(kDeviceTokenHeader, auth_header_value());
  int code = http.POST(json_body);
  if (status_code != nullptr) {
    *status_code = code;
  }
  if (response_body != nullptr) {
    *response_body = code > 0 ? http.getString() : http.errorToString(code);
  }
  http.end();
  return code > 0;
}

bool PlatformClient::json_get(const String& path, int* status_code, String* response_body) {
  HTTPClient http;
  http.setTimeout(kHttpTimeoutMs);
  if (!http.begin(join_url(path))) {
    if (response_body != nullptr) {
      *response_body = "request setup failed";
    }
    return false;
  }
  http.addHeader(kDeviceTokenHeader, auth_header_value());
  int code = http.GET();
  if (status_code != nullptr) {
    *status_code = code;
  }
  if (response_body != nullptr) {
    *response_body = code > 0 ? http.getString() : http.errorToString(code);
  }
  http.end();
  return code > 0;
}

bool PlatformClient::parse_url(String* host, uint16_t* port, String* path, bool* secure) const {
  if (!configured()) {
    return false;
  }

  String url = base_url_;
  bool is_secure = false;
  if (url.startsWith("https://")) {
    is_secure = true;
    url.remove(0, 8);
  } else if (url.startsWith("http://")) {
    url.remove(0, 7);
  } else {
    return false;
  }

  String host_port = url;
  String url_path = "";
  int slash = url.indexOf('/');
  if (slash >= 0) {
    host_port = url.substring(0, slash);
    url_path = url.substring(slash);
  }
  if (url_path.length() == 0) {
    url_path = "";
  }

  uint16_t resolved_port = is_secure ? 443 : 80;
  int colon = host_port.indexOf(':');
  if (colon >= 0) {
    resolved_port = static_cast<uint16_t>(host_port.substring(colon + 1).toInt());
    host_port = host_port.substring(0, colon);
  }

  if (host_port.length() == 0) {
    return false;
  }

  *host = host_port;
  *port = resolved_port;
  *path = url_path;
  *secure = is_secure;
  return true;
}

String PlatformClient::auth_header_value() const {
  return device_token_;
}

String PlatformClient::join_url(const String& path) const {
  if (path.startsWith("/")) {
    return base_url_ + path;
  }
  return base_url_ + "/" + path;
}

String PlatformClient::url_encode(const String& value) const {
  String encoded;
  const char* hex = "0123456789ABCDEF";
  for (size_t i = 0; i < value.length(); ++i) {
    const char c = value.charAt(i);
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
        c == '-' || c == '_' || c == '.' || c == '~') {
      encoded += c;
    } else {
      encoded += '%';
      encoded += hex[(static_cast<uint8_t>(c) >> 4) & 0x0F];
      encoded += hex[static_cast<uint8_t>(c) & 0x0F];
    }
  }
  return encoded;
}

void PlatformClient::set_error(String* error, const String& message) const {
  if (error != nullptr) {
    *error = message;
  }
}
