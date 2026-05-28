from __future__ import annotations

from copy import deepcopy

from app.api.deps import get_current_user, get_optional_current_user
from app.contracts import (
    ProtocolValidationError,
    parse_command_message,
    parse_command_result_message,
    parse_diagnostics_message,
    parse_image_upload_message,
)
from app.main import app
from app.models import Command, CommandStatus, DeviceDiagnosticEvent, DeviceDiagnosticSnapshot, DeviceNode
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_valid_heartbeat_envelope_is_accepted_and_creates_events():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        response = client.post(
            "/api/hardware/heartbeat",
            json=_heartbeat_envelope(device_id=device_id),
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["hardware_device_id"] == "master-01"
        assert body["status"] == "online"
        assert body["software_version"] == "1.0.0"

        with client.testing_session_local() as session:
            node = session.get(DeviceNode, "master-01")
            assert node.status == "online"
            assert node.software_version == "1.0.0"
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).all()]
            assert "HEARTBEAT_RECEIVED" in event_types
            assert "DEVICE_ONLINE" in event_types
    finally:
        teardown_overrides()


def test_heartbeat_envelope_accepts_actuator_and_runtime_state():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope["payload"]["actuators"] = {
            "ambient_light": {
                "enabled": True,
                "brightness_percent": 65,
            }
        }
        envelope["payload"]["runtime"] = {
            "capture_interval_seconds": 3600,
            "ota_status": "idle",
            "provisioning_status": "normal",
            "camera_node_status": "online",
            "last_command_id": "cmd_12",
            "last_command_status": "completed",
        }

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["light_on"] is True
        assert body["light_intensity_percent"] == 65

        with client.testing_session_local() as session:
            event = (
                session.query(DeviceDiagnosticEvent)
                .filter(DeviceDiagnosticEvent.event_type == "HEARTBEAT_RECEIVED")
                .one()
            )
            assert event.metadata_json["data"]["actuators"]["ambient_light"]["brightness_percent"] == 65
            assert event.metadata_json["data"]["runtime"]["capture_interval_seconds"] == 3600
    finally:
        teardown_overrides()


def test_valid_diagnostics_envelope_is_accepted_and_creates_event():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        response = client.post(
            "/api/hardware/diagnostics",
            json=_diagnostics_envelope(device_id=device_id),
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["hardware_device_id"] == "master-01"
        assert body["reported_status"] == "degraded"
        assert body["error_counters"]["wifi_disconnects"] == 2
        assert body["last_error_code"] == "CAMERA_TIMEOUT"

        with client.testing_session_local() as session:
            snapshot = session.get(DeviceDiagnosticSnapshot, "master-01")
            assert snapshot is not None
            assert snapshot.reported_status == "degraded"
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).all()]
            assert "DIAGNOSTICS_RECEIVED" in event_types
    finally:
        teardown_overrides()


def test_old_heartbeat_payload_is_still_accepted():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "software_version": "0.9.0",
                "message": "legacy heartbeat",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["software_version"] == "0.9.0"
    finally:
        teardown_overrides()


def test_old_diagnostics_payload_is_still_accepted_in_heartbeat():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "diagnostics": {
                    "schema_version": 1,
                    "uptime_seconds": 42,
                    "wifi_rssi_dbm": -61,
                    "error_counters": {"wifi_reconnects": 1},
                },
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["diagnostics"]["uptime_seconds"] == 42
    finally:
        teardown_overrides()


def test_unsupported_schema_major_version_is_rejected():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope["schema_version"] = "2.0"

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_schema_version"
    finally:
        teardown_overrides()


def test_missing_required_heartbeat_field_is_rejected():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope["payload"].pop("uptime_seconds")

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 422
    finally:
        teardown_overrides()


def test_missing_required_diagnostics_field_is_rejected():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _diagnostics_envelope(device_id=device_id)
        envelope["payload"].pop("severity")

        response = client.post(
            "/api/hardware/diagnostics",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 422
    finally:
        teardown_overrides()


def test_unknown_additive_field_does_not_break_contract_validation():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope["future_envelope_field"] = "safe"
        envelope["payload"]["future_payload_field"] = "safe"

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
    finally:
        teardown_overrides()


def test_heartbeat_envelope_without_sent_at_is_accepted_for_early_boot_fallback():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope.pop("sent_at")

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
    finally:
        teardown_overrides()


def test_heartbeat_epoch_fallback_sent_at_uses_server_event_time():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _heartbeat_envelope(device_id=device_id)
        envelope["sent_at"] = "1970-01-01T00:00:00Z"

        response = client.post(
            "/api/hardware/heartbeat",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        with client.testing_session_local() as session:
            event = (
                session.query(DeviceDiagnosticEvent)
                .filter(DeviceDiagnosticEvent.event_type == "HEARTBEAT_RECEIVED")
                .one()
            )
            assert event.occurred_at.year >= 2024
    finally:
        teardown_overrides()


def test_diagnostics_envelope_without_sent_at_is_accepted_for_early_boot_fallback():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()
        envelope = _diagnostics_envelope(device_id=device_id)
        envelope.pop("sent_at")

        response = client.post(
            "/api/hardware/diagnostics",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
    finally:
        teardown_overrides()


def test_missing_sent_at_is_accepted_by_diagnostics_and_command_result_contracts():
    diagnostics = _diagnostics_envelope(device_id=1)
    diagnostics.pop("sent_at")
    command_result = _command_result_envelope(status="completed")
    command_result.pop("sent_at")

    assert parse_diagnostics_message(diagnostics).sent_at is None
    assert parse_command_result_message(command_result).sent_at is None


def test_valid_image_upload_contract_is_accepted():
    message = parse_image_upload_message(_image_upload_envelope(status="uploaded"))

    assert message.message_type == "IMAGE_UPLOAD"
    assert message.payload.status == "uploaded"
    assert message.payload.source_hardware_device_id == "camera-01"
    assert message.payload.width == 360
    assert message.payload.height == 240


def test_image_upload_failure_requires_failure_reason():
    envelope = _image_upload_envelope(status="failed")

    try:
        parse_image_upload_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "contract_validation_failed"
    else:
        raise AssertionError("Failed image upload without failure_reason should fail validation.")


def test_image_upload_unknown_additive_fields_are_accepted():
    envelope = _image_upload_envelope(status="uploaded")
    envelope["future_envelope_field"] = "safe"
    envelope["payload"]["future_payload_field"] = "safe"

    message = parse_image_upload_message(envelope)

    assert message.model_extra["future_envelope_field"] == "safe"
    assert message.payload.model_extra["future_payload_field"] == "safe"


def test_valid_capture_image_command_contract():
    message = parse_command_message(_command_envelope(command_type="CAPTURE_IMAGE", target_role="camera"))

    assert message.message_type == "COMMAND"
    assert message.payload.command_id == "cmd_123"
    assert message.payload.command_type == "CAPTURE_IMAGE"
    assert message.payload.target.node_role == "camera"
    assert message.payload.params["reason"] == "manual"


def test_valid_set_light_brightness_command_contract():
    message = parse_command_message(
        _command_envelope(
            command_type="SET_LIGHT_BRIGHTNESS",
            target_role="master",
            params={"brightness_percent": 65},
            timeout_ms=20_000,
        )
    )

    assert message.payload.command_type == "SET_LIGHT_BRIGHTNESS"
    assert message.payload.params["brightness_percent"] == 65


def test_valid_reboot_command_contract():
    message = parse_command_message(
        _command_envelope(
            command_type="REBOOT",
            target_role="master",
            params={"reason": "support"},
            timeout_ms=30_000,
        )
    )

    assert message.payload.command_type == "REBOOT"
    assert message.payload.target.node_role == "master"


def test_valid_successful_command_result_contract():
    message = parse_command_result_message(_command_result_envelope(status="completed"))

    assert message.message_type == "COMMAND_RESULT"
    assert message.payload.status == "completed"
    assert message.payload.result["upload_ms"] == 1836


def test_valid_failed_command_result_contract():
    message = parse_command_result_message(
        _command_result_envelope(status="failed", message="capture failed", error_code="INTERNAL_ERROR")
    )

    assert message.payload.status == "failed"
    assert message.payload.error_code == "INTERNAL_ERROR"


def test_valid_rejected_and_timed_out_command_result_contracts():
    rejected = parse_command_result_message(
        _command_result_envelope(status="rejected", message="camera busy", error_code="DEVICE_BUSY")
    )
    timed_out = parse_command_result_message(
        _command_result_envelope(status="timed_out", message="capture timed out", error_code="TIMEOUT")
    )

    assert rejected.payload.status == "rejected"
    assert timed_out.payload.status == "timed_out"


def test_missing_required_command_id_is_rejected():
    envelope = _command_envelope(command_type="CAPTURE_IMAGE", target_role="camera")
    envelope["payload"].pop("command_id")

    try:
        parse_command_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "contract_validation_failed"
    else:
        raise AssertionError("Missing command_id should fail validation.")


def test_unsupported_command_type_is_rejected():
    envelope = _command_envelope(command_type="CAPTURE_IMAGE", target_role="camera")
    envelope["payload"]["command_type"] = "PUMP"

    try:
        parse_command_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "contract_validation_failed"
    else:
        raise AssertionError("Unsupported command_type should fail validation.")


def test_command_unsupported_schema_major_version_is_rejected():
    envelope = _command_envelope(command_type="CAPTURE_IMAGE", target_role="camera")
    envelope["schema_version"] = "2.0"

    try:
        parse_command_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "unsupported_schema_version"
    else:
        raise AssertionError("Unsupported schema major version should fail validation.")


def test_command_unknown_additive_fields_are_accepted():
    envelope = _command_envelope(command_type="CAPTURE_IMAGE", target_role="camera")
    envelope["future_envelope_field"] = "safe"
    envelope["payload"]["future_payload_field"] = "safe"
    envelope["payload"]["target"]["future_target_field"] = "safe"

    message = parse_command_message(envelope)

    assert message.model_extra["future_envelope_field"] == "safe"
    assert message.payload.model_extra["future_payload_field"] == "safe"


def test_legacy_command_api_creates_command_queued_event():
    client, device_id, _ = build_client_with_devices()
    try:
        response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "set_intensity", "value": "65"},
        )

        assert response.status_code == 201
        command_id = response.json()["id"]
        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.PENDING
            events = session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()
            assert events[-1].event_type == "COMMAND_QUEUED"
            assert events[-1].metadata_json["command_id"] == f"cmd_{command_id}"
            assert events[-1].metadata_json["command_type"] == "SET_LIGHT_BRIGHTNESS"
    finally:
        teardown_overrides()


def test_legacy_command_result_still_works_and_creates_completed_event():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "on"},
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()
        client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})

        result_response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json={"status": "completed", "message": "light on", "light_on": True},
            headers={"X-Device-Token": "token-owner"},
        )

        assert result_response.status_code == 200
        assert result_response.json()["status"] == "completed"
        with client.testing_session_local() as session:
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()]
            assert "COMMAND_ACKED" in event_types
            assert "COMMAND_COMPLETED" in event_types
    finally:
        teardown_overrides()


def test_command_result_envelope_updates_command_and_creates_failed_event():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "set_intensity", "value": "65"},
        )
        command_id = create_response.json()["id"]
        _use_device_token_auth()
        client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})

        envelope = _command_result_envelope(
            command_id=f"cmd_{command_id}",
            command_type="SET_LIGHT_BRIGHTNESS",
            status="failed",
            message="invalid PWM state",
            error_code="INTERNAL_ERROR",
            result={"light_intensity_percent": 65},
        )
        response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json=envelope,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.FAILED
            events = session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()
            assert events[-1].event_type == "COMMAND_FAILED"
            assert events[-1].metadata_json["status"] == "failed"
            assert events[-1].metadata_json["command_type"] == "SET_LIGHT_BRIGHTNESS"
    finally:
        teardown_overrides()


def _add_node(client, device_id: int) -> None:
    with client.testing_session_local() as session:
        session.add(
            DeviceNode(
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="offline",
            )
        )
        session.commit()


def _use_device_token_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)


def _heartbeat_envelope(*, device_id: int) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "evt_test_heartbeat",
        "device_id": device_id,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "HEARTBEAT",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "uptime_seconds": 123,
            "wifi_rssi_dbm": -58,
            "ip_address": "192.168.1.20",
            "free_heap_bytes": 180000,
            "node_status": "online",
            "firmware_version": "1.0.0",
            "capabilities": ["ota", "ambient_led"],
        },
    }


def _diagnostics_envelope(*, device_id: int) -> dict:
    payload = {
        "schema_version": "1.0",
        "message_id": "evt_test_diagnostics",
        "device_id": device_id,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "DIAGNOSTICS",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "status": "degraded",
            "severity": "warning",
            "error_counters": {
                "wifi_disconnects": 2,
                "image_upload_failures": 1,
            },
            "last_error_code": "CAMERA_TIMEOUT",
            "last_error_message": "Camera node did not respond before timeout",
            "reboot_reason": "software_reset",
            "subsystem_statuses": {
                "wifi": "online",
                "camera": "degraded",
                "ota": "online",
            },
        },
    }
    return deepcopy(payload)


def _command_envelope(
    *,
    command_type: str,
    target_role: str,
    params: dict | None = None,
    timeout_ms: int = 120_000,
) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "cmdmsg_test",
        "device_id": 1,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "command_id": "cmd_123",
            "command_type": command_type,
            "target": {
                "node_role": target_role,
                "hardware_device_id": "camera-01" if target_role == "camera" else "master-01",
            },
            "params": params or {"reason": "manual"},
            "timeout_ms": timeout_ms,
            "retry_policy": {
                "max_attempts": 3,
                "backoff_ms": 3000,
            },
            "priority": "normal",
            "scheduled_for": None,
        },
    }


def _command_result_envelope(
    *,
    command_id: str = "cmd_123",
    command_type: str = "CAPTURE_IMAGE",
    status: str,
    message: str = "image uploaded",
    error_code: str | None = None,
    result: dict | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "cmdresmsg_test",
        "device_id": 1,
        "hardware_device_id": "camera-01",
        "node_role": "camera",
        "message_type": "COMMAND_RESULT",
        "sent_at": "2026-05-27T12:00:10Z",
        "payload": {
            "command_id": command_id,
            "command_type": command_type,
            "status": status,
            "message": message,
            "result": result or {"image_id": 991, "upload_ms": 1836},
            "error_code": error_code,
        },
    }


def _image_upload_envelope(*, status: str, failure_reason: str | None = None) -> dict:
    payload = {
        "status": status,
        "source_hardware_device_id": "camera-01",
        "source_node_role": "camera",
        "captured_at": "2026-05-27T12:09:00Z",
        "upload_reason": "manual",
        "width": 360,
        "height": 240,
        "content_type": "image/png",
        "upload_ms": 1836,
    }
    if failure_reason is not None:
        payload["failure_reason"] = failure_reason
    return {
        "schema_version": "1.0",
        "message_id": "imgmsg_test",
        "device_id": 1,
        "hardware_device_id": "camera-01",
        "node_role": "camera",
        "message_type": "IMAGE_UPLOAD",
        "sent_at": "2026-05-27T12:00:10Z",
        "payload": payload,
    }
