#include "config.h"
#include "sensors/water_level_sensor.h"

#include <cassert>
#include <cstdint>

namespace {

class FakeTouchTransport : public WaterLevelTouchTransport {
 public:
  bool beginChannel(int gpio) override {
    if (gpio < 0 || !begin_ok) {
      return false;
    }
    return true;
  }

  bool readRaw(int gpio, uint32_t* raw) override {
    if (raw == nullptr || !read_ok) {
      return false;
    }
    if (gpio == WATER_LEVEL_TOP_GPIO) {
      *raw = top_raw;
      return true;
    }
    if (gpio == WATER_LEVEL_MIDDLE_GPIO) {
      *raw = middle_raw;
      return true;
    }
    if (gpio == WATER_LEVEL_BOTTOM_GPIO) {
      *raw = bottom_raw;
      return true;
    }
    return false;
  }

  void set(uint32_t top, uint32_t middle, uint32_t bottom) {
    top_raw = top;
    middle_raw = middle;
    bottom_raw = bottom;
  }

  bool begin_ok = true;
  bool read_ok = true;
  uint32_t top_raw = 1000;
  uint32_t middle_raw = 1000;
  uint32_t bottom_raw = 1000;
};

WaterLevelSensorConfig testConfig(
    uint32_t channel_debounce_ms = 0,
    uint32_t state_debounce_ms = 0,
    uint8_t filter_sample_count = 5) {
  WaterLevelSensorConfig config{};
  config.channels[0] = WaterLevelChannelConfig{
      WaterLevelPad::kTop,
      WATER_LEVEL_TOP_GPIO,
      WATER_LEVEL_TOP_TOUCH_CHANNEL};
  config.channels[1] = WaterLevelChannelConfig{
      WaterLevelPad::kMiddle,
      WATER_LEVEL_MIDDLE_GPIO,
      WATER_LEVEL_MIDDLE_TOUCH_CHANNEL};
  config.channels[2] = WaterLevelChannelConfig{
      WaterLevelPad::kBottom,
      WATER_LEVEL_BOTTOM_GPIO,
      WATER_LEVEL_BOTTOM_TOUCH_CHANNEL};
  config.filter_sample_count = filter_sample_count;
  config.sample_interval_ms = 0;
  config.startup_settle_ms = 0;
  config.channel_debounce_ms = channel_debounce_ms;
  config.state_debounce_ms = state_debounce_ms;
  config.inconsistent_grace_ms = 0;
  config.threshold_percent = 50;
  config.hysteresis_percent = 10;
  config.min_signal_delta = 20;
  config.max_stable_spread = 1000;
  return config;
}

void pumpSamples(
    WaterLevelSensor* sensor,
    FakeTouchTransport* transport,
    uint64_t* now_ms,
    uint32_t top,
    uint32_t middle,
    uint32_t bottom) {
  transport->set(top, middle, bottom);
  for (uint8_t index = 0; index < 5; ++index) {
    ++(*now_ms);
    assert(sensor->update(*now_ms));
  }
}

WaterLevelStoredCalibration fallingWhenWetCalibration() {
  WaterLevelStoredCalibration calibration{};
  calibration.version = kWaterLevelCalibrationVersion;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    calibration.channels[index].dry_valid = true;
    calibration.channels[index].wet_valid = true;
    calibration.channels[index].dry_baseline = 1000;
    calibration.channels[index].wet_reference = 300;
  }
  return calibration;
}

}  // namespace

int main() {
  static_assert(WATER_LEVEL_TOP_GPIO == 4, "top water-level pad must stay on GPIO4");
  static_assert(WATER_LEVEL_MIDDLE_GPIO == 5, "middle water-level pad must stay on GPIO5");
  static_assert(WATER_LEVEL_BOTTOM_GPIO == 6, "bottom water-level pad must stay on GPIO6");
  static_assert(WATER_LEVEL_TOP_TOUCH_CHANNEL == 4, "top pad must use TOUCH4");
  static_assert(WATER_LEVEL_MIDDLE_TOUCH_CHANNEL == 5, "middle pad must use TOUCH5");
  static_assert(WATER_LEVEL_BOTTOM_TOUCH_CHANNEL == 6, "bottom pad must use TOUCH6");

  FakeTouchTransport fake;
  WaterLevelSensor sensor(&fake, testConfig());
  assert(sensor.begin(0));
  uint64_t now_ms = 0;

  pumpSamples(&sensor, &fake, &now_ms, 1000, 1000, 1000);
  assert(sensor.reading().state == WaterLevelState::kUncalibrated);
  assert(sensor.reading().quality == WaterLevelQuality::kUncalibrated);
  assert(sensor.reading().valid);
  assert(sensor.captureDryCalibration());

  pumpSamples(&sensor, &fake, &now_ms, 300, 1000, 1000);
  assert(sensor.captureWetReference(WaterLevelPad::kTop));
  pumpSamples(&sensor, &fake, &now_ms, 1000, 300, 1000);
  assert(sensor.captureWetReference(WaterLevelPad::kMiddle));
  pumpSamples(&sensor, &fake, &now_ms, 1000, 1000, 300);
  assert(sensor.captureWetReference(WaterLevelPad::kBottom));
  assert(sensor.calibrationReady());

  WaterLevelStoredCalibration saved{};
  assert(sensor.saveCalibration(&saved));
  assert(saved.channels[0].threshold == 650);
  assert(saved.channels[0].wet_value_is_higher == false);

  pumpSamples(&sensor, &fake, &now_ms, 1000, 1000, 1000);
  assert(sensor.reading().state == WaterLevelState::kEmpty);
  assert(sensor.reading().percent == 0);
  assert(sensor.reading().quality == WaterLevelQuality::kValid);

  pumpSamples(&sensor, &fake, &now_ms, 1000, 1000, 300);
  assert(sensor.reading().state == WaterLevelState::kLow);
  assert(sensor.reading().percent == 33);

  pumpSamples(&sensor, &fake, &now_ms, 1000, 300, 300);
  assert(sensor.reading().state == WaterLevelState::kMedium);
  assert(sensor.reading().percent == 67);

  pumpSamples(&sensor, &fake, &now_ms, 300, 300, 300);
  assert(sensor.reading().state == WaterLevelState::kHigh);
  assert(sensor.reading().percent == 100);

  pumpSamples(&sensor, &fake, &now_ms, 300, 1000, 300);
  assert(sensor.reading().state == WaterLevelState::kInconsistent);
  assert(sensor.reading().quality == WaterLevelQuality::kInconsistent);

  FakeTouchTransport high_fake;
  WaterLevelSensor high_sensor(&high_fake, testConfig());
  assert(high_sensor.begin(0));
  uint64_t high_now_ms = 0;
  WaterLevelStoredCalibration rising{};
  rising.version = kWaterLevelCalibrationVersion;
  for (size_t index = 0; index < kWaterLevelChannelCount; ++index) {
    rising.channels[index].dry_valid = true;
    rising.channels[index].wet_valid = true;
    rising.channels[index].dry_baseline = 300;
    rising.channels[index].wet_reference = 1000;
  }
  assert(high_sensor.loadCalibration(rising));
  pumpSamples(&high_sensor, &high_fake, &high_now_ms, 1000, 300, 1000);
  assert(high_sensor.reading().state == WaterLevelState::kInconsistent);
  pumpSamples(&high_sensor, &high_fake, &high_now_ms, 300, 300, 1000);
  assert(high_sensor.reading().state == WaterLevelState::kLow);

  FakeTouchTransport debounced_fake;
  WaterLevelSensor debounced(&debounced_fake, testConfig(200, 200, 1));
  assert(debounced.begin(0));
  assert(debounced.loadCalibration(fallingWhenWetCalibration()));
  debounced_fake.set(1000, 1000, 1000);
  assert(debounced.update(1));
  assert(debounced.update(201));
  assert(debounced.reading().state == WaterLevelState::kEmpty);
  debounced_fake.set(1000, 1000, 300);
  assert(debounced.update(250));
  assert(debounced.reading().state == WaterLevelState::kEmpty);
  assert(debounced.update(450));
  assert(debounced.reading().state == WaterLevelState::kEmpty);
  assert(debounced.update(650));
  assert(debounced.reading().state == WaterLevelState::kLow);

  FakeTouchTransport missing_fake;
  missing_fake.read_ok = false;
  WaterLevelSensor missing(&missing_fake, testConfig());
  assert(missing.begin(0));
  assert(missing.update(0));
  assert(missing.reading().state == WaterLevelState::kSensorUnavailable);
  assert(missing.reading().quality == WaterLevelQuality::kSensorMissing);

  return 0;
}
