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
        sensor_mock_mode = config.get("mock_mode")
        self.mock_mode = bool(sensor_mock_mode) if sensor_mock_mode is not None else mock_mode

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

        return self._read_with_circuitpython()

    def _read_with_circuitpython(self) -> DHT22Reading:
        try:
            import adafruit_dht
            import board

            gpio_pin = int(self.config["gpio_pin"])
            board_pin = getattr(board, f"D{gpio_pin}")
            try:
                sensor = adafruit_dht.DHT22(board_pin, use_pulseio=False)
            except TypeError:
                sensor = adafruit_dht.DHT22(board_pin)

            try:
                temperature = sensor.temperature
                humidity = sensor.humidity
            finally:
                sensor.exit()

            if humidity is None or temperature is None:
                return DHT22Reading(None, None, False, "DHT22 returned no reading")
            return DHT22Reading(round(temperature, 2), round(humidity, 2), True)
        except ModuleNotFoundError as exc:
            return DHT22Reading(None, None, False, f"missing DHT22 dependency: {exc.name}")
        except AttributeError:
            return DHT22Reading(None, None, False, f"board pin D{self.config['gpio_pin']} is not available")
        except RuntimeError as exc:
            return DHT22Reading(None, None, False, str(exc))
        except Exception as exc:
            return DHT22Reading(None, None, False, str(exc))

    def _vary(self, base_value: float, variation: float) -> float:
        return base_value + random.uniform(-variation, variation)
