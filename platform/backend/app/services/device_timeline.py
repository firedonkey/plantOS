from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.device_diagnostic import DeviceDiagnosticEvent
from app.schemas.diagnostics import DeviceTimelineEventRead


def list_timeline_events(
    session: Session,
    device_id: int,
    *,
    limit: int = 50,
    before: datetime | None = None,
    after: datetime | None = None,
    event_types: list[str] | None = None,
    severities: list[str] | None = None,
    node_role: str | None = None,
    correlation_id: str | None = None,
) -> list[DeviceDiagnosticEvent]:
    safe_limit = min(max(limit, 1), 100)
    statement = select(DeviceDiagnosticEvent).where(DeviceDiagnosticEvent.device_id == device_id)
    if before is not None:
        statement = statement.where(DeviceDiagnosticEvent.occurred_at < before)
    if after is not None:
        statement = statement.where(DeviceDiagnosticEvent.occurred_at >= after)
    if event_types:
        statement = statement.where(DeviceDiagnosticEvent.event_type.in_([_normalize_filter(value) for value in event_types]))
    if severities:
        statement = statement.where(DeviceDiagnosticEvent.severity.in_([_normalize_filter(value) for value in severities]))
    if node_role:
        normalized_node_role = _normalize_filter(node_role)
        statement = statement.where(
            or_(
                DeviceDiagnosticEvent.metadata_json["node_role"].as_string() == normalized_node_role,
                DeviceDiagnosticEvent.metadata_json["target_node_role"].as_string() == normalized_node_role,
            )
        )
    if correlation_id:
        statement = statement.where(DeviceDiagnosticEvent.metadata_json["correlation_id"].as_string() == correlation_id.strip())
    statement = statement.order_by(DeviceDiagnosticEvent.occurred_at.desc(), DeviceDiagnosticEvent.id.desc()).limit(safe_limit)
    return list(session.scalars(statement))


def timeline_event_read(event: DeviceDiagnosticEvent) -> DeviceTimelineEventRead:
    metadata = event.metadata_json or {}
    data = _event_data(metadata)
    node_role = _string(metadata.get("node_role")) or _string(data.get("node_role")) or _string(metadata.get("target_node_role"))
    correlation_id = _string(metadata.get("correlation_id")) or _string(data.get("command_id"))
    return DeviceTimelineEventRead(
        id=int(event.id or 0),
        event_type=event.event_type,
        severity=event.severity,
        occurred_at=event.occurred_at,
        hardware_device_id=event.hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        summary=summarize_timeline_event(event),
        code=event.code,
        message=event.message,
        data=_compact_json(data),
        created_at=event.created_at,
    )


def summarize_timeline_event(event: DeviceDiagnosticEvent) -> str:
    metadata = event.metadata_json or {}
    data = _event_data(metadata)
    event_type = str(event.event_type or "").strip().upper()
    command_type = _string(metadata.get("command_type")) or _string(data.get("command_type"))
    status = _string(metadata.get("status")) or _string(data.get("status"))

    if event_type == "HEARTBEAT_RECEIVED":
        rssi = data.get("wifi_rssi_dbm")
        if isinstance(rssi, int):
            return f"Heartbeat received (RSSI {rssi} dBm)"
        return "Heartbeat received"

    if event_type == "COMMAND_POLL_STALE":
        stale_seconds = data.get("current_stale_seconds")
        if isinstance(stale_seconds, int):
            return f"Command polling stale for {stale_seconds}s"
        return "Command polling stale"

    if event_type.startswith("COMMAND_"):
        label = command_type or _string(metadata.get("command_id")) or "Command"
        target = _string(metadata.get("target_node_role")) or _string(metadata.get("node_role"))
        suffix = f" to {target} node" if target and event_type in {"COMMAND_SENT", "COMMAND_POLLED"} else ""
        action = {
            "COMMAND_QUEUED": "queued",
            "COMMAND_POLLED": "polled",
            "COMMAND_SENT": "sent",
            "COMMAND_ACKED": "acknowledged",
            "COMMAND_IN_PROGRESS": "in progress",
            "COMMAND_COMPLETED": "completed",
            "COMMAND_FAILED": "failed",
            "COMMAND_TIMED_OUT": "timed out",
            "COMMAND_REJECTED": "rejected",
        }.get(event_type, _humanize(event_type))
        if event_type in {"COMMAND_FAILED", "COMMAND_TIMED_OUT", "COMMAND_REJECTED"}:
            reason = _string(metadata.get("error_code")) or _string(event.code)
            return f"{label} {action}: {_humanize(reason)}" if reason else f"{label} {action}"
        return f"{label} {action}{suffix}"

    if event_type.startswith("OTA_"):
        progress = data.get("progress_percent")
        target_version = _string(data.get("target_version"))
        if event_type == "OTA_DOWNLOADING" and isinstance(progress, int):
            return f"OTA downloading {progress}%"
        if event_type == "OTA_INSTALLING":
            return "OTA installing"
        if event_type == "OTA_SUCCESS":
            return f"OTA success{f' to {target_version}' if target_version else ''}"
        if event_type == "OTA_FAILED":
            reason = _string(data.get("failure_reason")) or _string(event.code)
            return f"OTA failed: {_humanize(reason)}" if reason else "OTA failed"
        return _humanize(event_type)

    if event_type == "CAMERA_NODE_DISCONNECTED":
        return "Camera node disconnected"
    if event_type == "CAMERA_NODE_CONNECTED":
        return "Camera node connected"
    if event_type == "ACTUATOR_STATE_CHANGED":
        actuator = _humanize(_string(data.get("actuator")) or "actuator")
        previous = _grow_light_label(data.get("previous"))
        current = _grow_light_label(data.get("current"))
        if actuator in {"grow light", "ambient light"}:
            return f"Grow light changed: {previous} -> {current}"
        return f"{actuator.title()} changed: {previous} -> {current}"
    if event_type == "OTA_STATE_CHANGED":
        previous = _string(data.get("previous")) or "unknown"
        current = _string(data.get("current")) or "unknown"
        return f"OTA state changed: {_humanize(previous)} -> {_humanize(current)}"
    if event_type == "DEVICE_HEALTH_CHANGED":
        previous = _health_label(data.get("previous"))
        current = _health_label(data.get("current"))
        return f"Device health changed: {previous} -> {current}"
    if event_type == "WIFI_SIGNAL_DEGRADED":
        previous = data.get("previous")
        current = data.get("current")
        if isinstance(previous, int) and isinstance(current, int):
            return f"Wi-Fi signal degraded: {previous} -> {current} dBm"
        return "Wi-Fi signal degraded"
    if event_type == "WIFI_SIGNAL_RECOVERED":
        previous = data.get("previous")
        current = data.get("current")
        if isinstance(previous, int) and isinstance(current, int):
            return f"Wi-Fi signal recovered: {previous} -> {current} dBm"
        return "Wi-Fi signal recovered"
    if event_type == "DIAGNOSTICS_RECEIVED":
        severity = _string(data.get("severity")) or _string(event.severity)
        return f"Diagnostics received ({_humanize(severity)})" if severity else "Diagnostics received"
    if event_type == "PROVISIONING_STARTED":
        return "Provisioning started"
    if event_type == "PROVISIONING_SUCCESS":
        return "Provisioning completed"
    if event_type == "PROVISIONING_FAILED":
        reason = _string(data.get("failure_reason")) or _string(event.code)
        return f"Provisioning failed: {_humanize(reason)}" if reason else "Provisioning failed"
    if event_type == "IMAGE_CAPTURE_STARTED":
        return "Image capture started"
    if event_type == "IMAGE_CAPTURED":
        image_id = data.get("image_id")
        return f"Image captured #{image_id}" if isinstance(image_id, int) else "Image captured"
    if event_type == "IMAGE_UPLOAD_STARTED":
        return "Image upload started"
    if event_type == "IMAGE_UPLOADED":
        image_id = data.get("image_id")
        reason = _string(data.get("upload_reason"))
        if isinstance(image_id, int) and reason:
            return f"Image uploaded #{image_id} ({_humanize(reason)})"
        if isinstance(image_id, int):
            return f"Image uploaded #{image_id}"
        return "Image uploaded"
    if event_type == "IMAGE_UPLOAD_FAILED":
        reason = _string(data.get("failure_reason")) or _string(event.code)
        return f"Image upload failed: {_humanize(reason)}" if reason else "Image upload failed"
    if event_type == "DEVICE_ONLINE":
        return "Device online"
    if event_type == "DEVICE_OFFLINE":
        return "Device offline"

    return _string(event.message) or _humanize(event_type)


def _event_data(metadata: dict[str, Any]) -> dict[str, Any]:
    data = metadata.get("data")
    if isinstance(data, dict):
        return data
    return metadata


def _compact_json(value: Any, *, depth: int = 0) -> Any:
    if depth >= 5:
        return _truncate(value)
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 80:
                compact["truncated"] = True
                break
            compact[str(key)] = _compact_json(item, depth=depth + 1)
        return compact
    if isinstance(value, list):
        return [_compact_json(item, depth=depth + 1) for item in value[:80]]
    return _truncate(value)


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "..."
    return value


def _normalize_filter(value: str) -> str:
    return str(value or "").strip()


def _string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _grow_light_label(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "unknown"
    enabled = value.get("enabled")
    brightness = value.get("brightness_percent")
    if enabled is False:
        return "off"
    if enabled is True and isinstance(brightness, int):
        return f"{brightness}%"
    if enabled is True:
        return "on"
    if isinstance(brightness, int):
        return f"{brightness}%"
    return "unknown"


def _health_label(value: Any) -> str:
    if isinstance(value, dict):
        status = _string(value.get("status"))
        severity = _string(value.get("severity"))
        if status and severity:
            return f"{_humanize(status)} ({_humanize(severity)})"
        if status:
            return _humanize(status)
        if severity:
            return _humanize(severity)
        return "unknown"
    return _humanize(_string(value) or "unknown")


def _humanize(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown event"
    return text.replace("_", " ").lower()
