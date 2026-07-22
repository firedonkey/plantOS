from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from datetime import datetime, timezone
from typing import Any

from .simulator_config import SimulatorNodeConfig
from .simulator_events import MultipartFile, SimulatorApiClient, SimulatorApiError
from .simulator_fake_media import make_plant_png
from .simulator_ota import OtaSimulator


logger = logging.getLogger(__name__)


class SimulatedDeviceNode:
    def __init__(self, config: SimulatorNodeConfig, api: SimulatorApiClient, *, seed: int | None = None) -> None:
        self.config = config
        self.api = api
        self.rng = random.Random(seed if seed is not None else config.hardware_device_id)
        self.boot_time_monotonic = time.monotonic()
        self.message_counter = 0
        self.online = True
        self.light_enabled = False
        self.light_brightness_percent = 0
        self.capture_interval_seconds = 3600
        self.ota_status = "idle"
        self.last_command_id: str | None = None
        self.last_command_status: str | None = None
        self.last_error_code: str | None = None
        self.last_error_message: str | None = None
        self.error_counters: dict[str, int] = {}
        self.disabled_optional_paths: set[str] = set()
        self.ota = OtaSimulator()
        self.sensor_base_temperature_c = 25.8 + self.rng.uniform(-1.2, 1.2)
        self.sensor_base_humidity_percent = 41.0 + self.rng.uniform(-4.0, 4.0)
        self.sensor_base_water_temperature_c = 24.7 + self.rng.uniform(-0.8, 0.8)
        self.sensor_base_moisture_percent = 62.0 + self.rng.uniform(-8.0, 8.0)
        self.image_counter = 0

    async def register_node(self) -> None:
        if not self.config.register_node:
            return
        if self.config.device_id is None:
            raise ValueError(f"{self.config.hardware_device_id} cannot register without device_id.")
        payload = {
            "device_id": self.config.device_id,
            "hardware_device_id": self.config.hardware_device_id,
            "node_role": self.config.node_role,
            "node_index": self.config.node_index,
            "camera_role": self.config.camera_role if self.config.is_camera else None,
            "display_name": self.config.display_name,
            "hardware_model": self.config.hardware_model,
            "hardware_version": self.config.hardware_version,
            "software_version": self.config.firmware_version,
            "capabilities": self.capabilities_payload(),
            "status": "online" if self.online else "offline",
        }
        await self._post_json("/api/device-nodes/register", _without_none(payload))
        logger.info("[%s] registered node role=%s", self.config.hardware_device_id, self.config.node_role)

    async def send_heartbeat(self) -> None:
        if not self.should_transmit_now("heartbeat"):
            return
        payload = {
            "uptime_seconds": self.uptime_seconds(),
            "wifi_rssi_dbm": self.wifi_rssi_dbm(),
            "ip_address": self.ip_address(),
            "free_heap_bytes": self.free_heap_bytes(),
            "node_status": self.node_status(),
            "firmware_version": self.config.firmware_version,
            "hardware_model": self.config.hardware_model,
            "hardware_version": self.config.hardware_version,
            "camera_role": self.config.camera_role if self.config.is_camera else None,
            "capabilities": self.config.capabilities,
            "runtime": self.runtime_payload(),
        }
        actuators = self.actuators_payload()
        if actuators:
            payload["actuators"] = actuators
        await self._post_json("/api/hardware/heartbeat", self.envelope("HEARTBEAT", payload, "hb"))
        logger.debug("[%s] heartbeat status=%s", self.config.hardware_device_id, payload["node_status"])

    async def send_diagnostics(self) -> None:
        if not self.should_transmit_now("diagnostics"):
            return
        payload = self.diagnostics_payload()
        if "/api/hardware/diagnostics" in self.disabled_optional_paths:
            return
        try:
            await self._post_optional_json("/api/hardware/diagnostics", self.envelope("DIAGNOSTICS", _without_none(payload), "diag"))
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/hardware/diagnostics")
                logger.warning(
                    "[%s] diagnostics endpoint is unavailable; continuing with heartbeat-only simulation. Rebuild the backend to enable diagnostics.",
                    self.config.hardware_device_id,
                )
                return
            raise
        logger.debug("[%s] diagnostics severity=%s", self.config.hardware_device_id, payload["severity"])

    async def send_sensor_reading(self) -> None:
        if not self.config.is_master or not self.should_transmit_now("reading"):
            return
        payload = self.sensor_reading_payload()
        await self._post_json("/api/hardware/readings", payload)
        logger.info(
            "[%s] sensor reading temp=%.2fC humidity=%.1f%% water=%.2fC",
            self.config.hardware_device_id,
            payload["temperature"],
            payload["humidity"],
            payload["water_temperature_c"],
        )

    async def upload_fake_image(self) -> None:
        if not self.config.is_camera or not self.should_transmit_now("image"):
            return
        await self.upload_capture_image()

    async def upload_capture_image(self) -> dict[str, Any] | None:
        if self.config.device_id is None:
            return None
        if "/api/image" in self.disabled_optional_paths:
            return None
        if "image_upload_failure" in self.config.scenarios:
            self.last_error_code = "IMAGE_UPLOAD_FAILED"
            self.last_error_message = "Simulated image upload failure."
            self.error_counters["image_upload_failures"] = self.error_counters.get("image_upload_failures", 0) + 1
            await self.report_image_upload_failure("simulated_failure")
            logger.warning("[%s] simulated image upload failure", self.config.hardware_device_id)
            return None
        self.image_counter += 1
        captured_at = utc_now()
        upload_started_at = time.monotonic()
        png = make_plant_png(
            seed=abs(hash(self.config.hardware_device_id)) % 10000,
            frame_index=self.image_counter,
        )
        metadata = self.image_upload_envelope(
            status="uploaded",
            captured_at=captured_at,
            upload_reason="scheduled" if self.config.is_camera else "manual",
            width=360,
            height=240,
            content_type="image/png",
            upload_ms=max(1, int((time.monotonic() - upload_started_at) * 1000)),
        )
        try:
            response = await self._post_multipart(
                "/api/image",
                fields={
                    "device_id": self.config.device_id,
                    "source_hardware_device_id": self.config.hardware_device_id,
                    "camera_node_id": self.config.hardware_device_id,
                    "camera_role": self.config.camera_role,
                    "metadata": json.dumps(metadata),
                },
                files=[
                    MultipartFile(
                        field_name="file",
                        filename=f"{self.config.hardware_device_id}-{self.image_counter:04d}.png",
                        content_type="image/png",
                        data=png,
                    )
                ],
            )
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/image")
                logger.warning("[%s] image upload endpoint is unavailable.", self.config.hardware_device_id)
                return
            raise
        logger.info("[%s] uploaded fake image id=%s", self.config.hardware_device_id, response.get("id", "unknown"))
        return response

    async def report_image_upload_failure(self, failure_reason: str) -> None:
        if "/api/hardware/image-upload/report" in self.disabled_optional_paths:
            return
        try:
            await self._post_optional_json(
                "/api/hardware/image-upload/report",
                self.image_upload_envelope(
                    status="failed",
                    captured_at=utc_now(),
                    upload_reason="manual",
                    content_type="image/png",
                    failure_reason=failure_reason,
                ),
            )
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/hardware/image-upload/report")
                logger.warning(
                    "[%s] image upload report endpoint is unavailable; failure event simulation is disabled.",
                    self.config.hardware_device_id,
                )
                return
            raise

    async def poll_commands(self) -> None:
        if not self.should_transmit_now("poll"):
            return
        if "/api/hardware/commands/poll" in self.disabled_optional_paths:
            await self.poll_legacy_commands()
            return
        try:
            response = await self._get_optional_json(
                "/api/hardware/commands/poll",
                {
                    "hardware_device_id": self.config.hardware_device_id,
                    "node_role": self.config.node_role,
                    "firmware_version": self.config.firmware_version,
                    "schema_version": self.config.schema_version,
                    "hardware_model": self.config.hardware_model,
                    "limit": 10,
                },
            )
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/hardware/commands/poll")
                if self.config.is_master:
                    logger.warning(
                        "[%s] contract command polling endpoint is unavailable; falling back to legacy command polling.",
                        self.config.hardware_device_id,
                    )
                    await self.poll_legacy_commands()
                else:
                    logger.warning(
                        "[%s] contract command polling endpoint is unavailable; camera command simulation is disabled until the backend is rebuilt.",
                        self.config.hardware_device_id,
                    )
                return
            raise
        for command in response.get("commands") or []:
            if isinstance(command, dict):
                await self.handle_command(command)

    async def poll_legacy_commands(self) -> None:
        if not self.config.is_master:
            return
        if "/api/hardware/commands/pending" in self.disabled_optional_paths:
            return
        try:
            response = await self._get_optional_json(
                "/api/hardware/commands/pending",
                {"limit": 10},
            )
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/hardware/commands/pending")
                logger.warning(
                    "[%s] legacy command polling endpoint is unavailable; command simulation is disabled.",
                    self.config.hardware_device_id,
                )
                return
            raise
        commands = response.get("value") if isinstance(response.get("value"), list) else response.get("commands")
        for legacy_command in commands or []:
            if isinstance(legacy_command, dict):
                command = self.legacy_command_to_contract(legacy_command)
                if command is not None:
                    await self.handle_command(command)

    async def handle_command(self, command: dict[str, Any]) -> None:
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        command_type = str(payload.get("command_type") or "")
        command_id = str(payload.get("command_id") or "")
        is_legacy_poll_command = command.get("_simulator_transport") == "legacy_pending"
        self.last_command_id = command_id
        logger.info("[%s] command received type=%s id=%s", self.config.hardware_device_id, command_type, command_id)

        if not is_legacy_poll_command and "slow_command_ack" in self.config.scenarios:
            await asyncio.sleep(min(5.0, max(0.0, self.config.command_poll_interval_seconds)))
        if not is_legacy_poll_command:
            await self.send_command_result(command, "acked", f"{command_type} acknowledged.")

        if self.choose_command_failure(command_type):
            await self.fail_command(command, "Simulated command failure.", "INTERNAL_ERROR")
            return

        if command_type in {"SET_GROW_LIGHT_BRIGHTNESS", "SET_LIGHT_BRIGHTNESS"}:
            await self.handle_light_command(command)
        elif command_type == "CAPTURE_IMAGE":
            await self.handle_capture_command(command)
        elif command_type == "REQUEST_DIAGNOSTICS":
            await self.send_diagnostics()
            await self.complete_command(command, "Diagnostics reported.")
        elif command_type == "START_OTA":
            outcome = await self.ota.run(self, command)
            if outcome.success:
                await self.complete_command(command, outcome.message)
            elif outcome.rejected:
                await self.reject_command(command, outcome.message, outcome.error_code or "INVALID_PARAMS")
            else:
                await self.fail_command(command, outcome.message, outcome.error_code or "INTERNAL_ERROR")
        elif command_type == "REBOOT":
            await self.handle_reboot_command(command)
        elif command_type == "UPDATE_CAPTURE_INTERVAL":
            await self.handle_capture_interval_command(command)
        elif command_type in {"ENTER_PAIRING_MODE", "FACTORY_RESET"}:
            await self.complete_command(command, f"{command_type} simulated.")
        else:
            await self.send_command_result(command, "rejected", f"Unsupported command {command_type}.", error_code="UNKNOWN_COMMAND")

    async def handle_light_command(self, command: dict[str, Any]) -> None:
        params = command["payload"].get("params") or {}
        brightness = _int_percent(params.get("brightness_percent"), 100 if params.get("state") == "on" else 0)
        self.light_brightness_percent = brightness
        self.light_enabled = brightness > 0
        await asyncio.sleep(0.1)
        await self.complete_command(
            command,
            f"Light brightness set to {brightness}%.",
            result={
                "light_on": self.light_enabled,
                "light_intensity_percent": brightness,
            },
        )

    async def handle_capture_command(self, command: dict[str, Any]) -> None:
        await asyncio.sleep(0.25)
        upload_ms = self.rng.randint(650, 2200)
        image_response = await self.upload_capture_image()
        if image_response is None and "image_upload_failure" in self.config.scenarios:
            await self.fail_command(command, "Simulated image upload failure.", "INTERNAL_ERROR")
            return
        await self.complete_command(
            command,
            "Image capture simulated.",
            result={
                "image_id": image_response.get("id") if image_response else self.rng.randint(1000, 9999),
                "upload_ms": upload_ms,
                "source": "simulator",
            },
        )

    async def handle_reboot_command(self, command: dict[str, Any]) -> None:
        await self.send_command_result(command, "in_progress", "Rebooting simulator node.")
        self.online = False
        await asyncio.sleep(0.5)
        self.boot_time_monotonic = time.monotonic()
        self.online = True
        await self.complete_command(command, "Simulator node rebooted.")

    async def handle_capture_interval_command(self, command: dict[str, Any]) -> None:
        params = command["payload"].get("params") or {}
        interval = params.get("interval_seconds") or params.get("capture_interval_seconds")
        if isinstance(interval, int) and interval > 0:
            self.capture_interval_seconds = interval
            await self.complete_command(command, f"Capture interval set to {interval} seconds.", result={"capture_interval_seconds": interval})
        else:
            await self.send_command_result(command, "rejected", "Invalid capture interval.", error_code="INVALID_PARAMS")

    async def complete_command(self, command: dict[str, Any], message: str, *, result: dict[str, Any] | None = None) -> None:
        await self.send_command_result(command, "completed", message, result=result)

    async def fail_command(self, command: dict[str, Any], message: str, error_code: str) -> None:
        self.last_error_code = error_code
        self.last_error_message = message
        self.error_counters[error_code.lower()] = self.error_counters.get(error_code.lower(), 0) + 1
        await self.send_command_result(command, "failed", message, error_code=error_code)

    async def reject_command(self, command: dict[str, Any], message: str, error_code: str) -> None:
        self.last_error_code = error_code
        self.last_error_message = message
        await self.send_command_result(command, "rejected", message, error_code=error_code)

    async def send_command_result(
        self,
        command: dict[str, Any],
        status: str,
        message: str,
        *,
        result: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        command_id = str(payload.get("command_id") or "")
        route_id = parse_route_command_id(command_id)
        if route_id is None:
            logger.warning("[%s] cannot report command result for non-route command_id=%s", self.config.hardware_device_id, command_id)
            return
        result_payload = {
            "command_id": command_id,
            "command_type": payload.get("command_type"),
            "status": status,
            "message": message,
            "result": result or {},
            "error_code": error_code,
            "occurred_at": utc_now(),
        }
        await self._post_json(
            f"/api/hardware/commands/{route_id}/result",
            self.command_result_payload(command, result_payload),
        )
        self.last_command_status = status
        logger.info("[%s] command result id=%s status=%s", self.config.hardware_device_id, command_id, status)

    def command_result_payload(self, command: dict[str, Any], result_payload: dict[str, Any]) -> dict[str, Any]:
        if command.get("_simulator_transport") != "legacy_pending":
            return self.envelope("COMMAND_RESULT", _without_none(result_payload), "cmdres")
        result = result_payload.get("result") if isinstance(result_payload.get("result"), dict) else {}
        status = str(result_payload.get("status") or "")
        return _without_none(
            {
                "status": "completed" if status == "completed" else "failed",
                "message": result_payload.get("message"),
                "light_on": _optional_bool(result.get("light_on")),
                "light_intensity_percent": _optional_int_percent(result.get("light_intensity_percent")),
                "pump_on": _optional_bool(result.get("pump_on")),
            }
        )

    def legacy_command_to_contract(self, legacy_command: dict[str, Any]) -> dict[str, Any] | None:
        command_id = legacy_command.get("id")
        if command_id is None:
            return None
        target = str(legacy_command.get("target") or "").lower()
        action = str(legacy_command.get("action") or "").lower()
        command_type = legacy_command_type(target, action)
        if command_type is None:
            logger.warning(
                "[%s] ignoring unsupported legacy command target=%s action=%s",
                self.config.hardware_device_id,
                target,
                action,
            )
            return None
        target_role = "camera" if target == "camera" else "master"
        return {
            "_simulator_transport": "legacy_pending",
            "schema_version": self.config.schema_version,
            "message_id": f"legacy_cmdmsg_{command_id}",
            "device_id": legacy_command.get("device_id") or self.config.device_id,
            "hardware_device_id": self.config.hardware_device_id,
            "node_role": self.config.node_role,
            "message_type": "COMMAND",
            "sent_at": utc_now(),
            "payload": {
                "command_id": f"cmd_{command_id}",
                "command_type": command_type,
                "target": {
                    "node_role": target_role,
                    "hardware_device_id": None,
                },
                "params": legacy_command_params(target, action, legacy_command.get("value")),
                "timeout_ms": 150000 if target == "camera" else 20000,
                "priority": "normal",
            },
        }

    async def send_ota_status(
        self,
        *,
        command_id: str,
        status: str,
        progress_percent: int,
        target_version: str,
        firmware_channel: str,
        phase: str,
        message: str,
        failure_reason: str | None = None,
        release_id: str | None = None,
    ) -> None:
        self.ota_status = status
        payload = {
            "command_id": command_id,
            "status": status,
            "progress_percent": progress_percent,
            "current_version": self.config.firmware_version,
            "target_version": target_version,
            "firmware_channel": firmware_channel,
            "phase": phase,
            "message": message,
            "failure_reason": failure_reason,
            "release_id": release_id,
        }
        if "/api/hardware/ota/status" in self.disabled_optional_paths:
            return
        try:
            await self._post_optional_json("/api/hardware/ota/status", self.envelope("OTA_STATUS", _without_none(payload), "ota"))
        except SimulatorApiError as exc:
            if exc.status == 404:
                self.disabled_optional_paths.add("/api/hardware/ota/status")
                logger.warning(
                    "[%s] OTA status endpoint is unavailable; command flow continues without OTA timeline events.",
                    self.config.hardware_device_id,
                )
                return
            raise
        logger.info("[%s] OTA status=%s progress=%s", self.config.hardware_device_id, status, progress_percent)

    def envelope(self, message_type: str, payload: dict[str, Any], prefix: str) -> dict[str, Any]:
        self.message_counter += 1
        return {
            "schema_version": self.config.schema_version,
            "message_id": f"{prefix}_{self.config.hardware_device_id}_{self.message_counter}_{int(time.time() * 1000)}",
            "device_id": self.config.device_id,
            "hardware_device_id": self.config.hardware_device_id,
            "node_role": self.config.node_role,
            "message_type": message_type,
            "sent_at": utc_now(),
            "payload": payload,
        }

    def image_upload_envelope(
        self,
        *,
        status: str,
        captured_at: str | None,
        upload_reason: str,
        width: int | None = None,
        height: int | None = None,
        content_type: str | None = None,
        upload_ms: int | None = None,
        failure_reason: str | None = None,
    ) -> dict[str, Any]:
        payload = _without_none(
            {
                "status": status,
                "camera_node_id": self.config.hardware_device_id if self.config.is_camera else None,
                "camera_role": self.config.camera_role if self.config.is_camera else None,
                "source_hardware_device_id": self.config.hardware_device_id,
                "source_node_role": self.config.node_role,
                "captured_at": captured_at,
                "upload_reason": upload_reason,
                "width": width,
                "height": height,
                "content_type": content_type,
                "upload_ms": upload_ms,
                "failure_reason": failure_reason,
            }
        )
        return self.envelope("IMAGE_UPLOAD", payload, "img")

    def capabilities_payload(self) -> dict[str, Any]:
        return _without_none({
            "features": self.config.capabilities,
            "simulator": True,
            "contract_polling": True,
            "ota": "ota" in self.config.capabilities,
            "light_intensity_control": "grow_light" in self.config.capabilities or "ambient_led" in self.config.capabilities,
            "camera_role": self.config.camera_role if self.config.is_camera else None,
            "capture_phase_seconds": self.config.capture_phase_seconds if self.config.is_camera else None,
        })

    def actuators_payload(self) -> dict[str, Any] | None:
        if not self.config.is_master:
            return None
        return {
            "grow_light": {
                "enabled": self.light_enabled,
                "brightness_percent": self.light_brightness_percent,
            }
        }

    def runtime_payload(self) -> dict[str, Any]:
        return _without_none(
            {
                "capture_interval_seconds": self.capture_interval_seconds if self.config.is_master else None,
                "ota_status": self.ota_status,
                "provisioning_status": "provisioned",
                "camera_node_status": self.camera_node_status(),
                "last_command_id": self.last_command_id,
                "last_command_status": self.last_command_status,
            }
        )

    def diagnostics_payload(self) -> dict[str, Any]:
        scenario_code, scenario_message = self.scenario_error()
        status = self.node_status()
        last_error_code = self.last_error_code or scenario_code
        last_error_message = self.last_error_message or scenario_message
        severity = self.diagnostic_severity(status, last_error_code)
        return {
            "status": status,
            "severity": severity,
            "error_counters": self.diagnostic_error_counters(),
            "last_error_code": last_error_code,
            "last_error_message": last_error_message,
            "reboot_reason": "software_reset" if "reboot_loop" in self.config.scenarios else None,
            "subsystem_statuses": self.subsystem_statuses(),
        }

    def diagnostic_error_counters(self) -> dict[str, int]:
        counters = dict(self.error_counters)
        if "unstable_wifi" in self.config.scenarios:
            counters.setdefault("wifi_disconnects", 1)
        if "camera_disconnect" in self.config.scenarios or "camera_flapping" in self.config.scenarios:
            counters.setdefault("camera_timeouts", 1)
        if "image_upload_failure" in self.config.scenarios:
            counters.setdefault("image_upload_failures", 1)
        if "low_memory" in self.config.scenarios:
            counters.setdefault("low_memory_events", 1)
        return counters

    def diagnostic_severity(self, status: str, error_code: str | None) -> str:
        if "low_memory" in self.config.scenarios and self.free_heap_bytes() < 55_000:
            return "critical"
        if status in {"degraded", "error", "offline"} or error_code:
            return "warning"
        return "info"

    def scenario_error(self) -> tuple[str | None, str | None]:
        if "low_memory" in self.config.scenarios:
            return "LOW_MEMORY", "Free heap is below the simulator warning threshold."
        if "camera_disconnect" in self.config.scenarios:
            return "CAMERA_TIMEOUT", "Camera node did not respond before timeout."
        if "camera_flapping" in self.config.scenarios and not self.camera_flap_online():
            return "CAMERA_TIMEOUT", "Camera node connection is flapping."
        if "unstable_wifi" in self.config.scenarios:
            return "WIFI_UNSTABLE", "Wi-Fi connectivity is unstable."
        if "reboot_loop" in self.config.scenarios:
            return "REBOOT_LOOP", "Device is rebooting repeatedly."
        return None, None

    def sensor_reading_payload(self) -> dict[str, Any]:
        elapsed_minutes = max(0.0, (time.monotonic() - self.boot_time_monotonic) / 60.0)
        light_heat = 0.35 if self.light_enabled else 0.0
        temperature = self.sensor_base_temperature_c + light_heat + self.wave(elapsed_minutes, 0.18, 1.0)
        humidity = self.sensor_base_humidity_percent - light_heat * 0.8 + self.wave(elapsed_minutes, 1.7, 0.7)
        water_temperature = self.sensor_base_water_temperature_c + self.wave(elapsed_minutes, 0.08, 2.0)
        moisture = self.sensor_base_moisture_percent + self.wave(elapsed_minutes, 0.65, 0.45)
        return {
            "hardware_device_id": self.config.hardware_device_id,
            "moisture": round(max(0.0, min(100.0, moisture)), 1),
            "temperature": round(temperature, 2),
            "humidity": round(max(0.0, min(100.0, humidity)), 1),
            "water_temperature_c": round(water_temperature, 2),
            "water_level_raw": 740 + int(self.wave(elapsed_minutes, 22.0, 0.33)),
            "water_level_state": "ok",
            "light_on": self.light_enabled,
            "light_intensity_percent": self.light_brightness_percent,
            "pump_on": False,
            "pump_status": "off",
            "timestamp": utc_now(),
        }

    def wave(self, elapsed_minutes: float, amplitude: float, speed: float) -> float:
        phase = elapsed_minutes * speed + (abs(hash(self.config.hardware_device_id)) % 360) / 57.2958
        jitter = self.rng.uniform(-amplitude * 0.12, amplitude * 0.12)
        return math.sin(phase) * amplitude + jitter

    def subsystem_statuses(self) -> dict[str, str]:
        statuses = {
            "wifi": self.node_status(),
            "ota": self.ota_subsystem_status(),
        }
        if self.config.is_master:
            statuses["camera"] = self.camera_node_status()
            statuses["light"] = "online"
            if "low_memory" in self.config.scenarios:
                statuses["memory"] = "error" if self.free_heap_bytes() < 55_000 else "degraded"
        if self.config.is_camera:
            statuses["camera"] = "online" if self.online else "offline"
            if "image_upload_failure" in self.config.scenarios:
                statuses["image_upload"] = "degraded"
        return statuses

    def ota_subsystem_status(self) -> str:
        if self.ota_status in {"preparing", "downloading", "validating", "installing", "rebooting"}:
            return "updating"
        if self.ota_status in {"failed", "rolled_back"}:
            return "error"
        return "online"

    def camera_node_status(self) -> str | None:
        if not self.config.is_master:
            return None
        if "camera_disconnect" in self.config.scenarios:
            return "offline"
        if "camera_flapping" in self.config.scenarios:
            return "online" if self.camera_flap_online() else "offline"
        return "online"

    def camera_flap_online(self) -> bool:
        cycle_position = int(time.monotonic() - self.boot_time_monotonic) % 20
        return cycle_position < 12

    def node_status(self) -> str:
        if not self.online:
            return "offline"
        if self.config.is_camera and "camera_flapping" in self.config.scenarios and not self.camera_flap_online():
            return "offline"
        if (
            "unstable_wifi" in self.config.scenarios
            or "camera_disconnect" in self.config.scenarios
            or "camera_flapping" in self.config.scenarios
            or "low_memory" in self.config.scenarios
        ):
            return "degraded"
        if self.last_error_code:
            return "degraded"
        if self.ota_status in {"preparing", "downloading", "validating", "installing", "rebooting"}:
            return "updating"
        return "online"

    def should_transmit_now(self, kind: str) -> bool:
        if not self.online:
            return False
        if self.config.is_camera and "camera_flapping" in self.config.scenarios and not self.camera_flap_online():
            return False
        if "heartbeat_timeout" in self.config.scenarios and kind == "heartbeat":
            return False
        if "unstable_wifi" in self.config.scenarios and kind in {"heartbeat", "diagnostics", "poll"} and self.rng.random() < 0.25:
            self.error_counters["wifi_disconnects"] = self.error_counters.get("wifi_disconnects", 0) + 1
            return False
        return True

    def choose_command_failure(self, command_type: str) -> bool:
        return "command_failure" in self.config.scenarios or self.rng.random() < self.config.command_failure_rate

    def choose_ota_failure(self) -> str | None:
        if "ota_failure" in self.config.scenarios or "ota_checksum_failure" in self.config.scenarios:
            return "checksum_mismatch"
        if "ota_download_failure" in self.config.scenarios:
            return "download_failed"
        if "ota_install_failure" in self.config.scenarios:
            return "install_failed"
        if "ota_timeout" in self.config.scenarios:
            return "timeout"
        if "ota_rollback" in self.config.scenarios:
            return "rollback"
        if self.rng.random() < self.config.ota_failure_rate:
            return self.rng.choice(["checksum_mismatch", "download_failed", "timeout"])
        return None

    def uptime_seconds(self) -> int:
        if "reboot_loop" in self.config.scenarios and int(time.monotonic() - self.boot_time_monotonic) > 25:
            self.boot_time_monotonic = time.monotonic()
            self.error_counters["reboots"] = self.error_counters.get("reboots", 0) + 1
        return max(0, int(time.monotonic() - self.boot_time_monotonic))

    def wifi_rssi_dbm(self) -> int:
        base = -67 if "unstable_wifi" in self.config.scenarios else -54
        return max(-95, min(-35, base + self.rng.randint(-8, 8)))

    def free_heap_bytes(self) -> int:
        if "low_memory" in self.config.scenarios:
            return max(32_000, 48_000 + self.rng.randint(-6_000, 4_000))
        base = 188_000 if self.config.is_master else 205_000
        return max(90_000, base + self.rng.randint(-9_000, 9_000))

    def ip_address(self) -> str:
        suffix = abs(hash(self.config.hardware_device_id)) % 180 + 40
        return f"192.168.0.{suffix}"

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.api.post_json(path, payload, token=self.config.device_token)
        except SimulatorApiError as exc:
            if path not in self.disabled_optional_paths:
                logger.debug("[%s] POST failed path=%s error=%s", self.config.hardware_device_id, path, exc)
            raise

    async def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.api.get_json(path, token=self.config.device_token, params=params)
        except SimulatorApiError as exc:
            if path not in self.disabled_optional_paths:
                logger.debug("[%s] GET failed path=%s error=%s", self.config.hardware_device_id, path, exc)
            raise

    async def _post_optional_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.api.post_json(path, payload, token=self.config.device_token)

    async def _get_optional_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return self.api.get_json(path, token=self.config.device_token, params=params)

    async def _post_multipart(
        self,
        path: str,
        *,
        fields: dict[str, Any],
        files: list[MultipartFile],
    ) -> dict[str, Any]:
        try:
            return self.api.post_multipart(path, token=self.config.device_token, fields=fields, files=files)
        except SimulatorApiError as exc:
            if path not in self.disabled_optional_paths:
                logger.debug("[%s] multipart POST failed path=%s error=%s", self.config.hardware_device_id, path, exc)
            raise


def parse_route_command_id(command_id: str) -> int | None:
    text = str(command_id or "").strip()
    if text.startswith("cmd_"):
        text = text[4:]
    return int(text) if text.isdigit() else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def legacy_command_type(target: str, action: str) -> str | None:
    if target in {"grow_light", "light"} and action in {"on", "off", "set_intensity"}:
        return "SET_GROW_LIGHT_BRIGHTNESS"
    if target == "camera" and action == "capture":
        return "CAPTURE_IMAGE"
    return None


def legacy_command_params(target: str, action: str, value: Any) -> dict[str, Any]:
    if target in {"grow_light", "light"} and action == "set_intensity":
        return {"brightness_percent": _int_percent(value, 0)}
    if target in {"grow_light", "light"} and action == "on":
        return {"brightness_percent": 100}
    if target in {"grow_light", "light"} and action == "off":
        return {"brightness_percent": 0}
    if target == "camera" and action == "capture":
        return {"reason": "manual"}
    return {"value": value}


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_int_percent(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 0 <= value <= 100:
        return value
    return None


def _int_percent(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, parsed))
