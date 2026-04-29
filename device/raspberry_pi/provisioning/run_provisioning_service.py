"""Button-driven provisioning controller for PlantLab Raspberry Pi.

Behavior:
- Short press: log only
- Hold 5 seconds: start provisioning mode if the device is not already provisioned
- Hold 10 seconds: factory reset local + backend provisioning state

LED states:
- IDLE: off
- PROVISIONING: slow blink
- CONNECTED: solid on
- ERROR: fast blink
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

import RPi.GPIO as GPIO

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_CONFIG_PATH, load_config
from provisioning.button_handler import ButtonEvent, ButtonHandler
from provisioning.led_controller import LedController
from provisioning.service import ProvisioningService
from services.platform_runtime import PlatformRuntime


logger = logging.getLogger(__name__)


class ProvisioningController:
    def __init__(self, config_path: str = "config.gcp.yaml") -> None:
        config = load_config(config_path)
        provisioning_config = config.get("provisioning", {})
        platform_config = config.get("platform", {})
        hotspot_open = bool(provisioning_config.get("open_hotspot", False))
        if hotspot_open:
            hotspot_password = ""
        elif "hotspot_password" in provisioning_config:
            hotspot_password = str(provisioning_config.get("hotspot_password") or "")
        else:
            hotspot_password = "plantlabsetup"

        backend_url = (
            provisioning_config.get("backend_url")
            or platform_config.get("url")
            or "https://marspotatolab.com"
        )
        platform_url = platform_config.get("url")
        state_file = provisioning_config.get("state_file") or "data/provisioning/device_config.json"
        dry_run = bool(provisioning_config.get("network_dry_run", True))

        self.service = ProvisioningService(
            backend_url=str(backend_url),
            platform_url=str(platform_url).rstrip("/") if platform_url else None,
            state_file=str(state_file),
            host="0.0.0.0",
            port=8080,
            dry_run=dry_run,
            hardware_version=str(provisioning_config.get("hardware_version") or "raspberry_pi_3"),
            software_version=str(provisioning_config.get("software_version") or "0.1.0"),
            capabilities=provisioning_config.get("capabilities") or {},
            hotspot_password=hotspot_password,
            backend_retry_attempts=int(provisioning_config.get("backend_retry_attempts") or 12),
            backend_retry_delay_seconds=float(provisioning_config.get("backend_retry_delay_seconds") or 5),
        )

        self.state_file = Path(str(state_file))
        self.initial_state = "CONNECTED" if self.service.store.is_provisioned() else "IDLE"
        self.state = "IDLE"
        self.busy_lock = threading.Lock()
        self.runtime = PlatformRuntime(config, provisioning_state_file=self.state_file)

        self.led = LedController(pin=24)
        self.button = ButtonHandler(
            pin=23,
            long_press_seconds=5.0,
            factory_reset_seconds=10.0,
            on_event=self.on_button_event,
        )

    def run(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.led.start()
        self.button.start()
        self.set_state(self.initial_state)
        self._sync_runtime_with_state()

        logger.info("provisioning controller started; state=%s", self.state)
        try:
            while True:
                time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info("provisioning controller stopping")
        finally:
            self.runtime.stop()
            self.button.stop()
            self.led.stop()
            GPIO.cleanup()

    def on_button_event(self, event: ButtonEvent) -> None:
        logger.info("button event=%s duration=%.2fs", event.kind, event.duration_seconds)

        if event.kind == "short":
            logger.info("Button pressed (short)")
            return

        if event.kind == "long":
            if self.busy_lock.locked():
                logger.info("provisioning is already in progress")
                return
            threading.Thread(target=self._run_reprovision_flow, daemon=True).start()
            return

        if event.kind == "factory_reset":
            if self.busy_lock.locked():
                logger.info("factory reset ignored because provisioning is in progress")
                return
            threading.Thread(target=self._run_factory_reset_flow, daemon=True).start()

    def set_state(self, next_state: str) -> None:
        if self.state == next_state:
            return
        logger.info("state %s -> %s", self.state, next_state)
        self.state = next_state
        self.led.set_state(next_state)
        self._sync_runtime_with_state()

    def _sync_runtime_with_state(self) -> None:
        if self.state == "CONNECTED" and self.service.store.is_provisioned():
            try:
                self.runtime.start()
            except Exception as exc:
                logger.error("could not start platform runtime: %s", exc)
                self.runtime.stop()
                self.state = "ERROR"
                self.led.set_state("ERROR")
        else:
            self.runtime.stop()

    def _run_reprovision_flow(self) -> None:
        with self.busy_lock:
            self.set_state("PROVISIONING")
            if self.service.store.is_provisioned():
                logger.warning("device is already provisioned; resetting before provisioning again")
                try:
                    self.service.factory_reset(forget_wifi=False)
                except Exception as exc:
                    logger.error("factory reset before reprovision failed: %s", exc)
                    self.set_state("ERROR")
                    return
            try:
                self.service.run()
            except Exception as exc:
                logger.error("provisioning failed: %s", exc)
                self.set_state("ERROR")
                return

            if self.service.store.is_provisioned():
                self.set_state("CONNECTED")
            else:
                self.set_state("IDLE")

    def _run_factory_reset_flow(self) -> None:
        with self.busy_lock:
            logger.warning("factory reset triggered from hardware button")
            try:
                self.service.factory_reset()
            except Exception as exc:
                logger.error("factory reset failed: %s", exc)
                self.set_state("ERROR")
                return

            logger.info("factory reset complete; device is ready as a new device")
            self.set_state("IDLE")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the PlantLab Raspberry Pi button-driven provisioning controller."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to device YAML config.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ProvisioningController(config_path=args.config).run()


if __name__ == "__main__":
    main()
