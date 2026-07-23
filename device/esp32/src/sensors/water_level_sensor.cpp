#include "sensors/water_level_sensor.h"

#include <algorithm>
#include <limits>

#if __has_include(<Arduino.h>)
#include <Arduino.h>
#define PLANTLAB_WATER_LEVEL_HAS_ARDUINO 1
#else
#define PLANTLAB_WATER_LEVEL_HAS_ARDUINO 0
#endif

namespace {

uint32_t absDiff(uint32_t left, uint32_t right) {
  return left > right ? left - right : right - left;
}

uint32_t clampU32(uint32_t value, uint32_t low, uint32_t high) {
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

uint32_t medianOf(const uint32_t* values, uint8_t count) {
  if (values == nullptr || count == 0) {
    return 0;
  }
  uint32_t sorted[kWaterLevelMaxFilterSamples]{};
  const uint8_t safe_count = std::min<uint8_t>(count, kWaterLevelMaxFilterSamples);
  for (uint8_t index = 0; index < safe_count; ++index) {
    sorted[index] = values[index];
  }
  std::sort(sorted, sorted + safe_count);
  return sorted[safe_count / 2];
}

bool stateIsReportable(WaterLevelState state) {
  return state != WaterLevelState::kUnknown;
}

}  // namespace

const char* waterLevelPadName(WaterLevelPad pad) {
  switch (pad) {
    case WaterLevelPad::kTop:
      return "top";
    case WaterLevelPad::kMiddle:
      return "middle";
    case WaterLevelPad::kBottom:
      return "bottom";
    default:
      return "unknown";
  }
}

const char* waterLevelStateName(WaterLevelState state) {
  switch (state) {
    case WaterLevelState::kUncalibrated:
      return "uncalibrated";
    case WaterLevelState::kEmpty:
      return "empty";
    case WaterLevelState::kLow:
      return "low";
    case WaterLevelState::kMedium:
      return "medium";
    case WaterLevelState::kHigh:
      return "high";
    case WaterLevelState::kInconsistent:
      return "inconsistent";
    case WaterLevelState::kSensorUnavailable:
      return "sensor_unavailable";
    case WaterLevelState::kUnknown:
    default:
      return "unknown";
  }
}

const char* waterLevelQualityName(WaterLevelQuality quality) {
  switch (quality) {
    case WaterLevelQuality::kValid:
      return "valid";
    case WaterLevelQuality::kUncalibrated:
      return "uncalibrated";
    case WaterLevelQuality::kInconsistent:
      return "inconsistent";
    case WaterLevelQuality::kSensorMissing:
      return "sensor_missing";
    case WaterLevelQuality::kReadError:
      return "read_error";
    case WaterLevelQuality::kSaturated:
      return "saturated";
    case WaterLevelQuality::kLowSignalMargin:
      return "low_signal_margin";
    case WaterLevelQuality::kUnstable:
    default:
      return "unstable";
  }
}

uint8_t waterLevelPercent(WaterLevelState state) {
  switch (state) {
    case WaterLevelState::kLow:
      return 33;
    case WaterLevelState::kMedium:
      return 67;
    case WaterLevelState::kHigh:
      return 100;
    case WaterLevelState::kEmpty:
    case WaterLevelState::kUncalibrated:
    case WaterLevelState::kInconsistent:
    case WaterLevelState::kSensorUnavailable:
    case WaterLevelState::kUnknown:
    default:
      return 0;
  }
}

bool Esp32WaterLevelTouchTransport::beginChannel(int gpio) {
  return gpio >= 0;
}

bool Esp32WaterLevelTouchTransport::readRaw(int gpio, uint32_t* raw) {
  if (gpio < 0 || raw == nullptr) {
    return false;
  }
#if PLANTLAB_WATER_LEVEL_HAS_ARDUINO
  *raw = static_cast<uint32_t>(touchRead(gpio));
  return true;
#else
  return false;
#endif
}

WaterLevelSensor::WaterLevelSensor(WaterLevelTouchTransport* transport, const WaterLevelSensorConfig& config)
    : transport_(transport),
      config_(normalizedConfig(config)) {
  initializeChannelReadings();
}

WaterLevelSensorConfig WaterLevelSensor::normalizedConfig(WaterLevelSensorConfig config) const {
  config.filter_sample_count =
      std::max<uint8_t>(1, std::min<uint8_t>(config.filter_sample_count, kWaterLevelMaxFilterSamples));
  config.threshold_percent = std::min<uint8_t>(config.threshold_percent, 100);
  config.hysteresis_percent = std::min<uint8_t>(config.hysteresis_percent, 100);
  return config;
}

void WaterLevelSensor::initializeChannelReadings() {
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    channels_[index].reading.pad = config_.channels[index].pad;
    channels_[index].reading.gpio = config_.channels[index].gpio;
    channels_[index].reading.touch_channel = config_.channels[index].touch_channel;
    reading_.channels[index] = channels_[index].reading;
  }
}

bool WaterLevelSensor::begin(uint64_t now_ms) {
  begun_ = true;
  begin_ms_ = now_ms;
  next_sample_due_ms_ = now_ms;
  stable_state_ = WaterLevelState::kUnknown;
  pending_state_ = WaterLevelState::kUnknown;
  has_pending_state_ = false;
  pending_state_since_ms_ = 0;
  stable_state_since_ms_ = now_ms;

  bool any_ok = false;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    ChannelRuntime& runtime = channels_[index];
    runtime.begin_ok =
        transport_ != nullptr && transport_->beginChannel(config_.channels[index].gpio);
    runtime.read_success_seen = false;
    runtime.last_read_success_ms = 0;
    runtime.sample_count = 0;
    runtime.next_sample_index = 0;
    runtime.instantaneous_wet = false;
    runtime.debounced_wet = false;
    runtime.has_candidate = false;
    runtime.candidate_wet = false;
    runtime.candidate_since_ms = 0;
    runtime.reading.available = false;
    runtime.reading.stable = false;
    runtime.reading.read_failures = 0;
    runtime.reading.min_observed = std::numeric_limits<uint32_t>::max();
    runtime.reading.max_observed = 0;
    any_ok = any_ok || runtime.begin_ok;
  }

  evaluateReading(now_ms);
  return any_ok;
}

bool WaterLevelSensor::update(uint64_t now_ms) {
  if (!begun_) {
    begin(now_ms);
  }
  if (now_ms < next_sample_due_ms_) {
    return false;
  }
  next_sample_due_ms_ = now_ms + config_.sample_interval_ms;

  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    ChannelRuntime& runtime = channels_[index];
    if (!runtime.begin_ok || transport_ == nullptr) {
      runtime.reading.available = false;
      runtime.reading.read_failures =
          runtime.reading.read_failures == std::numeric_limits<uint16_t>::max()
              ? runtime.reading.read_failures
              : static_cast<uint16_t>(runtime.reading.read_failures + 1);
      continue;
    }

    uint32_t raw = 0;
    if (!transport_->readRaw(config_.channels[index].gpio, &raw)) {
      runtime.reading.read_failures =
          runtime.reading.read_failures == std::numeric_limits<uint16_t>::max()
              ? runtime.reading.read_failures
              : static_cast<uint16_t>(runtime.reading.read_failures + 1);
      if (runtime.read_success_seen &&
          config_.read_failure_timeout_ms > 0 &&
          now_ms - runtime.last_read_success_ms < config_.read_failure_timeout_ms) {
        continue;
      }
      runtime.reading.available = false;
      continue;
    }

    recordChannelSample(&runtime, raw, now_ms);
    updateChannelClassification(&runtime, now_ms);
  }

  evaluateReading(now_ms);
  return true;
}

WaterLevelReading WaterLevelSensor::reading() const {
  return reading_;
}

WaterLevelReading WaterLevelSensor::read(uint64_t now_ms) {
  update(now_ms);
  return reading_;
}

bool WaterLevelSensor::recordChannelSample(ChannelRuntime* runtime, uint32_t raw, uint64_t now_ms) {
  if (runtime == nullptr) {
    return false;
  }

  runtime->samples[runtime->next_sample_index] = raw;
  runtime->next_sample_index =
      static_cast<uint8_t>((runtime->next_sample_index + 1) % config_.filter_sample_count);
  if (runtime->sample_count < config_.filter_sample_count) {
    ++runtime->sample_count;
  }

  runtime->read_success_seen = true;
  runtime->last_read_success_ms = now_ms;
  runtime->reading.available = true;
  runtime->reading.raw = raw;
  runtime->reading.filtered = medianOf(runtime->samples, runtime->sample_count);
  runtime->reading.min_observed = std::min(runtime->reading.min_observed, raw);
  runtime->reading.max_observed = std::max(runtime->reading.max_observed, raw);
  runtime->reading.spread = absDiff(runtime->reading.max_observed, runtime->reading.min_observed);
  runtime->reading.read_failures = 0;
  runtime->reading.saturated =
      raw <= config_.saturated_raw_low ||
      (config_.saturated_raw_high > 0 && raw >= config_.saturated_raw_high);
  return true;
}

void WaterLevelSensor::updateChannelClassification(ChannelRuntime* runtime, uint64_t now_ms) {
  if (runtime == nullptr) {
    return;
  }
  runtime->reading.calibrated = runtime->reading.calibration.valid;
  runtime->reading.threshold = runtime->reading.calibration.threshold;
  runtime->reading.hysteresis = runtime->reading.calibration.hysteresis;
  runtime->reading.low_signal_margin = false;

  if (!runtime->reading.available ||
      runtime->sample_count < config_.filter_sample_count ||
      !runtime->reading.calibration.valid ||
      runtime->reading.saturated) {
    runtime->reading.stable = false;
    runtime->instantaneous_wet = false;
    runtime->has_candidate = false;
    return;
  }

  const WaterLevelChannelCalibration& calibration = runtime->reading.calibration;
  const uint32_t filtered = runtime->reading.filtered;
  const uint32_t hysteresis = calibration.hysteresis;
  bool wet = false;
  if (calibration.wet_value_is_higher) {
    const uint32_t on_threshold = calibration.threshold + hysteresis;
    const uint32_t keep_threshold =
        calibration.threshold > hysteresis ? calibration.threshold - hysteresis : 0;
    wet = runtime->debounced_wet ? filtered >= keep_threshold : filtered >= on_threshold;
  } else {
    const uint32_t on_threshold =
        calibration.threshold > hysteresis ? calibration.threshold - hysteresis : 0;
    const uint32_t keep_threshold = calibration.threshold + hysteresis;
    wet = runtime->debounced_wet ? filtered <= keep_threshold : filtered <= on_threshold;
  }

  runtime->instantaneous_wet = wet;
  const int64_t signed_margin =
      calibration.wet_value_is_higher
          ? static_cast<int64_t>(filtered) - static_cast<int64_t>(calibration.threshold)
          : static_cast<int64_t>(calibration.threshold) - static_cast<int64_t>(filtered);
  runtime->reading.margin = static_cast<int32_t>(
      std::max<int64_t>(std::numeric_limits<int32_t>::min(),
                        std::min<int64_t>(std::numeric_limits<int32_t>::max(), signed_margin)));
  runtime->reading.low_signal_margin = absDiff(filtered, calibration.threshold) <= hysteresis;

  if (!runtime->has_candidate || runtime->candidate_wet != wet) {
    runtime->has_candidate = true;
    runtime->candidate_wet = wet;
    runtime->candidate_since_ms = now_ms;
  }

  if (config_.channel_debounce_ms == 0 ||
      now_ms - runtime->candidate_since_ms >= config_.channel_debounce_ms) {
    runtime->debounced_wet = wet;
    runtime->reading.wet = runtime->debounced_wet;
    runtime->reading.stable = true;
  } else {
    runtime->reading.stable = false;
  }
}

void WaterLevelSensor::evaluateReading(uint64_t now_ms) {
  reading_.sampled_at_ms = now_ms;
  reading_.sensor_present = anyChannelAvailable();
  reading_.calibrated = allChannelsCalibrated();
  const size_t bottom_index = indexForPad(WaterLevelPad::kBottom);
  reading_.representative_raw =
      bottom_index < kWaterLevelChannelCount ? channels_[bottom_index].reading.filtered : 0;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    reading_.channels[index] = channels_[index].reading;
  }

  const bool in_startup_settle = now_ms - begin_ms_ < config_.startup_settle_ms;
  if (!reading_.sensor_present && begun_ && anyChannelSampleAttempted()) {
    stable_state_ = WaterLevelState::kSensorUnavailable;
    stable_state_since_ms_ = now_ms;
    has_pending_state_ = false;
    reading_.state = stable_state_;
    reading_.instantaneous_state = stable_state_;
    reading_.quality = WaterLevelQuality::kSensorMissing;
    reading_.stable = true;
    reading_.valid = true;
    reading_.percent = waterLevelPercent(reading_.state);
    reading_.stable_since_ms = stable_state_since_ms_;
    reading_.diagnostic_reason = "touch pads unavailable";
    return;
  }

  if (in_startup_settle || !allSampleWindowsFilled()) {
    reading_.instantaneous_state = WaterLevelState::kUnknown;
    reading_.state = stable_state_;
    reading_.quality = WaterLevelQuality::kUnstable;
    reading_.stable = false;
    reading_.valid = stateIsReportable(reading_.state);
    reading_.percent = waterLevelPercent(reading_.state);
    reading_.stable_since_ms = stable_state_since_ms_;
    reading_.diagnostic_reason = in_startup_settle ? "startup settle" : "warming filter";
    return;
  }

  if (!allChannelsAvailable()) {
    updateStableState(WaterLevelState::kSensorUnavailable, now_ms);
    reading_.instantaneous_state = WaterLevelState::kSensorUnavailable;
    reading_.quality = WaterLevelQuality::kReadError;
    reading_.diagnostic_reason = "one or more touch pads failed";
  } else if (!reading_.calibrated) {
    updateStableState(WaterLevelState::kUncalibrated, now_ms);
    reading_.instantaneous_state = WaterLevelState::kUncalibrated;
    reading_.quality = WaterLevelQuality::kUncalibrated;
    reading_.diagnostic_reason = "calibration required";
  } else {
    const ChannelRuntime& top = channels_[indexForPad(WaterLevelPad::kTop)];
    const ChannelRuntime& middle = channels_[indexForPad(WaterLevelPad::kMiddle)];
    const ChannelRuntime& bottom = channels_[indexForPad(WaterLevelPad::kBottom)];
    const WaterLevelState instantaneous =
        classify(top.instantaneous_wet, middle.instantaneous_wet, bottom.instantaneous_wet);
    const WaterLevelState debounced =
        classify(top.debounced_wet, middle.debounced_wet, bottom.debounced_wet);

    reading_.instantaneous_state = instantaneous;
    updateStableState(debounced, now_ms);

    if (anyChannelSaturated()) {
      reading_.quality = WaterLevelQuality::kSaturated;
      reading_.diagnostic_reason = "touch raw saturated";
    } else if (!allChannelsStable()) {
      reading_.quality = WaterLevelQuality::kUnstable;
      reading_.diagnostic_reason = "debouncing";
    } else if (instantaneous == WaterLevelState::kInconsistent ||
               stable_state_ == WaterLevelState::kInconsistent) {
      reading_.quality = stable_state_ == WaterLevelState::kInconsistent
                             ? WaterLevelQuality::kInconsistent
                             : WaterLevelQuality::kUnstable;
      reading_.diagnostic_reason = stable_state_ == WaterLevelState::kInconsistent
                                       ? "persistently inconsistent pads"
                                       : "inconsistent pads in grace period";
    } else if (anyChannelLowSignalMargin()) {
      reading_.quality = WaterLevelQuality::kLowSignalMargin;
      reading_.diagnostic_reason = "near threshold";
    } else {
      reading_.quality = WaterLevelQuality::kValid;
      reading_.diagnostic_reason = "ok";
    }
  }

  reading_.state = stable_state_;
  reading_.stable = !has_pending_state_ && allChannelsStable();
  if (stable_state_ == WaterLevelState::kUncalibrated ||
      stable_state_ == WaterLevelState::kSensorUnavailable) {
    reading_.stable = true;
  }
  reading_.valid = stateIsReportable(reading_.state);
  reading_.percent = waterLevelPercent(reading_.state);
  reading_.stable_since_ms = stable_state_since_ms_;
}

void WaterLevelSensor::updateStableState(WaterLevelState candidate, uint64_t now_ms) {
  const uint32_t debounce_ms =
      candidate == WaterLevelState::kInconsistent ? config_.inconsistent_grace_ms : config_.state_debounce_ms;

  if (candidate == stable_state_) {
    has_pending_state_ = false;
    pending_state_ = WaterLevelState::kUnknown;
    pending_state_since_ms_ = 0;
    return;
  }

  if (!has_pending_state_ || pending_state_ != candidate) {
    has_pending_state_ = true;
    pending_state_ = candidate;
    pending_state_since_ms_ = now_ms;
  }

  if (debounce_ms == 0 || now_ms - pending_state_since_ms_ >= debounce_ms) {
    stable_state_ = candidate;
    stable_state_since_ms_ = now_ms;
    has_pending_state_ = false;
    pending_state_ = WaterLevelState::kUnknown;
    pending_state_since_ms_ = 0;
  }
}

WaterLevelState WaterLevelSensor::classify(bool top_wet, bool middle_wet, bool bottom_wet) const {
  if (!top_wet && !middle_wet && !bottom_wet) {
    return WaterLevelState::kEmpty;
  }
  if (!top_wet && !middle_wet && bottom_wet) {
    return WaterLevelState::kLow;
  }
  if (!top_wet && middle_wet && bottom_wet) {
    return WaterLevelState::kMedium;
  }
  if (top_wet && middle_wet && bottom_wet) {
    return WaterLevelState::kHigh;
  }
  return WaterLevelState::kInconsistent;
}

bool WaterLevelSensor::captureDryCalibration() {
  bool ok = true;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    ChannelRuntime& runtime = channels_[index];
    if (!channelStableForCalibration(runtime)) {
      ok = false;
      continue;
    }
    runtime.reading.calibration.dry_baseline = runtime.reading.filtered;
    runtime.reading.calibration.dry_valid = true;
    recomputeChannelCalibration(index);
  }
  evaluateReading(reading_.sampled_at_ms);
  return ok;
}

bool WaterLevelSensor::captureWetReference(WaterLevelPad pad) {
  const size_t index = indexForPad(pad);
  if (index >= kWaterLevelChannelCount || !channelStableForCalibration(channels_[index])) {
    return false;
  }
  channels_[index].reading.calibration.wet_reference = channels_[index].reading.filtered;
  channels_[index].reading.calibration.wet_valid = true;
  const bool ok = recomputeChannelCalibration(index);
  evaluateReading(reading_.sampled_at_ms);
  return ok;
}

bool WaterLevelSensor::loadCalibration(const WaterLevelStoredCalibration& calibration) {
  if (calibration.version != kWaterLevelCalibrationVersion) {
    resetCalibration();
    return false;
  }
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    channels_[index].reading.calibration = calibration.channels[index];
    recomputeChannelCalibration(index);
  }
  evaluateReading(reading_.sampled_at_ms);
  return calibrationReady();
}

bool WaterLevelSensor::saveCalibration(WaterLevelStoredCalibration* calibration) const {
  if (calibration == nullptr) {
    return false;
  }
  calibration->version = kWaterLevelCalibrationVersion;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    calibration->channels[index] = channels_[index].reading.calibration;
  }
  return calibrationReady();
}

void WaterLevelSensor::resetCalibration() {
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    channels_[index].reading.calibration = WaterLevelChannelCalibration{};
    channels_[index].reading.calibrated = false;
    channels_[index].reading.threshold = 0;
    channels_[index].reading.hysteresis = 0;
    channels_[index].debounced_wet = false;
    channels_[index].instantaneous_wet = false;
    channels_[index].has_candidate = false;
  }
  stable_state_ = WaterLevelState::kUnknown;
  has_pending_state_ = false;
  evaluateReading(reading_.sampled_at_ms);
}

bool WaterLevelSensor::calibrationReady() const {
  return allChannelsCalibrated();
}

void WaterLevelSensor::setDiagnosticMode(bool enabled) {
  diagnostic_mode_ = enabled;
}

bool WaterLevelSensor::diagnosticMode() const {
  return diagnostic_mode_;
}

bool WaterLevelSensor::recomputeChannelCalibration(size_t index) {
  if (index >= kWaterLevelChannelCount) {
    return false;
  }
  WaterLevelChannelCalibration& calibration = channels_[index].reading.calibration;
  calibration.valid = false;
  if (!calibration.dry_valid || !calibration.wet_valid) {
    return false;
  }

  const uint32_t delta = absDiff(calibration.dry_baseline, calibration.wet_reference);
  if (delta < config_.min_signal_delta) {
    calibration.threshold = 0;
    calibration.hysteresis = 0;
    return false;
  }

  calibration.wet_value_is_higher = calibration.wet_reference > calibration.dry_baseline;
  const uint32_t dry = calibration.dry_baseline;
  const uint32_t offset = (delta * static_cast<uint32_t>(config_.threshold_percent)) / 100UL;
  if (calibration.wet_value_is_higher) {
    calibration.threshold = dry + offset;
  } else {
    calibration.threshold = dry > offset ? dry - offset : 0;
  }
  const uint32_t requested_hysteresis =
      (delta * static_cast<uint32_t>(config_.hysteresis_percent)) / 100UL;
  calibration.hysteresis = clampU32(requested_hysteresis, 1, std::max<uint32_t>(1, delta / 2));
  calibration.valid = true;
  channels_[index].reading.calibrated = true;
  channels_[index].reading.threshold = calibration.threshold;
  channels_[index].reading.hysteresis = calibration.hysteresis;
  return true;
}

bool WaterLevelSensor::channelStableForCalibration(const ChannelRuntime& runtime) const {
  return runtime.reading.available &&
         runtime.sample_count >= config_.filter_sample_count &&
         !runtime.reading.saturated &&
         (config_.max_stable_spread == 0 || runtime.reading.spread <= config_.max_stable_spread);
}

bool WaterLevelSensor::allSampleWindowsFilled() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (runtime.sample_count < config_.filter_sample_count) {
      return false;
    }
  }
  return true;
}

bool WaterLevelSensor::anyChannelAvailable() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (runtime.reading.available) {
      return true;
    }
  }
  return false;
}

bool WaterLevelSensor::anyChannelSampleAttempted() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (runtime.sample_count > 0 || runtime.reading.read_failures > 0) {
      return true;
    }
  }
  return false;
}

bool WaterLevelSensor::allChannelsAvailable() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (!runtime.reading.available) {
      return false;
    }
  }
  return true;
}

bool WaterLevelSensor::anyChannelSaturated() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (runtime.reading.saturated) {
      return true;
    }
  }
  return false;
}

bool WaterLevelSensor::anyChannelLowSignalMargin() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (runtime.reading.low_signal_margin) {
      return true;
    }
  }
  return false;
}

bool WaterLevelSensor::allChannelsStable() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (!runtime.reading.stable) {
      return false;
    }
  }
  return true;
}

bool WaterLevelSensor::allChannelsCalibrated() const {
  for (const ChannelRuntime& runtime : channels_) {
    if (!runtime.reading.calibration.valid) {
      return false;
    }
  }
  return true;
}

size_t WaterLevelSensor::indexForPad(WaterLevelPad pad) const {
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    if (config_.channels[index].pad == pad) {
      return index;
    }
  }
  return kWaterLevelChannelCount;
}
