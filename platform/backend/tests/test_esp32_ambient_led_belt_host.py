import shutil
import subprocess
from pathlib import Path


def test_esp32_ambient_led_belt_controller_host(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_ambient_led_belt_controller.cpp"
    controller_src = repo_root / "device/esp32/src/ambient_led_belt/ambient_led_belt_controller.cpp"
    arduino_json_candidates = [
        repo_root / "device/esp32/.pio/libdeps/esp32-local/ArduinoJson/src",
        repo_root / "device/esp32/.pio/libdeps/esp32-gcp/ArduinoJson/src",
        repo_root / "device/esp32/.pio/libdeps/esp32-s3-devkitc-1/ArduinoJson/src",
    ]
    arduino_json = next((path for path in arduino_json_candidates if (path / "ArduinoJson.h").exists()), None)

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
  void trim() {
    const auto first = value_.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
      value_.clear();
      return;
    }
    const auto last = value_.find_last_not_of(" \t\r\n");
    value_ = value_.substr(first, last - first + 1);
  }
  void toLowerCase() {
    std::transform(value_.begin(), value_.end(), value_.begin(), [](unsigned char c) {
      return static_cast<char>(std::tolower(c));
    });
  }
  int indexOf(const char* needle) const {
    const auto pos = value_.find(needle == nullptr ? "" : needle);
    return pos == std::string::npos ? -1 : static_cast<int>(pos);
  }
  int read() const {
    if (read_index_ >= value_.size()) {
      return -1;
    }
    return static_cast<unsigned char>(value_[read_index_++]);
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
  bool operator==(const char* rhs) const { return value_ == (rhs == nullptr ? "" : rhs); }
  bool operator!=(const char* rhs) const { return !(*this == rhs); }
  friend bool operator==(const String& lhs, const String& rhs) { return lhs.value_ == rhs.value_; }
  friend bool operator!=(const String& lhs, const String& rhs) { return !(lhs == rhs); }
  operator const char*() const { return value_.c_str(); }

 private:
  std::string value_;
  mutable std::size_t read_index_ = 0;
};

class SerialClass {
 public:
  template <typename... Args>
  void printf(const char*, Args...) {}
  void println(const char*) {}
};

inline SerialClass Serial;
''',
        encoding="utf-8",
    )

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert controller_src.exists(), f"missing ambient LED belt controller source: {controller_src}"
    assert arduino_json is not None, (
        "missing ArduinoJson dependency; run "
        "`cd device/esp32 && pio run -e esp32-local` first"
    )

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 ambient LED belt host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    output_binary = tmp_path / "test_ambient_led_belt_controller"
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
        str(controller_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)
