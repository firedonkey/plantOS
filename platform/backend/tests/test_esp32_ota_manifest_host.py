import shutil
import subprocess
from pathlib import Path


def test_esp32_ota_manifest_host_test(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_ota_manifest.cpp"
    manifest_src = repo_root / "device/esp32/src/ota/firmware_manifest.cpp"
    arduino_json = (
        repo_root
        / "device/esp32/.pio/libdeps/esp32-s3-devkitc-1/ArduinoJson/src"
    )
    arduino_stub = tmp_path / "Arduino.h"
    arduino_stub.write_text(
        """
#pragma once
#include <algorithm>
#include <cstddef>
#include <cctype>
#include <string>

class String {
 public:
  String() = default;
  String(const char* input) : value_(input == nullptr ? "" : input) {}
  String(const std::string& input) : value_(input) {}

  std::size_t length() const { return value_.size(); }
  char charAt(std::size_t index) const { return value_.at(index); }
  bool startsWith(const char* prefix) const { return value_.rfind(prefix == nullptr ? "" : prefix, 0) == 0; }
  int read() const {
    if (read_index_ >= value_.size()) {
      return -1;
    }
    return static_cast<unsigned char>(value_[read_index_++]);
  }
  void toLowerCase() {
    std::transform(value_.begin(), value_.end(), value_.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  }
  const char* c_str() const { return value_.c_str(); }

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
  operator const char*() const { return value_.c_str(); }

  bool operator==(const char* rhs) const { return value_ == (rhs == nullptr ? "" : rhs); }
  bool operator!=(const char* rhs) const { return !(*this == rhs); }
  friend bool operator==(const String& lhs, const String& rhs) { return lhs.value_ == rhs.value_; }
  friend bool operator!=(const String& lhs, const String& rhs) { return !(lhs == rhs); }

 private:
  std::string value_;
  mutable std::size_t read_index_ = 0;
};
""",
        encoding="utf-8",
    )

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert manifest_src.exists(), f"missing manifest source: {manifest_src}"
    assert (arduino_json / "ArduinoJson.h").exists(), (
        "missing ArduinoJson dependency; run "
        "`cd device/esp32 && pio run -e esp32-s3-devkitc-1` first"
    )

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 OTA manifest host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    output_binary = tmp_path / "test_ota_manifest"
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
        str(arduino_json),
        str(test_src),
        str(manifest_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)
