"""Interactive button hardware test for PlantLab Raspberry Pi onboarding.

Hardware under test:
- Button on GPIO23 (physical pin 16)
- Active LOW, wired to GND
- Internal pull-up enabled

Behavior:
- Prints a message immediately when the button is pressed
- Prints a message when the button is released
- Uses lightweight polling with software debounce for reliability
"""

from __future__ import annotations

import time

import RPi.GPIO as GPIO


BUTTON_PIN = 23
POLL_INTERVAL_SECONDS = 0.01
DEBOUNCE_SECONDS = 0.05


def main() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    last_stable_level = GPIO.input(BUTTON_PIN)
    last_seen_level = last_stable_level
    last_change_at = time.monotonic()
    press_started_at: float | None = None

    print("[button-test] started")
    print("[button-test] GPIO23 / pin 16, active LOW")
    print("[button-test] press Ctrl+C to quit")

    try:
        while True:
            now = time.monotonic()
            current_level = GPIO.input(BUTTON_PIN)

            if current_level != last_seen_level:
                last_seen_level = current_level
                last_change_at = now

            if (
                current_level != last_stable_level
                and (now - last_change_at) >= DEBOUNCE_SECONDS
            ):
                last_stable_level = current_level

                if current_level == GPIO.LOW:
                    press_started_at = now
                    print("[button-test] Button pressed")
                else:
                    duration = 0.0 if press_started_at is None else now - press_started_at
                    press_started_at = None
                    print(f"[button-test] Button released ({duration:.2f}s)")

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[button-test] quitting")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()

