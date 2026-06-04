from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.contracts import CanonicalEvent, DiagnosticSeverity, EventType, NodeRole
from app.models.device_diagnostic import DeviceDiagnosticEvent


logger = logging.getLogger(__name__)


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
    event_values = {
        "device_id": canonical.device_id,
        "hardware_device_id": canonical.hardware_device_id,
        "event_type": canonical.event_type.value,
        "severity": canonical.severity.value,
        "code": canonical.event_type.value,
        "message": _event_message(canonical.event_type),
        "metadata_json": {
            "schema_version": canonical.schema_version,
            "correlation_id": canonical.correlation_id,
            "node_role": canonical.node_role.value,
            "data": canonical.data,
        },
        "occurred_at": canonical.occurred_at,
        "created_at": datetime.now(timezone.utc),
    }
    db_event = DeviceDiagnosticEvent(
        **event_values,
    )
    session.add(db_event)
    session.flush()
    event_values["id"] = db_event.id
    session.commit()
    return _reload_or_detached_event(session, db_event, event_values)


def _reload_or_detached_event(
    session: Session,
    db_event: DeviceDiagnosticEvent,
    event_values: dict[str, Any],
) -> DeviceDiagnosticEvent:
    event_id = event_values.get("id")
    if event_id is None:
        return DeviceDiagnosticEvent(**event_values)

    try:
        session.expunge(db_event)
    except InvalidRequestError:
        pass

    try:
        reloaded = session.get(DeviceDiagnosticEvent, event_id)
    except SQLAlchemyError as exc:
        logger.warning(
            "Canonical event committed but could not be reloaded.",
            extra={
                "event_id": event_id,
                "event_type": event_values.get("event_type"),
                "device_id": event_values.get("device_id"),
                "hardware_device_id": event_values.get("hardware_device_id"),
                "reload_error": str(exc),
            },
        )
        return DeviceDiagnosticEvent(**event_values)

    if reloaded is None:
        logger.warning(
            "Canonical event committed but was missing during reload.",
            extra={
                "event_id": event_id,
                "event_type": event_values.get("event_type"),
                "device_id": event_values.get("device_id"),
                "hardware_device_id": event_values.get("hardware_device_id"),
            },
        )
        return DeviceDiagnosticEvent(**event_values)

    return reloaded


def _event_message(event_type: EventType) -> str:
    return event_type.value.replace("_", " ").title()


def _normalize_node_role(node_role: NodeRole | str) -> NodeRole:
    if isinstance(node_role, NodeRole):
        return node_role
    normalized = str(node_role or "").strip().lower()
    if normalized == "single_board":
        return NodeRole.MASTER
    return NodeRole(normalized)
