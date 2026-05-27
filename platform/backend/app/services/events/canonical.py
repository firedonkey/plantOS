from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.contracts import CanonicalEvent, DiagnosticSeverity, EventType, NodeRole
from app.models.device_diagnostic import DeviceDiagnosticEvent


def write_canonical_event(
    session: Session,
    *,
    event_type: EventType,
    severity: DiagnosticSeverity,
    device_id: int,
    hardware_device_id: str,
    node_role: NodeRole | str,
    correlation_id: str | None = None,
    data: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> DeviceDiagnosticEvent:
    event_time = occurred_at or datetime.now(timezone.utc)
    canonical = CanonicalEvent(
        event_type=event_type,
        severity=severity,
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=_normalize_node_role(node_role),
        occurred_at=event_time,
        correlation_id=correlation_id,
        data=data or {},
    )
    db_event = DeviceDiagnosticEvent(
        device_id=canonical.device_id,
        hardware_device_id=canonical.hardware_device_id,
        event_type=canonical.event_type.value,
        severity=canonical.severity.value,
        code=canonical.event_type.value,
        message=_event_message(canonical.event_type),
        metadata_json={
            "schema_version": canonical.schema_version,
            "correlation_id": canonical.correlation_id,
            "node_role": canonical.node_role.value,
            "data": canonical.data,
        },
        occurred_at=canonical.occurred_at,
        created_at=datetime.now(timezone.utc),
    )
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


def _event_message(event_type: EventType) -> str:
    return event_type.value.replace("_", " ").title()


def _normalize_node_role(node_role: NodeRole | str) -> NodeRole:
    if isinstance(node_role, NodeRole):
        return node_role
    normalized = str(node_role or "").strip().lower()
    if normalized == "single_board":
        return NodeRole.MASTER
    return NodeRole(normalized)
