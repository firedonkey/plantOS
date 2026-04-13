from dataclasses import dataclass
import random


@dataclass
class MoistureReading:
    raw_value: int | None
    percent: float | None
    ok: bool
    error: str | None = None


class MoistureADCSensor:
    def __init__(self, config: dict, mock_mode: bool = False):
        self.config = config
        self.mock_mode = mock_mode
        self._spi = None

    def read(self) -> MoistureReading:
        if self.mock_mode or not self.config.get("enabled", True):
            raw_value = self._mock_raw_value()
            return MoistureReading(raw_value, self._raw_to_percent(raw_value), True)

        try:
            raw_value = self._read_mcp3008_channel(int(self.config.get("adc_channel", 0)))
            return MoistureReading(raw_value, self._raw_to_percent(raw_value), True)
        except Exception as exc:
            return MoistureReading(None, None, False, str(exc))

    def _mock_raw_value(self) -> int:
        base_value = int(self.config.get("mock_raw_value", 650))
        variation = int(self.config.get("mock_raw_variation", 0))
        raw_value = base_value + random.randint(-variation, variation)
        return max(0, min(1023, raw_value))

    def close(self) -> None:
        if self._spi is not None:
            self._spi.close()
            self._spi = None

    def _raw_to_percent(self, raw_value: int) -> float:
        dry = float(self.config.get("dry_value", 850))
        wet = float(self.config.get("wet_value", 350))
        if dry == wet:
            return 0.0
        percent = (dry - raw_value) / (dry - wet) * 100.0
        return round(max(0.0, min(100.0, percent)), 1)

    def _read_mcp3008_channel(self, channel: int) -> int:
        if channel < 0 or channel > 7:
            raise ValueError("MCP3008 channel must be between 0 and 7")

        if self._spi is None:
            import spidev

            self._spi = spidev.SpiDev()
            self._spi.open(
                int(self.config.get("spi_bus", 0)),
                int(self.config.get("spi_device", 0)),
            )
            self._spi.max_speed_hz = 1350000

        response = self._spi.xfer2([1, (8 + channel) << 4, 0])
        return ((response[1] & 3) << 8) + response[2]
