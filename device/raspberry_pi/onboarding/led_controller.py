"""Non-blocking status LED controller for PlantLab onboarding.

LED wiring:
- GPIO24 (Pin 18)
- Series resistor to GND

This module keeps LED behavior independent from button/state logic by running
its own worker thread. The main loop can update state at any time via
set_state() without blocking.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Tuple

import RPi.GPIO as GPIO


@dataclass(frozen=True)
class LedPattern:
    """Simple ON/OFF timing pattern in seconds.

    - on_seconds/off_seconds > 0: blinking pattern
    - on_seconds == 0 and off_seconds == 0 with solid_on=True: solid ON
    - on_seconds == 0 and off_seconds == 0 with solid_on=False: solid OFF
    """

    on_seconds: float
    off_seconds: float
    solid_on: bool = False


class LedController:
    """Threaded LED controller for state-based, non-blocking patterns.

    State model used by onboarding logic:
    - IDLE: OFF
    - PROVISIONING: slow blink (1s ON / 1s OFF)
    - CONNECTED: solid ON
    - ERROR: fast blink (0.2s ON / 0.2s OFF)
    """

    VALID_STATES: Tuple[str, ...] = ("IDLE", "PROVISIONING", "CONNECTED", "ERROR")

    def __init__(self, pin: int = 24) -> None:
        self.pin = pin
        self._state = "IDLE"
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Easy-to-modify pattern table by state.
        self._patterns: Dict[str, LedPattern] = {
            "IDLE": LedPattern(on_seconds=0.0, off_seconds=0.0, solid_on=False),
            "PROVISIONING": LedPattern(on_seconds=1.0, off_seconds=1.0),
            "CONNECTED": LedPattern(on_seconds=0.0, off_seconds=0.0, solid_on=True),
            "ERROR": LedPattern(on_seconds=0.2, off_seconds=0.2),
        }

    def start(self) -> None:
        """Initialize GPIO pin and start background LED thread."""
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="led-controller", daemon=True)
        self._thread.start()
        print("[led] started in IDLE")

    def stop(self) -> None:
        """Stop background thread and turn off LED."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        GPIO.output(self.pin, GPIO.LOW)
        print("[led] stopped")

    def set_state(self, state: str) -> None:
        """Update LED state. Safe to call from other threads/callbacks."""
        if state not in self.VALID_STATES:
            raise ValueError(f"Invalid LED state: {state}")
        with self._state_lock:
            if state == self._state:
                return
            previous = self._state
            self._state = state
        print(f"[state] {previous} -> {state}")

    def get_state(self) -> str:
        with self._state_lock:
            return self._state

    def _run(self) -> None:
        """Worker loop that applies patterns without blocking main logic.

        Uses Event.wait(timeout) instead of busy loops to avoid high CPU usage.
        """
        last_state = None
        led_on = False

        while not self._stop_event.is_set():
            state = self.get_state()
            pattern = self._patterns[state]

            if state != last_state:
                # Reset phase on every state transition for predictable behavior.
                last_state = state
                led_on = False

            if pattern.on_seconds == 0.0 and pattern.off_seconds == 0.0:
                # Solid state (ON or OFF).
                GPIO.output(self.pin, GPIO.HIGH if pattern.solid_on else GPIO.LOW)
                # Sleep in short intervals so state changes apply quickly.
                self._stop_event.wait(0.1)
                continue

            # Blinking state.
            led_on = not led_on
            GPIO.output(self.pin, GPIO.HIGH if led_on else GPIO.LOW)
            delay = pattern.on_seconds if led_on else pattern.off_seconds
            self._stop_event.wait(delay)
