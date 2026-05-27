from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.device_diagnostic import DeviceDiagnosticEvent, DeviceDiagnosticSnapshot
from app.models.device_node import DeviceNode
from app.schemas.diagnostics import DeviceDiagnosticEventRead, DeviceDiagnosticSnapshotRead, HardwareDiagnosticsCreate

EVENT_RETENTION_DAYS = 30
EVENT_RETENTION_LIMIT = 100
EVENT_TYPE_BY_COUNTER = {
    "wifi_reconnects": "wifi_reconnect",
    "upload_failures": "upload_failure",
    "ble_provisioning_failures": "ble_provisioning_failure",
    "espnow_failures": "espnow_failure",
}


def upsert_diagnostic_snapshot(
    session: Session,
    *,
    device_id: int,
    node: DeviceNode,
    status: str,
    diagnostics: HardwareDiagnosticsCreate,
    reported_at: datetime | None = None,
) -> DeviceDiagnosticSnapshot:
    now = reported_at or datetime.now(timezone.utc)
    previous = session.get(DeviceDiagnosticSnapshot, node.hardware_device_id)
    previous_counters = dict(previous.error_counters or {}) if previous is not None else {}
    previous_last_error_code = previous.last_error_code if previous is not None else None
    previous_uptime_seconds = previous.uptime_seconds if previous is not None else None
    had_previous = previous is not None

    snapshot = previous or DeviceDiagnosticSnapshot(
        hardware_device_id=node.hardware_device_id,
        device_id=device_id,
    )
    session.add(snapshot)

    last_command = getattr(diagnostics, "last_command", None)
    last_error = getattr(diagnostics, "last_error", None)
    snapshot.device_id = device_id
    snapshot.node_role = node.node_role
    snapshot.schema_version = int(getattr(diagnostics, "schema_version", 1) or 1)
    snapshot.reported_status = _clean_text(status, 40)
    snapshot.firmware_version = _clean_text(node.software_version, 120)
    snapshot.uptime_seconds = getattr(diagnostics, "uptime_seconds", None)
    snapshot.wifi_rssi_dbm = getattr(diagnostics, "wifi_rssi_dbm", None)
    snapshot.reboot_reason = _clean_text(getattr(diagnostics, "reboot_reason", None), 80)
    snapshot.provisioning_state = _clean_text(getattr(diagnostics, "provisioning_state", None), 80)
    snapshot.last_sensor_reading_at = _timestamp_from_age(now, getattr(diagnostics, "last_sensor_reading_age_seconds", None))
    snapshot.last_camera_image_upload_at = _timestamp_from_age(now, getattr(diagnostics, "last_camera_image_upload_age_seconds", None))
    snapshot.last_command_id = last_command.id if last_command else None
    snapshot.last_command_status = _clean_text(last_command.status if last_command else None, 40)
    snapshot.last_command_code = _clean_text(last_command.code if last_command else None, 80)
    snapshot.last_command_message = _clean_text(last_command.message if last_command else None, 160)
    snapshot.last_command_at = _timestamp_from_age(now, last_command.age_seconds if last_command else None)
    snapshot.error_counters = dict(diagnostics.error_counters or {})
    snapshot.last_error_code = _clean_text(last_error.code if last_error else None, 80)
    snapshot.last_error_message = _clean_text(last_error.message if last_error else None, 160)
    snapshot.reported_at = now
    snapshot.updated_at = now

    _create_transition_events(
        session,
        device_id=device_id,
        hardware_device_id=node.hardware_device_id,
        had_previous=had_previous,
        previous_counters=previous_counters,
        previous_last_error_code=previous_last_error_code,
        previous_uptime_seconds=previous_uptime_seconds,
        snapshot=snapshot,
        occurred_at=now,
    )
    session.commit()
    session.refresh(snapshot)
    return snapshot


def list_diagnostic_snapshots(session: Session, device_id: int) -> list[DeviceDiagnosticSnapshot]:
    return list(
        session.scalars(
            select(DeviceDiagnosticSnapshot)
            .where(DeviceDiagnosticSnapshot.device_id == device_id)
            .order_by(DeviceDiagnosticSnapshot.node_role, DeviceDiagnosticSnapshot.hardware_device_id)
        )
    )


def list_diagnostic_events(session: Session, device_id: int, *, limit: int = 20) -> list[DeviceDiagnosticEvent]:
    safe_limit = min(max(limit, 1), 100)
    return list(
        session.scalars(
            select(DeviceDiagnosticEvent)
            .where(DeviceDiagnosticEvent.device_id == device_id)
            .order_by(DeviceDiagnosticEvent.created_at.desc(), DeviceDiagnosticEvent.id.desc())
            .limit(safe_limit)
        )
    )


def snapshot_read(snapshot: DeviceDiagnosticSnapshot | None) -> DeviceDiagnosticSnapshotRead | None:
    if snapshot is None:
        return None
    return DeviceDiagnosticSnapshotRead.model_validate(snapshot)


def event_read(event: DeviceDiagnosticEvent) -> DeviceDiagnosticEventRead:
    return DeviceDiagnosticEventRead(
        id=event.id,
        device_id=event.device_id,
        hardware_device_id=event.hardware_device_id,
        event_type=event.event_type,
        severity=event.severity,
        code=event.code,
        message=event.message,
        count=event.count,
        metadata_json=event.metadata_json or {},
        occurred_at=event.occurred_at,
        created_at=event.created_at,
    )


def _create_transition_events(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    had_previous: bool,
    previous_counters: dict,
    previous_last_error_code: str | None,
    previous_uptime_seconds: int | None,
    snapshot: DeviceDiagnosticSnapshot,
    occurred_at: datetime,
) -> None:
    for key, value in (snapshot.error_counters or {}).items():
        previous_value = int(previous_counters.get(key) or 0)
        if value > previous_value:
            session.add(
                DeviceDiagnosticEvent(
                    device_id=device_id,
                    hardware_device_id=hardware_device_id,
                    event_type=EVENT_TYPE_BY_COUNTER.get(key, key),
                    severity="warning",
                    code=key,
                    message=f"{key} increased",
                    count=value,
                    occurred_at=occurred_at,
                    created_at=occurred_at,
                )
            )

    if snapshot.last_error_code and (not had_previous or previous_last_error_code != snapshot.last_error_code):
        session.add(
            DeviceDiagnosticEvent(
                device_id=device_id,
                hardware_device_id=hardware_device_id,
                event_type="last_error",
                severity="error",
                code=snapshot.last_error_code,
                message=snapshot.last_error_message,
                occurred_at=occurred_at,
                created_at=occurred_at,
            )
        )

    if (
        had_previous
        and snapshot.reboot_reason
        and snapshot.uptime_seconds is not None
        and previous_uptime_seconds is not None
        and snapshot.uptime_seconds < previous_uptime_seconds
    ):
        session.add(
            DeviceDiagnosticEvent(
                device_id=device_id,
                hardware_device_id=hardware_device_id,
                event_type="reboot",
                severity="info",
                code=snapshot.reboot_reason,
                message="Device uptime reset",
                occurred_at=occurred_at,
                created_at=occurred_at,
            )
        )

    _prune_events(session, device_id=device_id, now=occurred_at)


def _prune_events(session: Session, *, device_id: int, now: datetime) -> None:
    cutoff = now - timedelta(days=EVENT_RETENTION_DAYS)
    session.execute(
        delete(DeviceDiagnosticEvent)
        .where(DeviceDiagnosticEvent.device_id == device_id)
        .where(DeviceDiagnosticEvent.created_at < cutoff)
    )
    keep_ids = list(
        session.scalars(
            select(DeviceDiagnosticEvent.id)
            .where(DeviceDiagnosticEvent.device_id == device_id)
            .order_by(DeviceDiagnosticEvent.created_at.desc(), DeviceDiagnosticEvent.id.desc())
            .limit(EVENT_RETENTION_LIMIT)
        )
    )
    if keep_ids:
        session.execute(
            delete(DeviceDiagnosticEvent)
            .where(DeviceDiagnosticEvent.device_id == device_id)
            .where(DeviceDiagnosticEvent.id.not_in(keep_ids))
        )


def _timestamp_from_age(now: datetime, age_seconds: int | None) -> datetime | None:
    if age_seconds is None:
        return None
    return now - timedelta(seconds=age_seconds)


def _clean_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return cleaned[:max_length]
