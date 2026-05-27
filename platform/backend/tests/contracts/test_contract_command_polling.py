from __future__ import annotations

from app.api.deps import get_current_user, get_optional_current_user
from app.main import app
from app.models import Command, CommandStatus, DeviceDiagnosticEvent, DeviceNode
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_contract_poll_returns_typed_command_envelope_and_sent_events():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands/light",
            json={"intensity_percent": 65},
        )
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        payload = response.json()
        assert payload["schema_version"] == "1.0"
        assert len(payload["commands"]) == 1
        envelope = payload["commands"][0]
        assert envelope["message_type"] == "COMMAND"
        assert envelope["hardware_device_id"] == "master-01"
        assert envelope["node_role"] == "master"
        assert envelope["payload"]["command_id"] == f"cmd_{command_id}"
        assert envelope["payload"]["command_type"] == "SET_LIGHT_BRIGHTNESS"
        assert envelope["payload"]["target"]["node_role"] == "master"
        assert envelope["payload"]["params"]["brightness_percent"] == 65

        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.SENT
            assert command.sent_at is not None
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()]
            assert "COMMAND_POLLED" in event_types
            assert "COMMAND_SENT" in event_types
    finally:
        teardown_overrides()


def test_contract_poll_returns_empty_list_cleanly():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        assert response.json() == {"schema_version": "1.0", "commands": []}
    finally:
        teardown_overrides()


def test_contract_poll_filters_master_command_from_camera_node():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        _add_node(client, device_id, hardware_device_id="camera-01", node_role="camera")
        create_response = client.post(
            f"/api/devices/{device_id}/commands/light",
            json={"state": "on"},
        )
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="camera-01", node_role="camera")

        assert response.status_code == 200
        assert response.json()["commands"] == []
        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.PENDING
    finally:
        teardown_overrides()


def test_contract_poll_returns_camera_command_to_camera_node():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        _add_node(client, device_id, hardware_device_id="camera-01", node_role="camera")
        create_response = client.post(f"/api/devices/{device_id}/commands/capture")
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="camera-01", node_role="camera")

        assert response.status_code == 200
        commands = response.json()["commands"]
        assert len(commands) == 1
        assert commands[0]["payload"]["command_id"] == f"cmd_{command_id}"
        assert commands[0]["payload"]["command_type"] == "CAPTURE_IMAGE"
        assert commands[0]["payload"]["target"]["node_role"] == "camera"
        assert commands[0]["payload"]["target"]["hardware_device_id"] == "camera-01"
    finally:
        teardown_overrides()


def test_contract_poll_rejects_unsupported_schema_version():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master", schema_version="2.0")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_schema_version"
    finally:
        teardown_overrides()


def test_contract_poll_handles_unsupported_firmware_version_without_legacy_breakage():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        response = _poll(
            client,
            hardware_device_id="master-01",
            node_role="master",
            firmware_version="0.0.1",
        )

        assert response.status_code == 200
        assert response.json()["commands"] == []
        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.PENDING
    finally:
        teardown_overrides()


def test_contract_poll_filters_unsupported_legacy_pump_command():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "pump", "action": "run", "value": "5"},
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        assert response.json()["commands"] == []
        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.PENDING
    finally:
        teardown_overrides()


def test_legacy_polling_still_works_after_contract_poll_endpoint_added():
    client, device_id, _ = build_client_with_devices()
    try:
        client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        _use_device_token_auth()

        response = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["status"] == "in_progress"
    finally:
        teardown_overrides()


def test_contract_poll_command_result_ack_flow_still_works():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()
        _poll(client, hardware_device_id="master-01", node_role="master")

        response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json={
                "schema_version": "1.0",
                "message_id": "cmdres_ack_test",
                "device_id": device_id,
                "hardware_device_id": "master-01",
                "node_role": "master",
                "message_type": "COMMAND_RESULT",
                "sent_at": "2026-05-27T12:00:03Z",
                "payload": {
                    "command_id": f"cmd_{command_id}",
                    "command_type": "SET_LIGHT_BRIGHTNESS",
                    "status": "acked",
                },
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        with client.testing_session_local() as session:
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()]
            assert "COMMAND_ACKED" in event_types
    finally:
        teardown_overrides()


def _add_node(client, device_id: int, *, hardware_device_id: str, node_role: str) -> None:
    with client.testing_session_local() as session:
        session.add(
            DeviceNode(
                device_id=device_id,
                hardware_device_id=hardware_device_id,
                node_role=node_role,
                hardware_model="esp32-s3-devkitc-1" if node_role == "master" else "xiao_esp32s3_camera",
                display_name=node_role.title(),
                status="online",
                capabilities={
                    "light_control": True,
                    "light_intensity_control": True,
                    "light_control_modes": ["on_off", "intensity"],
                }
                if node_role == "master"
                else {},
            )
        )
        session.commit()


def _use_device_token_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)


def _poll(
    client,
    *,
    hardware_device_id: str,
    node_role: str,
    schema_version: str = "1.0",
    firmware_version: str = "1.2.0",
):
    return client.get(
        "/api/hardware/commands/poll",
        params={
            "hardware_device_id": hardware_device_id,
            "node_role": node_role,
            "firmware_version": firmware_version,
            "schema_version": schema_version,
            "hardware_model": "esp32-s3-devkitc-1" if node_role == "master" else "xiao_esp32s3_camera",
        },
        headers={"X-Device-Token": "token-owner"},
    )
