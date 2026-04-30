from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import requests

from platform_client import (
    captured_image_path,
    handle_pending_commands,
    next_sleep_seconds,
    send_image,
    send_reading,
    send_status,
)
from services.automation import PlantAutomation


logger = logging.getLogger(__name__)


class PlatformRuntime:
    """Background device runtime for readings, images, commands, and status."""

    def __init__(self, config: dict, *, provisioning_state_file: str | Path):
        self.config = config
        self.provisioning_state_file = Path(provisioning_state_file)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            logger.info("platform runtime is already running")
            return

        device_context = self._device_context()
        logger.info(
            "starting platform runtime for platform_device_id=%s platform=%s",
            device_context["device_id"],
            device_context["platform_url"],
        )
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(device_context,),
            name="plantlab-platform-runtime",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 10.0) -> None:
        if not self.is_running():
            self._thread = None
            return

        logger.info("stopping platform runtime")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)
            if self._thread.is_alive():
                logger.warning("platform runtime did not stop within %.1fs", timeout_seconds)
            self._thread = None

    def _device_context(self) -> dict[str, str | int]:
        provisioning_data = self._load_provisioning_state()
        platform_config = self.config.get("platform", {})

        platform_url = (
            str(provisioning_data.get("platform_url") or "").rstrip("/")
            or str(platform_config.get("url") or "").rstrip("/")
        )
        device_id = provisioning_data.get("platform_device_id") or platform_config.get("device_id")
        device_token = provisioning_data.get("device_access_token") or platform_config.get("device_token")

        if not platform_url or not device_id or not device_token:
            raise RuntimeError(
                "Platform runtime requires platform_url, platform_device_id, and device_access_token."
            )

        return {
            "platform_url": str(platform_url),
            "device_id": int(device_id),
            "device_token": str(device_token),
        }

    def _load_provisioning_state(self) -> dict:
        if not self.provisioning_state_file.exists():
            return {}
        return json.loads(self.provisioning_state_file.read_text(encoding="utf-8"))

    def _run_loop(self, device_context: dict[str, str | int]) -> None:
        platform_url = str(device_context["platform_url"])
        device_id = int(device_context["device_id"])
        device_token = str(device_context["device_token"])
        platform_config = self.config.get("platform", {})
        camera_config = self.config.get("camera", {})
        send_interval = int(platform_config.get("send_interval_seconds") or 10)
        command_interval = int(platform_config.get("command_poll_interval_seconds") or 2)
        status_interval = int(platform_config.get("status_interval_seconds") or 10)
        image_every = int(platform_config.get("image_every_n_cycles") or 1)
        startup_send_interval = int(platform_config.get("startup_send_interval_seconds") or 2)
        startup_capture_overrides = {
            "resolution": str(camera_config.get("startup_resolution") or "640x480"),
            "skip_frames": int(camera_config.get("startup_skip_frames", 5)),
        }

        automation = PlantAutomation(self.config)
        command_thread = threading.Thread(
            target=self._run_command_loop,
            args=(platform_url, device_id, device_token, automation, command_interval),
            name="plantlab-command-poll",
            daemon=True,
        )
        status_thread = threading.Thread(
            target=self._run_status_loop,
            args=(platform_url, device_id, device_token, automation, status_interval),
            name="plantlab-status-heartbeat",
            daemon=True,
        )
        command_thread.start()
        status_thread.start()

        cycle = 0
        next_send_at = 0.0
        pending_image_path: Path | None = None
        has_uploaded_reading = False
        has_uploaded_first_image = False
        try:
            while not self._stop_event.is_set():
                now = time.monotonic()
                if now >= next_send_at:
                    cycle += 1
                    record = automation.run_once(
                        capture_overrides=None if has_uploaded_first_image else startup_capture_overrides
                    )
                    try:
                        send_reading(platform_url, device_id, device_token, record)
                        has_uploaded_reading = True
                    except requests.RequestException as exc:
                        logger.warning("reading upload failed: %s", exc)

                    should_upload_image = (
                        pending_image_path is not None
                        or not has_uploaded_first_image
                        or (image_every > 0 and cycle % image_every == 0)
                    )
                    if should_upload_image:
                        image_path = pending_image_path or captured_image_path(record, None)
                        if image_path is not None:
                            try:
                                send_image(platform_url, device_id, device_token, image_path)
                                pending_image_path = None
                                has_uploaded_first_image = True
                            except requests.RequestException as exc:
                                logger.warning("image upload failed: %s", exc)
                                pending_image_path = image_path
                        else:
                            logger.info("no camera image available to upload")

                    current_send_interval = (
                        startup_send_interval
                        if not (has_uploaded_reading and has_uploaded_first_image)
                        else send_interval
                    )
                    next_send_at = time.monotonic() + current_send_interval

                self._stop_event.wait(next_sleep_seconds(next_send_at))
        finally:
            self._stop_event.set()
            command_thread.join(timeout=5)
            status_thread.join(timeout=5)
            automation.close()
            logger.info("platform runtime stopped")

    def _run_command_loop(
        self,
        platform_url: str,
        device_id: int,
        device_token: str,
        automation: PlantAutomation,
        command_interval: int,
    ) -> None:
        logger.info("platform command polling every %s second(s)", command_interval)
        while not self._stop_event.is_set():
            started_at = time.monotonic()
            try:
                command_count = handle_pending_commands(
                    platform_url,
                    device_id,
                    device_token,
                    automation,
                )
                if command_count:
                    elapsed = time.monotonic() - started_at
                    logger.info("handled %s command(s) in %.2fs", command_count, elapsed)
            except requests.RequestException as exc:
                logger.warning("command poll failed: %s", exc)
            except Exception as exc:
                logger.warning("command handling failed: %s", exc)
            self._stop_event.wait(command_interval)

    def _run_status_loop(
        self,
        platform_url: str,
        device_id: int,
        device_token: str,
        automation: PlantAutomation,
        status_interval: int,
    ) -> None:
        while not self._stop_event.is_set():
            try:
                send_status(platform_url, device_id, device_token, automation.actuator_status())
            except requests.RequestException as exc:
                logger.warning("status heartbeat failed: %s", exc)
            except Exception as exc:
                logger.warning("status heartbeat skipped: %s", exc)
            self._stop_event.wait(status_interval)
