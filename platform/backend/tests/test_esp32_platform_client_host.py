import shutil
import subprocess
from pathlib import Path


def test_esp32_platform_client_heartbeat_includes_software_version(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_platform_client_heartbeat.cpp"
    client_src = repo_root / "device/esp32/src/platform/platform_client.cpp"
    contract_client_src = repo_root / "device/esp32/src/contracts/contract_client.cpp"
    command_dispatcher_src = repo_root / "device/esp32/src/contracts/command_dispatcher.cpp"
    envelope_builder_src = repo_root / "device/esp32/src/contracts/envelope_builder.cpp"
    envelope_parser_src = repo_root / "device/esp32/src/contracts/envelope_parser.cpp"
    ota_status_reporter_src = repo_root / "device/esp32/src/contracts/ota_status_reporter.cpp"
    time_sync_manager_src = repo_root / "device/esp32/src/time/time_sync_manager.cpp"
    arduino_json = (
        repo_root
        / "device/esp32/.pio/libdeps/esp32-s3-devkitc-1/ArduinoJson/src"
    )

    (tmp_path / "Arduino.h").write_text(
        r'''
#pragma once
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>

class String {
 public:
  String() = default;
  String(const char* input) : value_(input == nullptr ? "" : input) {}
  String(const std::string& input) : value_(input) {}
  String(char input) : value_(1, input) {}
  String(int input) : value_(std::to_string(input)) {}
  String(unsigned int input) : value_(std::to_string(input)) {}
  String(long input) : value_(std::to_string(input)) {}
  String(unsigned long input) : value_(std::to_string(input)) {}

  std::size_t length() const { return value_.size(); }
  const char* c_str() const { return value_.c_str(); }
  char charAt(std::size_t index) const { return value_.at(index); }
  bool startsWith(const char* prefix) const { return value_.rfind(prefix == nullptr ? "" : prefix, 0) == 0; }
  bool endsWith(const char* suffix) const {
    const std::string needle = suffix == nullptr ? "" : suffix;
    return value_.size() >= needle.size() && value_.compare(value_.size() - needle.size(), needle.size(), needle) == 0;
  }
  void trim() {
    const auto first = value_.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
      value_.clear();
      return;
    }
    const auto last = value_.find_last_not_of(" \t\r\n");
    value_ = value_.substr(first, last - first + 1);
  }
  void remove(std::size_t index) {
    if (index < value_.size()) {
      value_.erase(index);
    }
  }
  void remove(std::size_t index, std::size_t count) {
    if (index < value_.size()) {
      value_.erase(index, count);
    }
  }
  int indexOf(char needle) const {
    const auto pos = value_.find(needle);
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
  }
  int indexOf(const char* needle) const {
    const auto pos = value_.find(needle == nullptr ? "" : needle);
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
  }
  int indexOf(char needle, std::size_t from) const {
    const auto pos = value_.find(needle, from);
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
  }
  int indexOf(const char* needle, std::size_t from) const {
    const auto pos = value_.find(needle == nullptr ? "" : needle, from);
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
  }
  String substring(std::size_t start) const {
    return start >= value_.size() ? String("") : String(value_.substr(start));
  }
  String substring(std::size_t start, std::size_t end) const {
    if (start >= value_.size() || end <= start) {
      return String("");
    }
    return String(value_.substr(start, end - start));
  }
  int toInt() const { return std::atoi(value_.c_str()); }
  std::size_t write(uint8_t c) {
    value_ += static_cast<char>(c);
    return 1;
  }
  std::size_t write(const uint8_t* bytes, std::size_t length) {
    value_.append(reinterpret_cast<const char*>(bytes), length);
    return length;
  }
  int read() const {
    if (read_index_ >= value_.size()) {
      return -1;
    }
    return static_cast<unsigned char>(value_[read_index_++]);
  }
  void toLowerCase() {
    std::transform(value_.begin(), value_.end(), value_.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  }

  String& operator=(const char* input) {
    value_ = input == nullptr ? "" : input;
    return *this;
  }
  String& operator+=(const char* input) {
    value_ += input == nullptr ? "" : input;
    return *this;
  }
  String& operator+=(const String& input) {
    value_ += input.value_;
    return *this;
  }
  String& operator+=(char input) {
    value_ += input;
    return *this;
  }
  bool operator==(const char* rhs) const { return value_ == (rhs == nullptr ? "" : rhs); }
  bool operator!=(const char* rhs) const { return !(*this == rhs); }
  friend bool operator==(const String& lhs, const String& rhs) { return lhs.value_ == rhs.value_; }
  friend bool operator!=(const String& lhs, const String& rhs) { return !(lhs == rhs); }
  friend String operator+(const String& lhs, const String& rhs) { return String(lhs.value_ + rhs.value_); }
  friend String operator+(const String& lhs, const char* rhs) { return String(lhs.value_ + (rhs == nullptr ? "" : rhs)); }
  friend String operator+(const char* lhs, const String& rhs) { return String(std::string(lhs == nullptr ? "" : lhs) + rhs.value_); }
  operator const char*() const { return value_.c_str(); }

 private:
  std::string value_;
  mutable std::size_t read_index_ = 0;
};

inline uint32_t millis() { return 0; }
inline void delay(unsigned long) {}
''',
        encoding="utf-8",
    )
    (tmp_path / "WiFiClient.h").write_text(
        r'''
#pragma once
#include <cstddef>
#include <cstdint>
#include "Arduino.h"

class Client {
 public:
  virtual ~Client() = default;
  virtual bool connect(const char*, uint16_t) { return true; }
  virtual void setTimeout(uint32_t) {}
  virtual bool connected() { return false; }
  virtual std::size_t write(const uint8_t*, std::size_t length) { return length; }
  virtual void stop() {}
  virtual String readStringUntil(char) { return ""; }
  virtual int available() { return 0; }
  virtual String readString() { return ""; }
  virtual int readBytes(uint8_t*, std::size_t) { return 0; }
};

class WiFiClient : public Client {};
''',
        encoding="utf-8",
    )
    (tmp_path / "WiFiClientSecure.h").write_text(
        r'''
#pragma once
#include "WiFiClient.h"

class WiFiClientSecure : public WiFiClient {
 public:
  void setInsecure() {}
};
''',
        encoding="utf-8",
    )
    (tmp_path / "WiFi.h").write_text("#pragma once\n", encoding="utf-8")
    (tmp_path / "HTTPClient.h").write_text(
        r'''
#pragma once
#include <string>
#include <vector>
#include "Arduino.h"
#include "WiFiClient.h"

namespace platform_client_host_test {
inline std::string last_url;
inline std::string last_post_body;
inline std::string next_response_body = "{}";
inline int next_get_status = 200;
inline int next_post_status = 200;
inline std::vector<std::pair<std::string, std::string>> headers;

inline void reset_http_capture() {
  last_url.clear();
  last_post_body.clear();
  next_response_body = "{}";
  next_get_status = 200;
  next_post_status = 200;
  headers.clear();
}
}

class HTTPClient {
 public:
  void setTimeout(uint32_t) {}
  bool begin(const String& url) {
    platform_client_host_test::last_url = url.c_str();
    return true;
  }
  void addHeader(const char* key, const String& value) {
    platform_client_host_test::headers.emplace_back(key == nullptr ? "" : key, value.c_str());
  }
  int POST(const String& body) {
    platform_client_host_test::last_post_body = body.c_str();
    return platform_client_host_test::next_post_status;
  }
  int GET() { return platform_client_host_test::next_get_status; }
  String getString() const { return String(platform_client_host_test::next_response_body); }
  String errorToString(int code) const { return String(code); }
  void end() {}
  WiFiClient* getStreamPtr() { return &stream_; }
  bool connected() const { return false; }
  int getSize() const { return 0; }

 private:
  WiFiClient stream_;
};
''',
        encoding="utf-8",
    )

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert client_src.exists(), f"missing PlatformClient source: {client_src}"
    assert (arduino_json / "ArduinoJson.h").exists(), (
        "missing ArduinoJson dependency; run "
        "`cd device/esp32 && pio run -e esp32-s3-devkitc-1` first"
    )

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 PlatformClient host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    output_binary = tmp_path / "test_platform_client_heartbeat"
    compile_cmd = [
        clang,
        "-std=c++17",
        "-isysroot",
        sdk_path,
        "-I",
        f"{sdk_path}/usr/include/c++/v1",
        "-I",
        str(tmp_path),
        "-I",
        str(repo_root / "device/esp32/src"),
        "-I",
        str(repo_root / "device/esp32/include"),
        "-I",
        str(arduino_json),
        str(test_src),
        str(client_src),
        str(contract_client_src),
        str(command_dispatcher_src),
        str(envelope_builder_src),
        str(envelope_parser_src),
        str(ota_status_reporter_src),
        str(time_sync_manager_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)
