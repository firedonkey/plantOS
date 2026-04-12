class Relay:
    def __init__(
        self,
        gpio_pin: int,
        active_high: bool = True,
        mock_mode: bool = False,
        name: str = "relay",
    ):
        self.gpio_pin = gpio_pin
        self.active_high = active_high
        self.mock_mode = mock_mode
        self.name = name
        self._device = None
        self._is_on = False

        if not mock_mode:
            try:
                from gpiozero import OutputDevice

                self._device = OutputDevice(
                    gpio_pin,
                    active_high=active_high,
                    initial_value=False,
                )
            except Exception as exc:
                self.mock_mode = True
                print(f"[{self.name}] GPIO unavailable, using mock relay: {exc}")

    @property
    def is_on(self) -> bool:
        return self._is_on

    def on(self) -> None:
        self._is_on = True
        if self._device is not None:
            self._device.on()
        else:
            print(f"[{self.name}] ON")

    def off(self) -> None:
        self._is_on = False
        if self._device is not None:
            self._device.off()
        else:
            print(f"[{self.name}] OFF")

    def close(self) -> None:
        self.off()
        if self._device is not None:
            self._device.close()
            self._device = None
