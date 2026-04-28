"""Interactive LED hardware test for PlantLab Raspberry Pi onboarding.

Hardware under test:
- LED on GPIO24 (physical pin 18)

Controls:
- Space: toggle LED on/off
- q: quit

This script uses terminal raw mode so key presses are handled immediately
without requiring Enter. It is intended as a quick wiring validation tool.
"""

from __future__ import annotations

import select
import sys
import termios
import tty

import RPi.GPIO as GPIO


LED_PIN = 24


class RawTerminal:
    """Context manager that enables single-key reads without pressing Enter."""

    def __enter__(self) -> "RawTerminal":
        self._fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)


def read_key(timeout_seconds: float = 0.1) -> str | None:
    """Return one pressed key, or None if no key arrived within timeout."""
    ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
    if not ready:
        return None
    return sys.stdin.read(1)


def main() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

    led_on = False
    print("[led-test] interactive LED test started")
    print("[led-test] GPIO24 / pin 18")
    print("[led-test] press Space to toggle LED, q to quit")

    try:
        with RawTerminal():
            while True:
                key = read_key()
                if key is None:
                    continue

                if key.lower() == "q":
                    print("\n[led-test] quitting")
                    break

                if key == " ":
                    led_on = not led_on
                    GPIO.output(LED_PIN, GPIO.HIGH if led_on else GPIO.LOW)
                    state = "ON" if led_on else "OFF"
                    print(f"\n[led-test] LED {state}")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()


if __name__ == "__main__":
    main()

