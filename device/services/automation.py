from datetime import datetime, timedelta

from actuators.light import Light
from actuators.pump import Pump
from camera.capture import USBCamera
from sensors.dht22 import DHT22Sensor
from sensors.moisture_adc import MoistureADCSensor
from services.logger import PlantLogger


class PlantAutomation:
    def __init__(self, config: dict):
        self.config = config
        mock_mode = bool(config.get("hardware", {}).get("mock_mode", True))
        active_high = bool(config.get("actuators", {}).get("relay_active_high", True))

        self.dht22 = DHT22Sensor(config["sensors"]["dht22"], mock_mode)
        self.moisture = MoistureADCSensor(config["sensors"]["moisture"], mock_mode)
        self.pump = Pump(config["actuators"]["pump"], active_high, mock_mode)
        self.light = Light(config["actuators"]["light"], active_high, mock_mode)
        self.camera = USBCamera(config["camera"], mock_mode)
        self.logger = PlantLogger(config["logging"])
        self.last_pump_time: datetime | None = None
        self.last_capture_time: datetime | None = None

    def run_once(self) -> dict:
        now = datetime.now()
        dht = self.dht22.read()
        moisture = self.moisture.read()
        light_on = self.light.apply_schedule(now)
        image_path = self._maybe_capture(now)
        pump_event = self._maybe_water(now, moisture.percent)

        errors = []
        if not dht.ok:
            errors.append(f"dht22: {dht.error}")
        if not moisture.ok:
            errors.append(f"moisture: {moisture.error}")

        record = {
            "timestamp": now.isoformat(timespec="seconds"),
            "temperature_c": dht.temperature_c,
            "humidity_percent": dht.humidity_percent,
            "moisture_raw": moisture.raw_value,
            "moisture_percent": moisture.percent,
            "light_on": light_on,
            "pump_event": pump_event,
            "image_path": image_path,
            "errors": "; ".join(errors),
        }
        self.logger.log(record)
        return record

    def close(self) -> None:
        self.pump.close()
        self.light.close()
        self.moisture.close()

    def _maybe_water(self, now: datetime, moisture_percent: float | None) -> str:
        if moisture_percent is None:
            return "skipped_no_moisture_reading"

        threshold = float(self.config["automation"].get("moisture_threshold_percent", 35))
        cooldown = int(self.config["actuators"]["pump"].get("cooldown_seconds", 3600))
        if moisture_percent >= threshold:
            return "not_needed"
        if self.last_pump_time and now - self.last_pump_time < timedelta(seconds=cooldown):
            return "skipped_cooldown"

        run_seconds = int(self.config["actuators"]["pump"].get("run_seconds", 5))
        self.pump.run_for(run_seconds)
        self.last_pump_time = datetime.now()
        return f"ran_{run_seconds}s"

    def _maybe_capture(self, now: datetime) -> str | None:
        interval = int(self.config["camera"].get("capture_interval_seconds", 3600))
        if self.last_capture_time and now - self.last_capture_time < timedelta(seconds=interval):
            return None
        self.last_capture_time = now
        return self.camera.capture()
