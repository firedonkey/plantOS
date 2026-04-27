#include <Arduino.h>
#include <SD.h>
#include <SPI.h>

#include "camera/xiao_camera.h"

namespace {
XiaoCamera g_camera;
unsigned int g_capture_index = 0;
String g_command_buffer;

// XIAO ESP32-S3 Sense microSD slot (SPI)
constexpr int kSdChipSelectPin = 21;
}

bool init_sd_card() {
  SPI.begin(SCK, MISO, MOSI, kSdChipSelectPin);
  if (!SD.begin(kSdChipSelectPin, SPI)) {
    Serial.println("[camera-test] SD init failed");
    return false;
  }

  const uint64_t card_size_mb = SD.cardSize() / (1024ULL * 1024ULL);
  Serial.printf("[camera-test] SD initialized, size: %llu MB\n", card_size_mb);
  return true;
}

void print_help() {
  Serial.println("[camera-test] commands:");
  Serial.println("  c                 capture and save (no Enter)");
  Serial.println("  l                 list files on SD (no Enter)");
  Serial.println("  d <path>          dump file hex to serial (press Enter)");
  Serial.println("  h                 show this help (no Enter)");
}

void list_sd_files() {
  File root = SD.open("/");
  if (!root || !root.isDirectory()) {
    Serial.println("[camera-test] cannot open SD root");
    return;
  }

  Serial.println("[camera-test] SD file list begin");
  File entry = root.openNextFile();
  while (entry) {
    Serial.printf("[camera-test] %s (%u bytes)\n", entry.name(), static_cast<unsigned int>(entry.size()));
    entry.close();
    entry = root.openNextFile();
  }
  Serial.println("[camera-test] SD file list end");
}

void dump_file_hex(const String& path) {
  File file = SD.open(path.c_str(), FILE_READ);
  if (!file || file.isDirectory()) {
    Serial.printf("[camera-test] dump failed: %s\n", path.c_str());
    return;
  }

  Serial.printf("[camera-test] DUMP_BEGIN %s %u\n", path.c_str(), static_cast<unsigned int>(file.size()));
  constexpr size_t kChunkBytes = 32;
  uint8_t buffer[kChunkBytes];

  while (true) {
    const int bytes_read = file.read(buffer, kChunkBytes);
    if (bytes_read <= 0) {
      break;
    }
    for (int i = 0; i < bytes_read; ++i) {
      Serial.printf("%02X", buffer[i]);
    }
    Serial.println();
  }

  file.close();
  Serial.printf("[camera-test] DUMP_END %s\n", path.c_str());
}

void capture_and_save() {
  const String path = "/capture_" + String(g_capture_index++) + ".jpg";
  CameraFrameInfo frame{};
  if (!g_camera.capture_to_file(SD, path.c_str(), &frame)) {
    Serial.println("[camera-test] capture/save failed");
    return;
  }

  Serial.printf(
      "[camera-test] saved %s (%ux%u, %u bytes)\n",
      path.c_str(),
      frame.width,
      frame.height,
      static_cast<unsigned int>(frame.length_bytes));
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println();
  Serial.println("=== PlantLab Camera Test Firmware ===");
  Serial.println("[camera-test] board: Seeed XIAO ESP32-S3 Sense");
  Serial.println("[camera-test] manual mode: [space] or c = capture and save now");

  if (!g_camera.begin()) {
    Serial.println("[camera-test] camera init failed. Check camera module and pin map.");
    return;
  }
  if (!init_sd_card()) {
    Serial.println("[camera-test] SD card unavailable. Insert card and reboot.");
    return;
  }

  Serial.println("[camera-test] camera + SD initialized");
  print_help();
}

void handle_serial_commands() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == '\r') {
      continue;
    }

    if (ch == '\n') {
      const String cmd = g_command_buffer;
      g_command_buffer = "";
      if (cmd.length() == 0) {
        continue;
      }

      if (cmd == "c" || cmd == "C" || cmd == " ") {
        capture_and_save();
      } else if (cmd == "l" || cmd == "L") {
        list_sd_files();
      } else if (cmd == "h" || cmd == "H" || cmd == "help") {
        print_help();
      } else if (cmd.startsWith("d ")) {
        const String path = cmd.substring(2);
        dump_file_hex(path);
      } else {
        Serial.printf("[camera-test] unknown command: %s\n", cmd.c_str());
      }
      continue;
    }

    if (ch == ' ' && g_command_buffer.length() == 0) {
      capture_and_save();
      continue;
    }
    if ((ch == 'c' || ch == 'C') && g_command_buffer.length() == 0) {
      capture_and_save();
      continue;
    }
    if ((ch == 'l' || ch == 'L') && g_command_buffer.length() == 0) {
      list_sd_files();
      continue;
    }
    if ((ch == 'h' || ch == 'H') && g_command_buffer.length() == 0) {
      print_help();
      continue;
    }

    g_command_buffer += ch;
  }
}

void loop() {
  handle_serial_commands();
}
