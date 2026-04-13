import time

from actuators.relay import Relay


class Pump:
    def __init__(self, config: dict, active_high: bool, mock_mode: bool = False):
        self.config = config
        self.relay = Relay(
            gpio_pin=int(config["gpio_pin"]),
            active_high=active_high,
            mock_mode=mock_mode or not config.get("enabled", True),
            name="pump",
        )

    @property
    def is_on(self) -> bool:
        return self.relay.is_on

    def run_for(self, seconds: int | None = None) -> None:
        duration = int(seconds or self.config.get("run_seconds", 5))
        self.relay.on()
        time.sleep(duration)
        self.relay.off()

    def off(self) -> None:
        self.relay.off()

    def close(self) -> None:
        self.relay.close()
