#include "platform/platform_client.h"

#include <memory>

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

namespace {
constexpr uint32_t kHttpTimeoutMs = 10000;
constexpr char kDeviceTokenHeader[] = "X-Device-Token";
constexpr char kJsonContentType[] = "application/json";
constexpr char kMultipartContentType[] = "multipart/form-data; boundary=";
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
  StaticJsonDocument<384> doc;
  doc["device_id"] = device_id_;
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

bool PlatformClient::send_status(const PlatformStatus& status, String* error) {
  StaticJsonDocument<192> doc;
  doc["light_on"] = status.light_on;
  doc["pump_on"] = status.pump_on;
  doc["message"] = status.message;

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

bool PlatformClient::upload_jpeg(
    const uint8_t* bytes,
    size_t length,
    const char* filename,
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
      String(device_id_) + "\r\n"
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

  client->print("POST " + request_path + " HTTP/1.1\r\n");
  client->print("Host: " + host + "\r\n");
  client->print(String(kDeviceTokenHeader) + ": " + auth_header_value() + "\r\n");
  client->print("Connection: close\r\n");
  client->print("Content-Type: " + String(kMultipartContentType) + boundary + "\r\n");
  client->print("Content-Length: " + String(content_length) + "\r\n\r\n");
  client->print(prefix);
  client->write(bytes, length);
  client->print(suffix);

  uint32_t started_at = millis();
  while (client->connected() && !client->available() && millis() - started_at < kHttpTimeoutMs) {
    delay(10);
  }
  if (!client->available()) {
    set_error(error, "image upload timed out waiting for response");
    client->stop();
    return false;
  }

  String status_line = client->readStringUntil('\n');
  status_line.trim();
  int status_code = 0;
  int first_space = status_line.indexOf(' ');
  if (first_space >= 0) {
    int second_space = status_line.indexOf(' ', first_space + 1);
    String code = second_space > first_space ? status_line.substring(first_space + 1, second_space)
                                             : status_line.substring(first_space + 1);
    status_code = code.toInt();
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

  if (status_code < 200 || status_code >= 300) {
    set_error(error, "image upload failed with HTTP " + String(status_code) + ": " + response_body);
    return false;
  }
  return true;
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

void PlatformClient::set_error(String* error, const String& message) const {
  if (error != nullptr) {
    *error = message;
  }
}
