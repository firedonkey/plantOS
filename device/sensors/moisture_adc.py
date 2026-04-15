from dataclasses import dataclass
from collections import deque
import random
import time


@dataclass
class MoistureReading:
    raw_value: int | None
    percent: float | None
    ok: bool
    error: str | None = None
    smoothed_raw_value: float | None = None


class MoistureADCSensor:
    def __init__(self, config: dict, mock_mode: bool = False):
        self.config = config
        self.mock_mode = mock_mode or bool(config.get("mock_mode", False))
        self._ads = None
        self._channel = None
        self._i2c = None
        self._samples = deque(maxlen=max(1, int(config.get("moving_average_samples", 5))))

    def read(self) -> MoistureReading:
        try:
            raw_values = self._read_sample_window()
            latest_raw = raw_values[-1]
            smoothed_raw = sum(self._samples) / len(self._samples)
            return MoistureReading(
                raw_value=latest_raw,
                smoothed_raw_value=round(smoothed_raw, 1),
                percent=self._raw_to_percent(smoothed_raw),
                ok=True,
            )
        except Exception as exc:
            return MoistureReading(None, None, False, f"ADS1115 read failed: {exc}")

    def _read_sample_window(self) -> list[int]:
        sample_count = max(1, int(self.config.get("moving_average_samples", 5)))
        interval = max(0.0, float(self.config.get("read_interval_seconds", 1)))
        raw_values = []

        for sample_index in range(sample_count):
            raw_value = self._read_single_raw_value()
            self._samples.append(raw_value)
            raw_values.append(raw_value)
            # Keep sensor sampling simple and predictable for debugging on a Pi.
            if sample_index < sample_count - 1 and interval > 0:
                time.sleep(interval)

        return raw_values

    def _read_single_raw_value(self) -> int:
        if self.mock_mode or not self.config.get("enabled", True):
            return self._mock_raw_value()

        adc_type = str(self.config.get("adc_type", "ads1115")).lower()
        if adc_type != "ads1115":
            raise ValueError(f"Unsupported moisture adc_type: {adc_type}")
        return self._read_ads1115_channel()

    def _mock_raw_value(self) -> int:
        base_value = int(self.config.get("mock_raw_value", 650))
        variation = int(self.config.get("mock_raw_variation", 0))
        raw_value = base_value + random.randint(-variation, variation)
        dry = int(self.config.get("dry_value", 26000))
        wet = int(self.config.get("wet_value", 12000))
        upper_bound = max(dry, wet, base_value)
        return max(0, min(upper_bound, raw_value))

    def close(self) -> None:
        if self._i2c is not None and hasattr(self._i2c, "deinit"):
            self._i2c.deinit()
        self._ads = None
        self._channel = None
        self._i2c = None

    def _raw_to_percent(self, raw_value: float) -> float:
        dry = float(self.config.get("dry_value", 26000))
        wet = float(self.config.get("wet_value", 12000))
        if dry == wet:
            return 0.0
        percent = (dry - raw_value) / (dry - wet) * 100.0
        return round(max(0.0, min(100.0, percent)), 1)

    def _read_ads1115_channel(self) -> int:
        if self._channel is None:
            try:
                import board
                import busio
                import adafruit_ads1x15.ads1115 as ADS
                from adafruit_ads1x15.analog_in import AnalogIn
            except Exception as exc:
                raise RuntimeError(
                    "ADS1115 libraries unavailable. Install device/requirements-pi.txt on the Raspberry Pi."
                ) from exc

            channel_index = int(self.config.get("adc_channel", 0))
            channel_map = {
                0: ADS.P0,
                1: ADS.P1,
                2: ADS.P2,
                3: ADS.P3,
            }
            if channel_index not in channel_map:
                raise ValueError("ADS1115 channel must be between 0 and 3")

            address = _parse_int(self.config.get("i2c_address", "0x48"))
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS.ADS1115(self._i2c, address=address)
            self._ads.gain = float(self.config.get("gain", 1))
            if self.config.get("data_rate"):
                self._ads.data_rate = int(self.config["data_rate"])
            self._channel = AnalogIn(self._ads, channel_map[channel_index])

        return int(self._channel.value)


def _parse_int(value) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)
