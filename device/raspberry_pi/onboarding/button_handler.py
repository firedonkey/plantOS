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
    - While the button is still held, a lightweight monitor can trigger the
      long-press event as soon as the hold crosses the configured threshold.
    - On RISING edge (button release), compute duration = now - press_start.
    - Classify event:
      - held >= long_press_seconds -> long press immediately
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
        self._last_polled_level: Optional[int] = None
        self._long_press_fired = False
        self._event_detect_enabled = False
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._stop_event.clear()
        # If a stale edge detector exists from a previous run/process, clear it first.
        try:
            GPIO.remove_event_detect(self.pin)
        except RuntimeError:
            pass

        # We detect both edges and run our own debounce logic in the callback.
        try:
            GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self._handle_edge, bouncetime=1)
            self._event_detect_enabled = True
            print(f"[button] using edge-detect mode on GPIO{self.pin}")
        except RuntimeError as exc:
            self._event_detect_enabled = False
            print(
                f"[button] edge-detect unavailable on GPIO{self.pin} ({exc}). "
                "Falling back to polling mode."
            )
        self._start_polling()

    def stop(self) -> None:
        self._stop_event.set()
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=1.0)
            self._poll_thread = None
        try:
            if self._event_detect_enabled:
                GPIO.remove_event_detect(self.pin)
        except RuntimeError:
            pass
        self._event_detect_enabled = False

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
                self._long_press_fired = False
                return

            # level == GPIO.HIGH => release.
            if self._press_started_at is None:
                return

            duration = now - self._press_started_at
            self._press_started_at = None
            long_press_fired = self._long_press_fired
            self._long_press_fired = False

        if long_press_fired:
            return

        event = self._classify_release_event(duration)
        if event is not None and self.on_event is not None:
            self.on_event(event)

    def _start_polling(self) -> None:
        self._poll_thread = threading.Thread(target=self._poll_loop, name="button-poll", daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Fallback mode plus long-press monitor while the button is held."""
        self._last_polled_level = GPIO.input(self.pin)
        while not self._stop_event.is_set():
            self._check_button_state()
            self._stop_event.wait(0.01)

    def _check_button_state(self) -> None:
        now = time.monotonic()
        level = GPIO.input(self.pin)
        callback_event: Optional[ButtonEvent] = None
        should_handle_edge = False

        with self._lock:
            if self._last_polled_level is None:
                self._last_polled_level = level

            if not self._event_detect_enabled and level != self._last_polled_level:
                self._last_polled_level = level
                should_handle_edge = True
            else:
                self._last_polled_level = level

                if (
                    level == GPIO.LOW
                    and self._press_started_at is not None
                    and not self._long_press_fired
                ):
                    duration = now - self._press_started_at
                    if duration >= self.long_press_seconds:
                        self._long_press_fired = True
                        callback_event = ButtonEvent(kind="long", duration_seconds=duration)

        if should_handle_edge:
            self._handle_edge(self.pin)
            return

        if callback_event is not None and self.on_event is not None:
            self.on_event(callback_event)

    def _classify_release_event(self, duration_seconds: float) -> Optional[ButtonEvent]:
        if duration_seconds < self.short_press_max_seconds:
            return ButtonEvent(kind="short", duration_seconds=duration_seconds)
        # 2s-5s range intentionally ignored for now.
        return None
