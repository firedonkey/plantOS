from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import DiagnosticSeverity, EventType
from app.models.device_diagnostic import DeviceDiagnosticEvent
from app.services.events import write_canonical_event


def write_canonical_event_once(
    session: Session,
    *,
    event_type: EventType,
    severity: DiagnosticSeverity,
    device_id: int,
    hardware_device_id: str,
    node_role: str,
    correlation_id: str,
    data: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> DeviceDiagnosticEvent | None:
    existing = session.scalars(
        select(DeviceDiagnosticEvent)
        .where(DeviceDiagnosticEvent.device_id == device_id)
        .where(DeviceDiagnosticEvent.hardware_device_id == hardware_device_id)
        .where(DeviceDiagnosticEvent.event_type == event_type.value)
    ).all()
    for event in existing:
        metadata = event.metadata_json or {}
        if metadata.get("correlation_id") == correlation_id:
            return None

    return write_canonical_event(
        session,
        event_type=event_type,
        severity=severity,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        correlation_id=correlation_id,
        data=data or {},
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )
