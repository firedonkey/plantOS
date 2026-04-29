"""PlantLab Raspberry Pi onboarding hardware test.

Tests:
- Button on GPIO23 (active LOW, pull-up)
- Status LED on GPIO24

Behavior:
- Default state: IDLE (LED off)
- Short press (<2s): print "Button pressed (short)"
- Long press (>=5s): enter PROVISIONING (slow blink)
- Factory reset (>=10s): print "Factory reset requested" and return to IDLE
- After 10s in PROVISIONING: switch to CONNECTED (solid ON)
"""

from __future__ import annotations

import time

import RPi.GPIO as GPIO

from button_handler import ButtonEvent, ButtonHandler
from led_controller import LedController


class OnboardingTestApp:
    """Small firmware-style state machine for local GPIO validation."""

    def __init__(self) -> None:
        self.state = "IDLE"
        self.provision_started_at: float | None = None

        self.led = LedController(pin=24)
        self.button = ButtonHandler(pin=23, on_event=self.on_button_event)

    def set_state(self, next_state: str) -> None:
        if self.state == next_state:
            return
        print(f"[main] state {self.state} -> {next_state}")
        self.state = next_state
        self.led.set_state(next_state)
        if next_state == "PROVISIONING":
            self.provision_started_at = time.monotonic()

    def on_button_event(self, event: ButtonEvent) -> None:
        print(f"[button] {event.kind} press ({event.duration_seconds:.2f}s)")
        if event.kind == "short":
            print("Button pressed (short)")
            return

        if event.kind == "long":
            print("Entering provisioning mode")
            self.set_state("PROVISIONING")
            return

        if event.kind == "factory_reset":
            print("Factory reset requested")
            self.set_state("IDLE")
            self.provision_started_at = None

    def run(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.led.start()
        self.button.start()
        self.set_state("IDLE")

        print("[main] onboarding test started")
        print("[main] short press <2s, long press >=5s, factory reset >=10s, Ctrl+C to exit")

        try:
            while True:
                if self.state == "PROVISIONING" and self.provision_started_at is not None:
                    elapsed = time.monotonic() - self.provision_started_at
                    if elapsed >= 10.0:
                        self.set_state("CONNECTED")
                        self.provision_started_at = None
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[main] stopping onboarding test")
        finally:
            try:
                self.button.stop()
            except RuntimeError:
                pass
            self.led.stop()
            GPIO.cleanup()


if __name__ == "__main__":
    OnboardingTestApp().run()
