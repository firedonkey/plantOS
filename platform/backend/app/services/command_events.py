from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import CommandPayload, CommandTarget, CommandTargetRole, CommandType, DiagnosticSeverity, EventType
from app.models import Command, CommandStatus
from app.models.device_diagnostic import DeviceDiagnosticEvent
from app.models.device_node import DeviceNode


def contract_command_id(command: Command) -> str:
    return f"cmd_{command.id}"


def parse_contract_command_id(value: str) -> int | None:
    text = str(value or "").strip()
    if text.startswith("cmd_"):
        text = text[4:]
    return int(text) if text.isdigit() else None


def build_command_payload(session: Session, command: Command) -> CommandPayload | None:
    command_type = _command_type(command)
    if command_type is None:
        return None
    target_node = _target_node(session, command)
    target_role = _target_role(command)
    return CommandPayload(
        command_id=contract_command_id(command),
        command_type=command_type,
        target=CommandTarget(
            node_role=target_role,
            hardware_device_id=target_node.hardware_device_id if target_node is not None else None,
            camera_role=_camera_role(command),
        ),
        params=_command_params(command),
        timeout_ms=_timeout_ms(command),
        priority="normal",
        scheduled_for=None,
    )


def add_command_event(
    session: Session,
    command: Command,
    *,
    event_type: EventType,
    status: str,
    correlation_id: str | None = None,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
    occurred_at: datetime | None = None,
) -> DeviceDiagnosticEvent:
    target_node = _target_node(session, command)
    payload = build_command_payload(session, command)
    command_type = payload.command_type.value if payload is not None else _legacy_command_type(command)
    target_role = (
        payload.target.node_role.value
        if payload is not None
        else _target_role(command).value
    )
    target_hardware_device_id = payload.target.hardware_device_id if payload is not None else None
    event_time = occurred_at or datetime.now(timezone.utc)
    event = DeviceDiagnosticEvent(
        device_id=command.device_id,
        hardware_device_id=target_node.hardware_device_id if target_node is not None else None,
        event_type=event_type.value,
        severity=_event_severity(event_type).value,
        code=error_code or event_type.value,
        message=_event_message(event_type),
        metadata_json={
            "schema_version": "1.0",
            "correlation_id": correlation_id or contract_command_id(command),
            "command_id": contract_command_id(command),
            "legacy_command_id": command.id,
            "command_type": command_type,
            "target_node_role": target_role,
            "target_hardware_device_id": target_hardware_device_id,
            "status": status,
            "params": payload.params if payload is not None else {"target": _value(command.target), "action": _value(command.action), "value": command.value},
            "result": result or {},
        },
        occurred_at=event_time,
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    return event


def event_type_for_result_status(status: str) -> EventType:
    normalized = str(status or "").strip().lower()
    if normalized == "completed":
        return EventType.COMMAND_COMPLETED
    if normalized == "failed":
        return EventType.COMMAND_FAILED
    if normalized == "timed_out":
        return EventType.COMMAND_TIMED_OUT
    if normalized == "rejected":
        return EventType.COMMAND_REJECTED
    if normalized == "acked":
        return EventType.COMMAND_ACKED
    return EventType.COMMAND_IN_PROGRESS


def _command_type(command: Command) -> CommandType | None:
    target = _value(command.target)
    action = _value(command.action)
    if target in {"grow_light", "light"} and action in {"on", "off", "set_intensity", "set_channel_intensity"}:
        return CommandType.SET_GROW_LIGHT_BRIGHTNESS
    if target == "ambient_led_belt" and action == "set":
        return CommandType.SET_AMBIENT_LED_BELT
    if target == "camera" and action == "capture":
        return CommandType.CAPTURE_IMAGE
    if target == "ota" and action == "start":
        return CommandType.START_OTA
    if target == "diagnostics" and action == "request":
        return CommandType.REQUEST_DIAGNOSTICS
    if target == "system" and action == "reboot":
        return CommandType.REBOOT
    return None


def _legacy_command_type(command: Command) -> str:
    return f"LEGACY_{_value(command.target).upper()}_{_value(command.action).upper()}"


def _command_params(command: Command) -> dict[str, Any]:
    target = _value(command.target)
    action = _value(command.action)
    if target in {"grow_light", "light"} and action == "set_intensity":
        try:
            brightness = int(command.value or 0)
        except ValueError:
            brightness = 0
        return {"brightness_percent": max(0, min(100, brightness))}
    if target in {"grow_light", "light"} and action == "set_channel_intensity":
        params = _json_command_value(command.value)
        if not isinstance(params, dict):
            return {"brightness_percent": 0}
        channel = str(params.get("channel") or "").strip().lower()
        try:
            brightness = int(params.get("brightness_percent") or 0)
        except (TypeError, ValueError):
            brightness = 0
        payload = {"brightness_percent": max(0, min(100, brightness))}
        if channel in {"red", "white"}:
            payload["channel"] = channel
        return payload
    if target in {"grow_light", "light"} and action == "on":
        return {"brightness_percent": 100}
    if target in {"grow_light", "light"} and action == "off":
        return {"brightness_percent": 0}
    if target == "ambient_led_belt" and action == "set":
        params = _json_command_value(command.value)
        return params if isinstance(params, dict) else {}
    if target == "camera" and action == "capture":
        params = {"reason": "manual"}
        capture_params = _json_command_value(command.value)
        if isinstance(capture_params, dict):
            params.update(capture_params)
        return params
    if target == "ota" and action == "start":
        return _ota_command_params(command.value)
    if target == "diagnostics" and action == "request":
        return {"reason": command.value or "manual"}
    if target == "system" and action == "reboot":
        return {"reason": command.value or "manual"}
    return {"value": command.value}


def _target_role(command: Command) -> CommandTargetRole:
    return CommandTargetRole.CAMERA if _value(command.target) == "camera" else CommandTargetRole.MASTER


def _target_node(session: Session, command: Command) -> DeviceNode | None:
    target_role = _target_role(command).value
    roles = ("camera",) if target_role == "camera" else ("master", "single_board")
    if target_role == "camera" and _camera_role_is_all(command):
        return None
    query = (
        select(DeviceNode)
        .where(DeviceNode.device_id == command.device_id)
        .where(DeviceNode.node_role.in_(roles))
    )
    camera_role = _camera_role(command)
    if target_role == "camera" and camera_role is not None:
        if camera_role == "top":
            query = query.where((DeviceNode.camera_role == camera_role) | (DeviceNode.camera_role.is_(None)))
        else:
            query = query.where(DeviceNode.camera_role == camera_role)
    return session.scalar(query.order_by(DeviceNode.node_index, DeviceNode.hardware_device_id).limit(1))


def _timeout_ms(command: Command) -> int:
    if _value(command.target) == "camera" and _value(command.action) == "capture":
        return 150_000
    if _value(command.target) == "ota" and _value(command.action) == "start":
        return 1_800_000
    if _value(command.target) == "system" and _value(command.action) == "reboot":
        return 60_000
    return 20_000


def _ota_command_params(value: str | None) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"target_version": text}
        return parsed if isinstance(parsed, dict) else {"target_version": text}
    return {"target_version": text}


def _camera_role(command: Command) -> str | None:
    if _value(command.target) != "camera":
        return None
    params = _json_command_value(command.value)
    if not isinstance(params, dict):
        return None
    role = str(params.get("camera_role") or "").strip().lower()
    if role in {"top", "side"}:
        return role
    return None


def _camera_role_is_all(command: Command) -> bool:
    if _value(command.target) != "camera":
        return False
    params = _json_command_value(command.value)
    if not isinstance(params, dict):
        return False
    return str(params.get("camera_role") or "").strip().lower() == "all"


def _json_command_value(value: str | None) -> Any:
    text = str(value or "").strip()
    if not text.startswith("{"):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _event_severity(event_type: EventType) -> DiagnosticSeverity:
    if event_type in {EventType.COMMAND_FAILED, EventType.COMMAND_TIMED_OUT, EventType.COMMAND_REJECTED}:
        return DiagnosticSeverity.WARNING
    return DiagnosticSeverity.INFO


def _event_message(event_type: EventType) -> str:
    return event_type.value.replace("_", " ").title()


def _value(value) -> str:
    return str(getattr(value, "value", value) or "").strip().lower()
