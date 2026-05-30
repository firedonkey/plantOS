from __future__ import annotations

from app.api.deps import get_current_user, get_optional_current_user
from app.main import app
from app.models import DeviceDiagnosticEvent, DeviceNode
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_command_events_survive_noisy_diagnostics_burst():
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
                    software_version="1.0.0",
                )
            )
            session.commit()

        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "set_intensity", "value": "65"},
        )
        assert create_response.status_code == 201

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        for index in range(120):
            response = client.post(
                "/api/hardware/diagnostics",
                json=_diagnostics(device_id=device_id, message_id=f"diag_retention_{index}"),
                headers={"X-Device-Token": "token-owner"},
            )
            assert response.status_code == 200

        with client.testing_session_local() as session:
            command_events = (
                session.query(DeviceDiagnosticEvent)
                .filter(DeviceDiagnosticEvent.device_id == device_id)
                .filter(DeviceDiagnosticEvent.event_type == "COMMAND_QUEUED")
                .all()
            )
            assert len(command_events) == 1
    finally:
        teardown_overrides()


def _diagnostics(*, device_id: int, message_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": message_id,
        "device_id": device_id,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "DIAGNOSTICS",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "status": "online",
            "severity": "info",
            "error_counters": {},
            "subsystem_statuses": {"wifi": "online"},
        },
    }
