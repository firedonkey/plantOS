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
  uint8_t warmup_frames = 4;
  uint16_t warmup_delay_ms = 120;
};

class XiaoCamera {
 public:
  bool begin(const XiaoCameraOptions& options = XiaoCameraOptions{});
  bool warmup();
  CameraFrameInfo capture_once();
  bool capture_to_file(fs::FS& filesystem, const char* path, CameraFrameInfo* out_info = nullptr);

 private:
  XiaoCameraOptions options_{};
};
