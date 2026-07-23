#pragma once

#include <stddef.h>
#include <stdint.h>

enum class WaterLevelPad : uint8_t {
  kTop = 0,
  kMiddle = 1,
  kBottom = 2,
};

enum class WaterLevelState : uint8_t {
  kUnknown = 0,
  kUncalibrated,
  kEmpty,
  kLow,
  kMedium,
  kHigh,
  kInconsistent,
  kSensorUnavailable,
};

enum class WaterLevelQuality : uint8_t {
  kValid = 0,
  kUncalibrated,
  kUnstable,
  kInconsistent,
  kSensorMissing,
  kReadError,
  kSaturated,
  kLowSignalMargin,
};

constexpr uint32_t kWaterLevelCalibrationVersion = 1;
constexpr size_t kWaterLevelChannelCount = 3;
constexpr uint8_t kWaterLevelMaxFilterSamples = 9;

struct WaterLevelChannelConfig {
  WaterLevelChannelConfig() = default;
  WaterLevelChannelConfig(WaterLevelPad pad_value, int gpio_value, int touch_channel_value)
      : pad(pad_value), gpio(gpio_value), touch_channel(touch_channel_value) {}

  WaterLevelPad pad = WaterLevelPad::kTop;
  int gpio = -1;
  int touch_channel = -1;
};

struct WaterLevelChannelCalibration {
  bool dry_valid = false;
  bool wet_valid = false;
  bool valid = false;
  uint32_t dry_baseline = 0;
  uint32_t wet_reference = 0;
  uint32_t threshold = 0;
  uint32_t hysteresis = 0;
  bool wet_value_is_higher = false;
};

struct WaterLevelStoredCalibration {
  uint32_t version = kWaterLevelCalibrationVersion;
  WaterLevelChannelCalibration channels[kWaterLevelChannelCount]{};
};

struct WaterLevelSensorConfig {
  WaterLevelChannelConfig channels[kWaterLevelChannelCount]{};
  uint8_t filter_sample_count = 5;
  uint32_t sample_interval_ms = 100;
  uint32_t startup_settle_ms = 2000;
  uint32_t channel_debounce_ms = 1500;
  uint32_t state_debounce_ms = 2000;
  uint32_t inconsistent_grace_ms = 10000;
  uint8_t threshold_percent = 50;
  uint8_t hysteresis_percent = 10;
  uint32_t min_signal_delta = 25;
  uint32_t max_stable_spread = 300;
  uint32_t read_failure_timeout_ms = 5000;
  uint32_t saturated_raw_low = 0;
  uint32_t saturated_raw_high = 0;
};

struct WaterLevelChannelReading {
  WaterLevelPad pad = WaterLevelPad::kTop;
  int gpio = -1;
  int touch_channel = -1;
  bool available = false;
  bool calibrated = false;
  bool wet = false;
  bool stable = false;
  bool saturated = false;
  bool low_signal_margin = false;
  uint32_t raw = 0;
  uint32_t filtered = 0;
  uint32_t min_observed = 0;
  uint32_t max_observed = 0;
  uint32_t spread = 0;
  uint32_t threshold = 0;
  uint32_t hysteresis = 0;
  int32_t margin = 0;
  uint16_t read_failures = 0;
  WaterLevelChannelCalibration calibration{};
};

struct WaterLevelReading {
  bool valid = false;
  bool sensor_present = false;
  bool calibrated = false;
  bool stable = false;
  WaterLevelState state = WaterLevelState::kUnknown;
  WaterLevelState instantaneous_state = WaterLevelState::kUnknown;
  WaterLevelQuality quality = WaterLevelQuality::kUnstable;
  uint8_t percent = 0;
  uint32_t representative_raw = 0;
  uint64_t sampled_at_ms = 0;
  uint64_t stable_since_ms = 0;
  const char* diagnostic_reason = "startup";
  WaterLevelChannelReading channels[kWaterLevelChannelCount]{};
};

class WaterLevelTouchTransport {
 public:
  virtual ~WaterLevelTouchTransport() = default;
  virtual bool beginChannel(int gpio) = 0;
  virtual bool readRaw(int gpio, uint32_t* raw) = 0;
};

class Esp32WaterLevelTouchTransport : public WaterLevelTouchTransport {
 public:
  bool beginChannel(int gpio) override;
  bool readRaw(int gpio, uint32_t* raw) override;
};

const char* waterLevelPadName(WaterLevelPad pad);
const char* waterLevelStateName(WaterLevelState state);
const char* waterLevelQualityName(WaterLevelQuality quality);
uint8_t waterLevelPercent(WaterLevelState state);

class WaterLevelSensor {
 public:
  WaterLevelSensor(WaterLevelTouchTransport* transport, const WaterLevelSensorConfig& config);

  bool begin(uint64_t now_ms = 0);
  bool update(uint64_t now_ms);
  WaterLevelReading reading() const;
  WaterLevelReading read(uint64_t now_ms);

  bool captureDryCalibration();
  bool captureWetReference(WaterLevelPad pad);
  bool loadCalibration(const WaterLevelStoredCalibration& calibration);
  bool saveCalibration(WaterLevelStoredCalibration* calibration) const;
  void resetCalibration();
  bool calibrationReady() const;

  void setDiagnosticMode(bool enabled);
  bool diagnosticMode() const;

 private:
  struct ChannelRuntime {
    WaterLevelChannelReading reading{};
    bool begin_ok = false;
    bool read_success_seen = false;
    uint64_t last_read_success_ms = 0;
    uint32_t samples[kWaterLevelMaxFilterSamples]{};
    uint8_t sample_count = 0;
    uint8_t next_sample_index = 0;
    bool instantaneous_wet = false;
    bool debounced_wet = false;
    bool has_candidate = false;
    bool candidate_wet = false;
    uint64_t candidate_since_ms = 0;
  };

  WaterLevelSensorConfig normalizedConfig(WaterLevelSensorConfig config) const;
  void initializeChannelReadings();
  bool recordChannelSample(ChannelRuntime* runtime, uint32_t raw, uint64_t now_ms);
  void updateChannelClassification(ChannelRuntime* runtime, uint64_t now_ms);
  void evaluateReading(uint64_t now_ms);
  bool recomputeChannelCalibration(size_t index);
  bool channelStableForCalibration(const ChannelRuntime& runtime) const;
  WaterLevelState classify(bool top_wet, bool middle_wet, bool bottom_wet) const;
  void updateStableState(WaterLevelState candidate, uint64_t now_ms);
  bool allSampleWindowsFilled() const;
  bool anyChannelAvailable() const;
  bool anyChannelSampleAttempted() const;
  bool allChannelsAvailable() const;
  bool anyChannelSaturated() const;
  bool anyChannelLowSignalMargin() const;
  bool allChannelsStable() const;
  bool allChannelsCalibrated() const;
  size_t indexForPad(WaterLevelPad pad) const;

  WaterLevelTouchTransport* transport_;
  WaterLevelSensorConfig config_;
  ChannelRuntime channels_[kWaterLevelChannelCount]{};
  WaterLevelReading reading_{};
  bool begun_ = false;
  bool diagnostic_mode_ = false;
  uint64_t begin_ms_ = 0;
  uint64_t next_sample_due_ms_ = 0;
  WaterLevelState stable_state_ = WaterLevelState::kUnknown;
  WaterLevelState pending_state_ = WaterLevelState::kUnknown;
  bool has_pending_state_ = false;
  uint64_t pending_state_since_ms_ = 0;
  uint64_t stable_state_since_ms_ = 0;
};
