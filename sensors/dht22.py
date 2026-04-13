from dataclasses import dataclass
import random


@dataclass
class DHT22Reading:
    temperature_c: float | None
    humidity_percent: float | None
    ok: bool
    error: str | None = None


class DHT22Sensor:
    def __init__(self, config: dict, mock_mode: bool = False):
        self.config = config
        self.mock_mode = mock_mode

    def read(self) -> DHT22Reading:
        if self.mock_mode or not self.config.get("enabled", True):
            temperature = self._vary(
                float(self.config.get("mock_temperature_c", 22.0)),
                float(self.config.get("mock_temperature_variation_c", 0.0)),
            )
            humidity = self._vary(
                float(self.config.get("mock_humidity_percent", 50.0)),
                float(self.config.get("mock_humidity_variation_percent", 0.0)),
            )
            return DHT22Reading(
                temperature_c=round(temperature, 1),
                humidity_percent=round(max(0.0, min(100.0, humidity)), 1),
                ok=True,
            )

        try:
            import Adafruit_DHT

            humidity, temperature = Adafruit_DHT.read_retry(
                Adafruit_DHT.DHT22,
                int(self.config["gpio_pin"]),
            )
            if humidity is None or temperature is None:
                return DHT22Reading(None, None, False, "DHT22 returned no reading")
            return DHT22Reading(round(temperature, 2), round(humidity, 2), True)
        except Exception as exc:
            return DHT22Reading(None, None, False, str(exc))

    def _vary(self, base_value: float, variation: float) -> float:
        return base_value + random.uniform(-variation, variation)
