from dataclasses import dataclass


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
            return DHT22Reading(
                temperature_c=float(self.config.get("mock_temperature_c", 22.0)),
                humidity_percent=float(self.config.get("mock_humidity_percent", 50.0)),
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
