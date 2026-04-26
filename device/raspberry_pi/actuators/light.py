from datetime import datetime

from actuators.relay import Relay


class Light:
    def __init__(self, config: dict, active_high: bool, mock_mode: bool = False):
        self.config = config
        self.relay = Relay(
            gpio_pin=int(config["gpio_pin"]),
            active_high=active_high,
            mock_mode=mock_mode or not config.get("enabled", True),
            name="light",
        )

    @property
    def is_on(self) -> bool:
        return self.relay.is_on

    def apply_schedule(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        on_hour = int(self.config.get("on_hour", 7))
        off_hour = int(self.config.get("off_hour", 21))

        should_be_on = on_hour <= now.hour < off_hour
        if should_be_on:
            self.relay.on()
        else:
            self.relay.off()
        return should_be_on

    def on(self) -> None:
        self.relay.on()

    def off(self) -> None:
        self.relay.off()

    def close(self) -> None:
        self.relay.close()
