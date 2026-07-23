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
        assert envelope["payload"]["command_type"] == "SET_GROW_LIGHT_BRIGHTNESS"
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


def test_contract_poll_includes_grow_light_channel_intensity_params():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands/grow-light-channel",
            json={"channel": "white", "intensity_percent": 12},
        )
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        commands = response.json()["commands"]
        assert len(commands) == 1
        payload = commands[0]["payload"]
        assert payload["command_id"] == f"cmd_{command_id}"
        assert payload["command_type"] == "SET_GROW_LIGHT_BRIGHTNESS"
        assert payload["target"]["node_role"] == "master"
        assert payload["params"]["channel"] == "white"
        assert payload["params"]["brightness_percent"] == 12
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


def test_contract_poll_targets_specific_camera_role_without_leaking_to_other_camera():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        _add_node(client, device_id, hardware_device_id="camera-top", node_role="camera", camera_role="top")
        _add_node(client, device_id, hardware_device_id="camera-side", node_role="camera", camera_role="side")
        create_response = client.post(f"/api/devices/{device_id}/commands/capture", json={"camera_role": "top"})
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        side_response = _poll(client, hardware_device_id="camera-side", node_role="camera")
        top_response = _poll(client, hardware_device_id="camera-top", node_role="camera")

        assert side_response.status_code == 200
        assert side_response.json()["commands"] == []
        assert top_response.status_code == 200
        assert len(top_response.json()["commands"]) == 1
        top_command = top_response.json()["commands"][0]
        assert top_command["payload"]["command_id"] == f"cmd_{command_id}"
        assert top_command["payload"]["target"]["hardware_device_id"] == "camera-top"
        assert top_command["payload"]["target"]["camera_role"] == "top"
        assert top_command["payload"]["params"]["camera_role"] == "top"
    finally:
        teardown_overrides()


def test_contract_poll_all_camera_capture_has_no_specific_target_hardware_id():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        _add_node(client, device_id, hardware_device_id="camera-top", node_role="camera", camera_role="top")
        _add_node(client, device_id, hardware_device_id="camera-side", node_role="camera", camera_role="side")
        create_response = client.post(f"/api/devices/{device_id}/commands/capture", json={"camera_role": "all"})
        command_id = create_response.json()["command_id"]
        _use_device_token_auth()

        top_response = _poll(client, hardware_device_id="camera-top", node_role="camera")

        assert top_response.status_code == 200
        commands = top_response.json()["commands"]
        assert len(commands) == 1
        assert commands[0]["payload"]["command_id"] == f"cmd_{command_id}"
        assert commands[0]["payload"]["target"]["node_role"] == "camera"
        assert commands[0]["payload"]["target"].get("hardware_device_id") is None
        assert commands[0]["payload"]["target"].get("camera_role") is None
        assert commands[0]["payload"]["params"]["camera_role"] == "all"
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


def test_contract_poll_returns_request_diagnostics_command_to_master_node():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "diagnostics", "action": "request"},
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        commands = response.json()["commands"]
        assert len(commands) == 1
        assert commands[0]["payload"]["command_id"] == f"cmd_{command_id}"
        assert commands[0]["payload"]["command_type"] == "REQUEST_DIAGNOSTICS"
        assert commands[0]["payload"]["target"]["node_role"] == "master"
    finally:
        teardown_overrides()


def test_contract_poll_returns_reboot_command_to_master_node():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "system", "action": "reboot", "value": "validation"},
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        commands = response.json()["commands"]
        assert len(commands) == 1
        assert commands[0]["payload"]["command_id"] == f"cmd_{command_id}"
        assert commands[0]["payload"]["command_type"] == "REBOOT"
        assert commands[0]["payload"]["target"]["node_role"] == "master"
        assert commands[0]["payload"]["params"]["reason"] == "validation"
    finally:
        teardown_overrides()


def test_contract_poll_returns_ambient_led_belt_command_to_master_node():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id, hardware_device_id="master-01", node_role="master")
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={
                "target": "ambient_led_belt",
                "action": "set",
                "value": {
                    "mode": "solid",
                    "enabled": True,
                    "brightness": 26,
                    "color": {"r": 255, "g": 0, "b": 0},
                    "logical_pixel_count": 14,
                    "color_order": "RGB",
                },
            },
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()

        response = _poll(client, hardware_device_id="master-01", node_role="master")

        assert response.status_code == 200
        commands = response.json()["commands"]
        assert len(commands) == 1
        assert commands[0]["payload"]["command_id"] == f"cmd_{command_id}"
        assert commands[0]["payload"]["command_type"] == "SET_AMBIENT_LED_BELT"
        assert commands[0]["payload"]["target"]["node_role"] == "master"
        assert commands[0]["payload"]["params"] == {
            "mode": "solid",
            "enabled": True,
            "brightness": 26,
            "color": {"r": 255, "g": 0, "b": 0},
            "logical_pixel_count": 14,
            "color_order": "RGB",
        }
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
                    "command_type": "SET_GROW_LIGHT_BRIGHTNESS",
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


def _add_node(client, device_id: int, *, hardware_device_id: str, node_role: str, camera_role: str | None = None) -> None:
    with client.testing_session_local() as session:
        session.add(
            DeviceNode(
                device_id=device_id,
                hardware_device_id=hardware_device_id,
                node_role=node_role,
                camera_role=camera_role,
                hardware_model="esp32-s3-devkitc-1" if node_role == "master" else "xiao_esp32s3_camera",
                display_name=f"{camera_role.title()} camera" if camera_role else node_role.title(),
                status="online",
                capabilities={
                    "light_control": True,
                    "light_intensity_control": True,
                    "light_control_modes": ["on_off", "intensity"],
                    "grow_light_driver": "dual_al8860",
                    "grow_light_channel_control": True,
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
