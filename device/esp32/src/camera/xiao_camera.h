#pragma once

#include <FS.h>
#include <esp_camera.h>
#include <stddef.h>
#include <stdint.h>

struct CameraFrameInfo {
  size_t length_bytes;
  size_t width;
  size_t height;
  bool valid;
};

struct XiaoCameraOptions {
  framesize_t frame_size = FRAMESIZE_UXGA;
  pixformat_t pixel_format = PIXFORMAT_JPEG;
  int jpeg_quality = 12;
  int fb_count = 2;
  camera_grab_mode_t grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  uint16_t expected_sensor_pid = 0;
  bool require_psram = true;
  bool autofocus_enabled = false;
  bool autofocus_required = false;
  bool continuous_autofocus = false;
  uint16_t autofocus_timeout_ms = 2500;
  uint16_t autofocus_settle_ms = 250;
  uint8_t warmup_frames = 4;
  uint16_t warmup_delay_ms = 120;
};

inline XiaoCameraOptions makeDefaultXiaoCameraOptions() {
  XiaoCameraOptions options{};
#if defined(PLANTLAB_CAMERA_EXPECTED_SENSOR_PID)
  options.expected_sensor_pid = PLANTLAB_CAMERA_EXPECTED_SENSOR_PID;
#endif
#if defined(PLANTLAB_OV5640_AF_ENABLED)
  options.autofocus_enabled = true;
#endif
  return options;
}

class XiaoCamera {
 public:
  bool begin(const XiaoCameraOptions& options = XiaoCameraOptions{});
  bool warmup();
  CameraFrameInfo capture_once();
  bool capture_to_file(fs::FS& filesystem, const char* path, CameraFrameInfo* out_info = nullptr);

 private:
  XiaoCameraOptions options_{};
};
