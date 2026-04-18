import threading
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
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._run_thread: threading.Thread | None = None

    @property
    def is_on(self) -> bool:
        return self.relay.is_on

    def run_for(self, seconds: int | None = None, wait: bool = True) -> None:
        duration = int(seconds or self.config.get("run_seconds", 5))
        with self._lock:
            self._stop_event.set()
            self._stop_event = threading.Event()
            stop_event = self._stop_event
            self.relay.on()

        if wait:
            self._wait_then_stop(duration, stop_event)
            return

        self._run_thread = threading.Thread(
            target=self._wait_then_stop,
            args=(duration, stop_event),
            daemon=True,
        )
        self._run_thread.start()

    def off(self) -> None:
        with self._lock:
            self._stop_event.set()
            self.relay.off()

    def close(self) -> None:
        self.off()
        if self._run_thread is not None and self._run_thread.is_alive():
            self._run_thread.join(timeout=1)
        self.relay.close()

    def _wait_then_stop(self, duration: int, stop_event: threading.Event) -> None:
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if stop_event.wait(min(0.2, deadline - time.monotonic())):
                return
        with self._lock:
            if stop_event is self._stop_event:
                self.relay.off()
