from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OtaOutcome:
    success: bool
    message: str
    error_code: str | None = None
    rejected: bool = False


class OtaSimulator:
    async def run(self, node, command: dict[str, Any]) -> OtaOutcome:
        payload = command.get("payload") or {}
        params = payload.get("params") or {}
        command_id = str(payload.get("command_id") or "")
        target_version = str(params.get("target_version") or "").strip()
        download_url = str(params.get("download_url") or "").strip()
        channel = str(params.get("firmware_channel") or "stable")
        release_id = params.get("release_id")

        if not target_version:
            return OtaOutcome(False, "START_OTA missing target_version.", "INVALID_PARAMS", rejected=True)
        if not download_url:
            return OtaOutcome(False, "START_OTA missing download_url.", "INVALID_PARAMS", rejected=True)
        hardware_model = params.get("hardware_model")
        if hardware_model and hardware_model != node.config.hardware_model:
            return OtaOutcome(False, "START_OTA hardware_model is not supported by this node.", "UNSUPPORTED_TARGET", rejected=True)
        if node.ota_status not in {"idle", "success", "failed", "rolled_back"}:
            return OtaOutcome(False, "OTA already running.", "DEVICE_BUSY", rejected=True)

        await node.send_command_result(command, "in_progress", "OTA accepted.")
        failure = node.choose_ota_failure()
        if failure == "download_failed":
            await self._status(node, command_id, "preparing", 5, target_version, channel, "prepare", "Preparing OTA.", release_id=release_id)
            await self._sleep(node)
            await self._status(
                node,
                command_id,
                "failed",
                22,
                target_version,
                channel,
                "download",
                "OTA download failed.",
                failure_reason="download_failed",
                release_id=release_id,
            )
            return OtaOutcome(False, "OTA download failed.", "TRANSPORT_ERROR")
        if failure == "timeout":
            await self._status(node, command_id, "downloading", 36, target_version, channel, "download", "OTA download stalled.", release_id=release_id)
            await self._sleep(node)
            await self._status(
                node,
                command_id,
                "failed",
                36,
                target_version,
                channel,
                "download",
                "OTA timed out.",
                failure_reason="timeout",
                release_id=release_id,
            )
            return OtaOutcome(False, "OTA timed out.", "TIMEOUT")

        steps = [
            ("preparing", 5, "prepare", "Preparing OTA."),
            ("downloading", 25, "download", "Downloading firmware."),
            ("downloading", 62, "download", "Downloading firmware."),
            ("validating", 78, "validate", "Validating firmware."),
            ("installing", 92, "install", "Installing firmware."),
            ("rebooting", 98, "reboot", "Rebooting into new firmware."),
        ]
        for status, progress, phase, message in steps:
            await self._status(node, command_id, status, progress, target_version, channel, phase, message, release_id=release_id)
            await self._sleep(node)
            if failure == "checksum_mismatch" and status == "validating":
                await self._status(
                    node,
                    command_id,
                    "failed",
                    progress,
                    target_version,
                    channel,
                    phase,
                    "Firmware checksum validation failed.",
                    failure_reason="checksum_mismatch",
                    release_id=release_id,
                )
                return OtaOutcome(False, "Firmware checksum validation failed.", "INTERNAL_ERROR")
            if failure == "rollback" and status == "installing":
                await self._status(
                    node,
                    command_id,
                    "rolled_back",
                    progress,
                    target_version,
                    channel,
                    "rollback",
                    "OTA rolled back to previous firmware.",
                    failure_reason="rollback_failed",
                    release_id=release_id,
                )
                return OtaOutcome(False, "OTA rolled back.", "INTERNAL_ERROR")
            if failure == "install_failed" and status == "installing":
                await self._status(
                    node,
                    command_id,
                    "failed",
                    progress,
                    target_version,
                    channel,
                    phase,
                    "OTA install failed.",
                    failure_reason="install_failed",
                    release_id=release_id,
                )
                return OtaOutcome(False, "OTA install failed.", "INTERNAL_ERROR")

        node.config.firmware_version = target_version
        await self._status(node, command_id, "success", 100, target_version, channel, "completed", "OTA completed successfully.", release_id=release_id)
        return OtaOutcome(True, "OTA completed successfully.")

    async def _status(
        self,
        node,
        command_id: str,
        status: str,
        progress: int,
        target_version: str,
        channel: str,
        phase: str,
        message: str,
        *,
        failure_reason: str | None = None,
        release_id: str | None = None,
    ) -> None:
        await node.send_ota_status(
            command_id=command_id,
            status=status,
            progress_percent=progress,
            target_version=target_version,
            firmware_channel=channel,
            phase=phase,
            message=message,
            failure_reason=failure_reason,
            release_id=release_id,
        )

    async def _sleep(self, node) -> None:
        delay = max(0.0, node.config.ota_step_delay_seconds)
        if delay:
            await asyncio.sleep(delay)
