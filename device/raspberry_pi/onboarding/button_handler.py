"""GPIO button handling for PlantLab onboarding state machine.

Button wiring:
- GPIO23 (Pin 16)
- Active LOW (wired to GND)
- Internal pull-up enabled
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import RPi.GPIO as GPIO


@dataclass(frozen=True)
class ButtonEvent:
    """Button event derived from measured press duration."""

    kind: str  # "short" or "long"
    duration_seconds: float


class ButtonHandler:
    """Edge-detect button handler with duration measurement and debounce.

    How duration is measured:
    - On FALLING edge (active-low button press), record press_start timestamp.
    - On RISING edge (button release), compute duration = now - press_start.
    - Classify event:
      - duration >= long_press_seconds -> long press
      - duration < short_press_max_seconds -> short press
    """

    def __init__(
        self,
        pin: int = 23,
        *,
        debounce_seconds: float = 0.05,
        short_press_max_seconds: float = 2.0,
        long_press_seconds: float = 5.0,
        on_event: Optional[Callable[[ButtonEvent], None]] = None,
    ) -> None:
        self.pin = pin
        self.debounce_seconds = debounce_seconds
        self.short_press_max_seconds = short_press_max_seconds
        self.long_press_seconds = long_press_seconds
        self.on_event = on_event

        self._lock = threading.Lock()
        self._press_started_at: Optional[float] = None
        self._last_edge_at: float = 0.0

    def start(self) -> None:
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # If a stale edge detector exists from a previous run/process, clear it first.
        try:
            GPIO.remove_event_detect(self.pin)
        except RuntimeError:
            pass

        # We detect both edges and run our own debounce logic in the callback.
        try:
            GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self._handle_edge, bouncetime=1)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Failed to add edge detection on GPIO{self.pin}. "
                "Another process may still be using this pin."
            ) from exc

    def stop(self) -> None:
        try:
            GPIO.remove_event_detect(self.pin)
        except RuntimeError:
            pass

    def _handle_edge(self, channel: int) -> None:
        now = time.monotonic()
        with self._lock:
            # Software debounce window for edge chatter.
            if (now - self._last_edge_at) < self.debounce_seconds:
                return
            self._last_edge_at = now

            level = GPIO.input(channel)
            if level == GPIO.LOW:
                # Press started (active low).
                self._press_started_at = now
                return

            # level == GPIO.HIGH => release.
            if self._press_started_at is None:
                return

            duration = now - self._press_started_at
            self._press_started_at = None

        event = self._classify_event(duration)
        if event is not None and self.on_event is not None:
            self.on_event(event)

    def _classify_event(self, duration_seconds: float) -> Optional[ButtonEvent]:
        if duration_seconds >= self.long_press_seconds:
            return ButtonEvent(kind="long", duration_seconds=duration_seconds)
        if duration_seconds < self.short_press_max_seconds:
            return ButtonEvent(kind="short", duration_seconds=duration_seconds)
        # 2s-5s range intentionally ignored for now.
        return None
