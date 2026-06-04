from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.contracts import DiagnosticSeverity, EventType
from app.models import Device, DeviceDiagnosticEvent, DeviceNode, User
from app.models.base import Base
from app.schemas.diagnostics import HardwareDiagnosticsCreate
from app.services.device_diagnostics import upsert_diagnostic_snapshot
from app.services.events import write_canonical_event


def test_write_canonical_event_persists_and_returns_event_info():
    TestingSessionLocal = _session_factory()
    with TestingSessionLocal() as session:
        device_id, hardware_device_id = _seed_device_node(session)

        event = write_canonical_event(
            session,
            event_type=EventType.HEARTBEAT_RECEIVED,
            severity=DiagnosticSeverity.INFO,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role="master",
            correlation_id="heartbeat-test",
            data={"source": "test"},
        )

        assert event.id is not None
        assert event.event_type == EventType.HEARTBEAT_RECEIVED.value
        assert event.metadata_json["correlation_id"] == "heartbeat-test"
        assert event.metadata_json["data"] == {"source": "test"}

        persisted = session.get(DeviceDiagnosticEvent, event.id)
        assert persisted is not None
        assert persisted.event_type == EventType.HEARTBEAT_RECEIVED.value


def test_write_canonical_event_does_not_refresh_after_commit(monkeypatch):
    TestingSessionLocal = _session_factory()
    with TestingSessionLocal() as session:
        device_id, hardware_device_id = _seed_device_node(session)

        def fail_refresh(*args, **kwargs):
            raise AssertionError("write_canonical_event should not call session.refresh")

        monkeypatch.setattr(session, "refresh", fail_refresh)

        event = write_canonical_event(
            session,
            event_type=EventType.HEARTBEAT_RECEIVED,
            severity=DiagnosticSeverity.INFO,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role="master",
            correlation_id="no-refresh",
            data={"source": "test"},
        )

        assert event.id is not None
        persisted = session.get(DeviceDiagnosticEvent, event.id)
        assert persisted is not None


def test_write_canonical_event_returns_detached_event_when_post_commit_reload_fails(monkeypatch, caplog):
    TestingSessionLocal = _session_factory()
    with TestingSessionLocal() as session:
        device_id, hardware_device_id = _seed_device_node(session)

        def fail_get(*args, **kwargs):
            raise InvalidRequestError("simulated post-commit reload failure")

        monkeypatch.setattr(session, "get", fail_get)
        caplog.set_level(logging.WARNING)

        event = write_canonical_event(
            session,
            event_type=EventType.HEARTBEAT_RECEIVED,
            severity=DiagnosticSeverity.INFO,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role="master",
            correlation_id="reload-failure",
            data={"source": "test"},
        )

        assert event.id is not None
        assert event.event_type == EventType.HEARTBEAT_RECEIVED.value
        assert event.metadata_json["correlation_id"] == "reload-failure"
        assert "Canonical event committed but could not be reloaded." in caplog.text

    with TestingSessionLocal() as verify_session:
        persisted = verify_session.get(DeviceDiagnosticEvent, event.id)
        assert persisted is not None
        assert persisted.event_type == EventType.HEARTBEAT_RECEIVED.value


def test_diagnostic_retention_does_not_delete_current_canonical_event():
    TestingSessionLocal = _session_factory()
    with TestingSessionLocal() as session:
        device_id, hardware_device_id = _seed_device_node(session)
        node = session.get(DeviceNode, hardware_device_id)
        assert node is not None

        old = datetime.now() - timedelta(days=1)
        for index in range(1005):
            session.add(
                DeviceDiagnosticEvent(
                    device_id=device_id,
                    hardware_device_id=hardware_device_id,
                    event_type="old_event",
                    severity="info",
                    code="old_event",
                    message="Old event",
                    metadata_json={"index": index},
                    occurred_at=old,
                    created_at=old + timedelta(seconds=index),
                )
            )
        session.commit()

        current = write_canonical_event(
            session,
            event_type=EventType.HEARTBEAT_RECEIVED,
            severity=DiagnosticSeverity.INFO,
            device_id=device_id,
            hardware_device_id=hardware_device_id,
            node_role="master",
            correlation_id="current-event",
            data={"source": "heartbeat"},
        )

        upsert_diagnostic_snapshot(
            session,
            device_id=device_id,
            node=node,
            status="online",
            diagnostics=HardwareDiagnosticsCreate(
                schema_version=1,
                uptime_seconds=100,
                wifi_rssi_dbm=-55,
                error_counters={"upload_failures": 1},
            ),
            reported_at=datetime.now(),
        )

        persisted = session.get(DeviceDiagnosticEvent, current.id)
        assert persisted is not None
        assert persisted.event_type == EventType.HEARTBEAT_RECEIVED.value


def test_legacy_heartbeat_upload_failure_diagnostics_path_does_not_raise():
    from app.api.deps import get_current_user, get_optional_current_user
    from app.main import app
    from tests.test_hardware_api import build_client_with_devices, teardown_overrides

    client, device_id, _ = build_client_with_devices()
    try:
        with client.testing_session_local() as session:
            session.add(
                DeviceNode(
                    device_id=device_id,
                    hardware_device_id="master-01",
                    node_role="master",
                    display_name="Master",
                    status="online",
                    software_version="0.1.6",
                )
            )
            session.commit()

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "software_version": "0.1.6",
                "light_intensity_percent": 50,
                "diagnostics": {
                    "schema_version": 1,
                    "uptime_seconds": 230335,
                    "wifi_rssi_dbm": -51,
                    "error_counters": {"upload_failures": 1},
                    "last_error": {
                        "code": "sensor_upload_failed",
                        "message": "sensor reading upload failed",
                    },
                },
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        with client.testing_session_local() as session:
            event_types = {
                event.event_type
                for event in session.scalars(select(DeviceDiagnosticEvent).where(DeviceDiagnosticEvent.device_id == device_id))
            }
            assert EventType.HEARTBEAT_RECEIVED.value in event_types
            assert EventType.DIAGNOSTICS_RECEIVED.value in event_types
            assert "upload_failure" in event_types
            assert "last_error" in event_types
    finally:
        teardown_overrides()


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_device_node(session: Session) -> tuple[int, str]:
    user = User(email="owner@example.com", google_sub="owner-google")
    session.add(user)
    session.commit()
    device = Device(user_id=user.id, name="Kitchen Rose", api_token="token-owner")
    session.add(device)
    session.commit()
    hardware_device_id = "master-01"
    node = DeviceNode(
        device_id=device.id,
        hardware_device_id=hardware_device_id,
        node_role="master",
        display_name="Master",
        status="online",
        software_version="0.1.6",
    )
    session.add(node)
    session.commit()
    return device.id, hardware_device_id
