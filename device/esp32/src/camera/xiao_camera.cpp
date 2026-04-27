#include "camera/xiao_camera.h"

#include <Arduino.h>
#include <esp_camera.h>

namespace {
// Seeed XIAO ESP32-S3 Sense OV2640 pin mapping
// If your board revision differs, update these values.
constexpr int kPwdnGpio = -1;
constexpr int kResetGpio = -1;
constexpr int kXclkGpio = 10;
constexpr int kSiodGpio = 40;
constexpr int kSiocGpio = 39;

constexpr int kY9Gpio = 48;
constexpr int kY8Gpio = 11;
constexpr int kY7Gpio = 12;
constexpr int kY6Gpio = 14;
constexpr int kY5Gpio = 16;
constexpr int kY4Gpio = 18;
constexpr int kY3Gpio = 17;
constexpr int kY2Gpio = 15;
constexpr int kVsyncGpio = 38;
constexpr int kHrefGpio = 47;
constexpr int kPclkGpio = 13;
}  // namespace

bool XiaoCamera::begin() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = kY2Gpio;
  config.pin_d1 = kY3Gpio;
  config.pin_d2 = kY4Gpio;
  config.pin_d3 = kY5Gpio;
  config.pin_d4 = kY6Gpio;
  config.pin_d5 = kY7Gpio;
  config.pin_d6 = kY8Gpio;
  config.pin_d7 = kY9Gpio;
  config.pin_xclk = kXclkGpio;
  config.pin_pclk = kPclkGpio;
  config.pin_vsync = kVsyncGpio;
  config.pin_href = kHrefGpio;
  config.pin_sccb_sda = kSiodGpio;
  config.pin_sccb_scl = kSiocGpio;
  config.pin_pwdn = kPwdnGpio;
  config.pin_reset = kResetGpio;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 2;
  config.frame_size = FRAMESIZE_VGA;

  const esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[camera] init failed: 0x%x\n", static_cast<unsigned int>(err));
    return false;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_brightness(sensor, 0);
    sensor->set_saturation(sensor, 0);
  }

  return true;
}

CameraFrameInfo XiaoCamera::capture_once() {
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    return CameraFrameInfo{0, 0, 0, false};
  }

  const CameraFrameInfo info{
      frame->len,
      frame->width,
      frame->height,
      true,
  };

  esp_camera_fb_return(frame);
  return info;
}

bool XiaoCamera::capture_to_file(fs::FS& filesystem, const char* path, CameraFrameInfo* out_info) {
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    return false;
  }

  const CameraFrameInfo info{
      frame->len,
      frame->width,
      frame->height,
      true,
  };

  File file = filesystem.open(path, FILE_WRITE);
  if (!file) {
    esp_camera_fb_return(frame);
    return false;
  }

  const size_t bytes_written = file.write(frame->buf, frame->len);
  file.close();
  esp_camera_fb_return(frame);

  if (bytes_written != info.length_bytes) {
    return false;
  }

  if (out_info != nullptr) {
    *out_info = info;
  }
  return true;
}
