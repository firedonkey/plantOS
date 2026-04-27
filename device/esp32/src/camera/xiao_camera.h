#pragma once

#include <FS.h>
#include <stddef.h>
#include <stdint.h>

struct CameraFrameInfo {
  size_t length_bytes;
  size_t width;
  size_t height;
  bool valid;
};

class XiaoCamera {
 public:
  bool begin();
  CameraFrameInfo capture_once();
  bool capture_to_file(fs::FS& filesystem, const char* path, CameraFrameInfo* out_info = nullptr);
};
