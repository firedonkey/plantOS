#include "camera/xiao_camera.h"

#include <Arduino.h>
#include <esp_camera.h>

#if defined(PLANTLAB_OV5640_AF_ENABLED)
#include <ESP32_OV5640_AF.h>
#endif

namespace {
// Seeed XIAO ESP32-S3 Sense camera pin mapping
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

const char* sensor_name(uint16_t pid) {
  switch (pid) {
    case OV2640_PID:
      return "OV2640";
    case OV3660_PID:
      return "OV3660";
    case OV5640_PID:
      return "OV5640";
    default:
      return "unknown";
  }
}

void apply_common_sensor_settings(sensor_t* sensor, int jpeg_quality) {
  sensor->set_quality(sensor, jpeg_quality);
  sensor->set_whitebal(sensor, 1);
  sensor->set_awb_gain(sensor, 1);
  sensor->set_wb_mode(sensor, 0);
  sensor->set_gain_ctrl(sensor, 1);
  sensor->set_exposure_ctrl(sensor, 1);
  sensor->set_aec2(sensor, 1);
  sensor->set_ae_level(sensor, 2);
  sensor->set_dcw(sensor, 1);
  sensor->set_bpc(sensor, 1);
  sensor->set_wpc(sensor, 1);
  sensor->set_raw_gma(sensor, 1);
  sensor->set_lenc(sensor, 1);
  sensor->set_brightness(sensor, 1);
  sensor->set_contrast(sensor, 1);
  sensor->set_saturation(sensor, 0);
}

void apply_ov5640_sensor_settings(sensor_t* sensor) {
  sensor->set_gainceiling(sensor, GAINCEILING_8X);
  sensor->set_denoise(sensor, 1);
  sensor->set_sharpness(sensor, 1);
}

#if defined(PLANTLAB_OV5640_AF_ENABLED)
bool wait_ov5640_af_ack(sensor_t* sensor, const char* label) {
  for (uint16_t retry = 0; retry < 1000; ++retry) {
    const int ack = sensor->get_reg(sensor, OV5640_CMD_ACK, 0xff);
    if (ack < 0) {
      Serial.printf("[camera] OV5640 autofocus %s ack read failed rc=%d\n", label, ack);
      return false;
    }
    if (ack == 0x00) {
      return true;
    }
    delay(5);
  }

  Serial.printf("[camera] OV5640 autofocus %s ack timed out\n", label);
  return false;
}

bool send_ov5640_af_command(sensor_t* sensor, uint8_t command, const char* label) {
  int rc = sensor->set_reg(sensor, OV5640_CMD_MAIN, 0xff, 0x01);
  if (rc < 0) {
    Serial.printf("[camera] OV5640 autofocus %s reset command failed rc=%d\n", label, rc);
    return false;
  }
  rc = sensor->set_reg(sensor, OV5640_CMD_MAIN, 0xff, 0x08);
  if (rc < 0) {
    Serial.printf("[camera] OV5640 autofocus %s release command failed rc=%d\n", label, rc);
    return false;
  }
  if (!wait_ov5640_af_ack(sensor, label)) {
    return false;
  }
  rc = sensor->set_reg(sensor, OV5640_CMD_ACK, 0xff, 0x01);
  if (rc < 0) {
    Serial.printf("[camera] OV5640 autofocus %s ack reset failed rc=%d\n", label, rc);
    return false;
  }
  rc = sensor->set_reg(sensor, OV5640_CMD_MAIN, 0xff, command);
  if (rc < 0) {
    Serial.printf("[camera] OV5640 autofocus %s command failed rc=%d\n", label, rc);
    return false;
  }
  return wait_ov5640_af_ack(sensor, label);
}

bool wait_ov5640_single_autofocus(sensor_t* sensor, uint16_t timeout_ms) {
  const unsigned long started_at = millis();
  int status = sensor->get_reg(sensor, OV5640_CMD_FW_STATUS, 0xff);
  while (millis() - started_at < timeout_ms) {
    status = sensor->get_reg(sensor, OV5640_CMD_FW_STATUS, 0xff);
    if (status < 0) {
      Serial.printf("[camera] OV5640 autofocus status read failed rc=%d\n", status);
      return false;
    }
    if (status == FW_STATUS_S_FOCUSED) {
      Serial.printf("[camera] OV5640 single autofocus focused fw_status=0x%02x\n", status);
      return true;
    }
    if (status == FW_STATUS_S_IDLE && millis() - started_at > 500) {
      Serial.printf("[camera] OV5640 single autofocus idle fw_status=0x%02x\n", status);
      return true;
    }
    delay(50);
  }

  Serial.printf("[camera] OV5640 single autofocus timed out fw_status=0x%02x\n", status);
  return false;
}
#endif

bool configure_ov5640_autofocus(sensor_t* sensor, const XiaoCameraOptions& options) {
  if (!options.autofocus_enabled) {
    return true;
  }

  if (sensor->id.PID != OV5640_PID) {
    Serial.println("[camera] OV5640 autofocus skipped: detected sensor is not OV5640");
    return !options.autofocus_required;
  }

#if defined(PLANTLAB_OV5640_AF_ENABLED)
  OV5640 ov5640;
  if (!ov5640.start(sensor)) {
    Serial.println("[camera] OV5640 autofocus start failed");
    return !options.autofocus_required;
  }

  const uint8_t init_result = ov5640.focusInit();
  if (init_result != 0) {
    Serial.printf("[camera] OV5640 autofocus firmware init failed rc=%u\n", static_cast<unsigned int>(init_result));
    return !options.autofocus_required;
  }

  if (options.continuous_autofocus) {
    const uint8_t mode_result = ov5640.autoFocusMode();
    if (mode_result != 0) {
      Serial.printf("[camera] OV5640 continuous autofocus mode failed rc=%u\n", static_cast<unsigned int>(mode_result));
      return !options.autofocus_required;
    }
    Serial.printf(
        "[camera] OV5640 continuous autofocus enabled fw_status=0x%02x\n",
        static_cast<unsigned int>(ov5640.getFWStatus()));
  } else {
    if (!send_ov5640_af_command(sensor, AF_TRIG_SINGLE_AUTO_FOCUS, "single")) {
      return !options.autofocus_required;
    }
    if (!wait_ov5640_single_autofocus(sensor, options.autofocus_timeout_ms)) {
      return !options.autofocus_required;
    }
  }

  if (options.autofocus_settle_ms > 0) {
    delay(options.autofocus_settle_ms);
  }

  return true;
#else
  Serial.println("[camera] OV5640 autofocus requested but firmware was built without PLANTLAB_OV5640_AF_ENABLED");
  return !options.autofocus_required;
#endif
}
}  // namespace

bool XiaoCamera::begin(const XiaoCameraOptions& options) {
  options_ = options;

  if (options.require_psram && !psramFound()) {
    Serial.println("[camera] PSRAM not found; XIAO high-resolution camera capture requires PSRAM");
    return false;
  }

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
  config.pixel_format = options.pixel_format;
  config.grab_mode = options.grab_mode;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = options.jpeg_quality;
  config.fb_count = options.fb_count;
  config.frame_size = options.frame_size;

  const esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[camera] init failed: 0x%x\n", static_cast<unsigned int>(err));
    return false;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor == nullptr) {
    Serial.println("[camera] sensor probe failed after esp_camera_init");
    esp_camera_deinit();
    return false;
  }

  Serial.printf(
      "[camera] sensor=%s PID=0x%04x frame_size=%d jpeg_quality=%d fb_count=%d grab_mode=%d\n",
      sensor_name(sensor->id.PID),
      static_cast<unsigned int>(sensor->id.PID),
      static_cast<int>(options.frame_size),
      options.jpeg_quality,
      options.fb_count,
      static_cast<int>(options.grab_mode));

  if (options.expected_sensor_pid != 0 && sensor->id.PID != options.expected_sensor_pid) {
    Serial.printf(
        "[camera] unexpected sensor PID=0x%04x (%s), expected PID=0x%04x (%s)\n",
        static_cast<unsigned int>(sensor->id.PID),
        sensor_name(sensor->id.PID),
        static_cast<unsigned int>(options.expected_sensor_pid),
        sensor_name(options.expected_sensor_pid));
    esp_camera_deinit();
    return false;
  }

  apply_common_sensor_settings(sensor, options.jpeg_quality);
  if (sensor->id.PID == OV5640_PID) {
    apply_ov5640_sensor_settings(sensor);
    Serial.println("[camera] applied OV5640 tuning");
  }

  if (!configure_ov5640_autofocus(sensor, options)) {
    esp_camera_deinit();
    return false;
  }

  if (sensor->id.PID == OV5640_PID && options.autofocus_enabled) {
    apply_common_sensor_settings(sensor, options.jpeg_quality);
    apply_ov5640_sensor_settings(sensor);
    Serial.println("[camera] reapplied OV5640 tuning after autofocus");
  }

  return true;
}

bool XiaoCamera::warmup() {
  bool captured_any = false;
  for (uint8_t index = 0; index < options_.warmup_frames; ++index) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame == nullptr) {
      Serial.printf("[camera] warmup frame %u failed\n", static_cast<unsigned int>(index + 1));
      delay(options_.warmup_delay_ms);
      continue;
    }
    captured_any = true;
    esp_camera_fb_return(frame);
    delay(options_.warmup_delay_ms);
  }
  return captured_any || options_.warmup_frames == 0;
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
