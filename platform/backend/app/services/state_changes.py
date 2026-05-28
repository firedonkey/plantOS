from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import DiagnosticSeverity, EventType
from app.models import Command
from app.models.device_diagnostic import DeviceDiagnosticEvent
from app.models.device_node import DeviceNode
from app.services.events import write_canonical_event


WIFI_DEGRADED_RSSI_DBM = -80
WIFI_RECOVERED_RSSI_DBM = -70
LOW_MEMORY_HEAP_BYTES = 32_768


def emit_heartbeat_state_changes(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    current: dict[str, Any],
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    previous = _latest_event_data(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        event_type=EventType.HEARTBEAT_RECEIVED.value,
    )
    if previous is None:
        return

    _emit_actuator_change(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        previous=previous,
        current=current,
        correlation_id=correlation_id,
        occurred_at=occurred_at,
    )
    _emit_camera_node_change(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        previous=previous,
        current=current,
        correlation_id=correlation_id,
        occurred_at=occurred_at,
    )
    _emit_ota_state_change(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        previous_status=_runtime_value(previous, "ota_status"),
        current_status=_runtime_value(current, "ota_status"),
        source="heartbeat",
        correlation_id=correlation_id,
        occurred_at=occurred_at,
    )
    _emit_device_health_change(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        previous=_string(previous.get("node_status")),
        current=_string(current.get("node_status")),
        source="heartbeat",
        correlation_id=correlation_id,
        occurred_at=occurred_at,
    )
    _emit_wifi_signal_change(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        previous=_int(previous.get("wifi_rssi_dbm")),
        current=_int(current.get("wifi_rssi_dbm")),
        correlation_id=correlation_id,
        occurred_at=occurred_at,
    )


def emit_diagnostics_state_changes(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    current: dict[str, Any],
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    previous = _latest_event_data(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        event_type=EventType.DIAGNOSTICS_RECEIVED.value,
    )
    if previous is None:
        return

    previous_health = _diagnostics_health(previous)
    current_health = _diagnostics_health(current)
    if previous_health == current_health:
        return
    write_canonical_event(
        session,
        event_type=EventType.DEVICE_HEALTH_CHANGED,
        severity=_health_event_severity(current_health.get("status"), current_health.get("severity")),
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data={
            "source": "diagnostics",
            "previous": previous_health,
            "current": current_health,
        },
        occurred_at=occurred_at,
    )


def emit_ota_state_change(
    session: Session,
    *,
    node: DeviceNode,
    previous_status: str | None,
    current_status: str | None,
    correlation_id: str | None,
    data: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> None:
    _emit_ota_state_change(
        session,
        device_id=node.device_id,
        hardware_device_id=node.hardware_device_id,
        node_role=node.node_role,
        previous_status=previous_status,
        current_status=current_status,
        source="ota_status",
        correlation_id=correlation_id,
        occurred_at=occurred_at,
        extra=data,
    )


def emit_command_actuator_state_change(
    session: Session,
    *,
    command: Command,
    previous: dict[str, Any],
    current: dict[str, Any],
    occurred_at: datetime | None,
) -> None:
    previous_state = _clean_ambient_light(previous)
    current_state = _clean_ambient_light(current)
    if previous_state == current_state:
        return
    target_node = _target_node_for_command(session, command)
    if target_node is None:
        return
    write_canonical_event(
        session,
        event_type=EventType.ACTUATOR_STATE_CHANGED,
        severity=DiagnosticSeverity.INFO,
        device_id=command.device_id,
        hardware_device_id=target_node.hardware_device_id,
        node_role=target_node.node_role,
        correlation_id=f"cmd_{command.id}",
        data={
            "source": "command_result",
            "actuator": "ambient_light",
            "previous": previous_state,
            "current": current_state,
        },
        occurred_at=occurred_at,
    )


def _emit_actuator_change(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    previous_state = _clean_ambient_light((previous.get("actuators") or {}).get("ambient_light"))
    current_state = _clean_ambient_light((current.get("actuators") or {}).get("ambient_light"))
    if previous_state == current_state:
        return
    if not previous_state and not current_state:
        return
    write_canonical_event(
        session,
        event_type=EventType.ACTUATOR_STATE_CHANGED,
        severity=DiagnosticSeverity.INFO,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data={
            "source": "heartbeat",
            "actuator": "ambient_light",
            "previous": previous_state,
            "current": current_state,
        },
        occurred_at=occurred_at,
    )


def _emit_camera_node_change(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    previous_status = _runtime_value(previous, "camera_node_status")
    current_status = _runtime_value(current, "camera_node_status")
    if not previous_status or not current_status or previous_status == current_status:
        return
    if previous_status == "online" and current_status == "offline":
        event_type = EventType.CAMERA_NODE_DISCONNECTED
        severity = DiagnosticSeverity.WARNING
    elif previous_status == "offline" and current_status == "online":
        event_type = EventType.CAMERA_NODE_CONNECTED
        severity = DiagnosticSeverity.INFO
    else:
        return
    write_canonical_event(
        session,
        event_type=event_type,
        severity=severity,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data={
            "source": "heartbeat",
            "previous": previous_status,
            "current": current_status,
        },
        occurred_at=occurred_at,
    )


def _emit_ota_state_change(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    previous_status: str | None,
    current_status: str | None,
    source: str,
    correlation_id: str | None,
    occurred_at: datetime | None,
    extra: dict[str, Any] | None = None,
) -> None:
    if not previous_status or not current_status or previous_status == current_status:
        return
    latest = _latest_event_data(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        event_type=EventType.OTA_STATE_CHANGED.value,
    )
    if _string((latest or {}).get("current")) == current_status:
        return
    payload = {
        "source": source,
        "previous": previous_status,
        "current": current_status,
    }
    if extra:
        payload.update(extra)
    write_canonical_event(
        session,
        event_type=EventType.OTA_STATE_CHANGED,
        severity=DiagnosticSeverity.WARNING if current_status in {"failed", "rolled_back"} else DiagnosticSeverity.INFO,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data=payload,
        occurred_at=occurred_at,
    )


def _emit_device_health_change(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    previous: str | None,
    current: str | None,
    source: str,
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    if not previous or not current or previous == current:
        return
    write_canonical_event(
        session,
        event_type=EventType.DEVICE_HEALTH_CHANGED,
        severity=_health_event_severity(current, None),
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data={
            "source": source,
            "previous": previous,
            "current": current,
        },
        occurred_at=occurred_at,
    )


def _emit_wifi_signal_change(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    previous: int | None,
    current: int | None,
    correlation_id: str | None,
    occurred_at: datetime | None,
) -> None:
    if previous is None or current is None:
        return
    latest_signal_event = _latest_wifi_signal_event_type(
        session,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
    )
    payload = {
        "previous": previous,
        "current": current,
        "thresholds": {
            "degraded_dbm": WIFI_DEGRADED_RSSI_DBM,
            "recovered_dbm": WIFI_RECOVERED_RSSI_DBM,
        },
    }
    if (
        current <= WIFI_DEGRADED_RSSI_DBM
        and latest_signal_event != EventType.WIFI_SIGNAL_DEGRADED.value
        and previous > WIFI_DEGRADED_RSSI_DBM
    ):
        write_canonical_event(
            session,
            event_type=EventType.WIFI_SIGNAL_DEGRADED,
            severity=DiagnosticSeverity.WARNING,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role=node_role,
            correlation_id=correlation_id,
            data=payload,
            occurred_at=occurred_at,
        )
    elif current >= WIFI_RECOVERED_RSSI_DBM and latest_signal_event == EventType.WIFI_SIGNAL_DEGRADED.value:
        write_canonical_event(
            session,
            event_type=EventType.WIFI_SIGNAL_RECOVERED,
            severity=DiagnosticSeverity.INFO,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role=node_role,
            correlation_id=correlation_id,
            data=payload,
            occurred_at=occurred_at,
        )


def _latest_event_data(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    event_type: str,
) -> dict[str, Any] | None:
    event = session.scalar(
        select(DeviceDiagnosticEvent)
        .where(DeviceDiagnosticEvent.device_id == device_id)
        .where(DeviceDiagnosticEvent.hardware_device_id == hardware_device_id)
        .where(DeviceDiagnosticEvent.event_type == event_type)
        .order_by(DeviceDiagnosticEvent.occurred_at.desc(), DeviceDiagnosticEvent.id.desc())
        .limit(1)
    )
    if event is None:
        return None
    metadata = event.metadata_json or {}
    data = metadata.get("data")
    return data if isinstance(data, dict) else metadata


def _latest_wifi_signal_event_type(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
) -> str | None:
    event = session.scalar(
        select(DeviceDiagnosticEvent)
        .where(DeviceDiagnosticEvent.device_id == device_id)
        .where(DeviceDiagnosticEvent.hardware_device_id == hardware_device_id)
        .where(
            DeviceDiagnosticEvent.event_type.in_(
                [
                    EventType.WIFI_SIGNAL_DEGRADED.value,
                    EventType.WIFI_SIGNAL_RECOVERED.value,
                ]
            )
        )
        .order_by(DeviceDiagnosticEvent.occurred_at.desc(), DeviceDiagnosticEvent.id.desc())
        .limit(1)
    )
    return event.event_type if event is not None else None


def _diagnostics_health(data: dict[str, Any]) -> dict[str, str | None]:
    return {
        "status": _string(data.get("status")),
        "severity": _string(data.get("severity")),
    }


def _health_event_severity(status: str | None, severity: str | None) -> DiagnosticSeverity:
    if severity == "critical" or status == "error":
        return DiagnosticSeverity.CRITICAL
    if severity == "warning" or status in {"degraded", "offline"}:
        return DiagnosticSeverity.WARNING
    return DiagnosticSeverity.INFO


def _runtime_value(payload: dict[str, Any], key: str) -> str | None:
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        return None
    return _string(runtime.get(key))


def _clean_ambient_light(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, Any] = {}
    if isinstance(value.get("enabled"), bool):
        cleaned["enabled"] = value["enabled"]
    brightness = _int(value.get("brightness_percent"))
    if brightness is not None and 0 <= brightness <= 100:
        cleaned["brightness_percent"] = brightness
    return cleaned


def _target_node_for_command(session: Session, command: Command) -> DeviceNode | None:
    roles = ("master", "single_board")
    return session.scalar(
        select(DeviceNode)
        .where(DeviceNode.device_id == command.device_id)
        .where(DeviceNode.node_role.in_(roles))
        .order_by(DeviceNode.node_index, DeviceNode.hardware_device_id)
        .limit(1)
    )


def _string(value: Any) -> str | None:
    text = str(value).strip().lower() if value is not None else ""
    return text or None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
