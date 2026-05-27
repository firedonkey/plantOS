from __future__ import annotations

from app.api.deps import get_current_user, get_optional_current_user
from app.contracts import OTACommandParams, ProtocolValidationError, parse_command_message, parse_ota_status_message
from app.main import app
from app.models import DeviceDiagnosticEvent
from app.services.firmware import OtaCompatibilityError, validate_ota_command_compatibility
from tests.test_firmware_ota_api import add_master_node, add_release, build_client_with_devices, teardown_overrides


def test_valid_ota_status_envelope_is_accepted_by_contract_parser():
    message = parse_ota_status_message(_ota_status_envelope(status="downloading", progress_percent=42))

    assert message.message_type == "OTA_STATUS"
    assert message.payload.command_id == "cmd_ota_123"
    assert message.payload.status == "downloading"
    assert message.payload.progress_percent == 42
    assert message.payload.firmware_channel == "beta"


def test_valid_ota_success_and_failed_status_contracts():
    success = parse_ota_status_message(
        _ota_status_envelope(status="success", progress_percent=100, phase="completed", current_version="1.2.0")
    )
    failed = parse_ota_status_message(
        _ota_status_envelope(
            status="failed",
            progress_percent=37,
            phase="install",
            failure_reason="checksum_mismatch",
            message="Firmware checksum validation failed",
        )
    )

    assert success.payload.status == "success"
    assert success.payload.phase == "completed"
    assert failed.payload.status == "failed"
    assert failed.payload.failure_reason == "checksum_mismatch"


def test_ota_status_missing_required_field_is_rejected():
    envelope = _ota_status_envelope(status="downloading")
    envelope["payload"].pop("command_id")

    try:
        parse_ota_status_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "contract_validation_failed"
    else:
        raise AssertionError("Missing OTA command_id should fail validation.")


def test_ota_status_unsupported_schema_major_version_is_rejected():
    envelope = _ota_status_envelope(status="downloading")
    envelope["schema_version"] = "2.0"

    try:
        parse_ota_status_message(envelope)
    except ProtocolValidationError as exc:
        assert exc.code == "unsupported_schema_version"
    else:
        raise AssertionError("Unsupported schema major version should fail validation.")


def test_ota_status_unknown_additive_fields_are_accepted():
    envelope = _ota_status_envelope(status="downloading")
    envelope["future_envelope_field"] = "safe"
    envelope["payload"]["future_payload_field"] = "safe"

    message = parse_ota_status_message(envelope)

    assert message.model_extra["future_envelope_field"] == "safe"
    assert message.payload.model_extra["future_payload_field"] == "safe"


def test_start_ota_command_params_are_validated_for_registered_node():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            node = add_master_node(session, device_id, software_version="1.1.0")
            command_message = parse_command_message(
                _start_ota_command_envelope(
                    params={
                        "target_version": "1.2.0",
                        "firmware_channel": "beta",
                        "hardware_model": "esp32-s3-devkitc-1",
                        "minimum_current_version": "1.0.0",
                    }
                )
            )
            params = OTACommandParams.model_validate(command_message.payload.params)

            validate_ota_command_compatibility(node=node, params=params)
    finally:
        teardown_overrides()


def test_ota_command_rejects_unsupported_hardware():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            node = add_master_node(session, device_id, software_version="1.1.0")
            params = OTACommandParams(
                target_version="1.2.0",
                hardware_model="other-board",
            )

            try:
                validate_ota_command_compatibility(node=node, params=params)
            except OtaCompatibilityError as exc:
                assert exc.code == "unsupported_hardware"
            else:
                raise AssertionError("Unsupported hardware should be rejected.")
    finally:
        teardown_overrides()


def test_ota_command_rejects_unsupported_firmware_version():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            node = add_master_node(session, device_id, software_version="0.9.0")
            params = OTACommandParams(
                target_version="1.2.0",
                hardware_model="esp32-s3-devkitc-1",
                minimum_current_version="1.0.0",
            )

            try:
                validate_ota_command_compatibility(node=node, params=params)
            except OtaCompatibilityError as exc:
                assert exc.code == "unsupported_firmware_version"
            else:
                raise AssertionError("Unsupported firmware version should be rejected.")
    finally:
        teardown_overrides()


def test_ota_status_envelope_updates_node_and_emits_canonical_events():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id, software_version="1.1.0")
            add_release(session, release_id="master-1.2.0", version="1.2.0", version_code=1_002_000)

        _use_device_token_auth()
        response = client.post(
            "/api/hardware/ota/status",
            json=_ota_status_envelope(status="downloading", progress_percent=42),
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "downloading"
        assert response.json()["progress"] == 42
        with testing_session_local() as session:
            event_types = [event.event_type for event in session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()]
            assert "OTA_STARTED" in event_types
            assert "OTA_DOWNLOADING" in event_types
    finally:
        teardown_overrides()


def test_ota_failed_status_envelope_emits_failed_event():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id, software_version="1.1.0")
            add_release(session, release_id="master-1.2.0", version="1.2.0", version_code=1_002_000)

        _use_device_token_auth()
        response = client.post(
            "/api/hardware/ota/status",
            json=_ota_status_envelope(
                status="failed",
                progress_percent=37,
                failure_reason="checksum_mismatch",
                message="Firmware checksum validation failed",
            ),
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["error"] == "Firmware checksum validation failed"
        with testing_session_local() as session:
            event = session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id.desc()).first()
            assert event.event_type == "OTA_FAILED"
            assert event.severity == "warning"
            assert event.metadata_json["data"]["failure_reason"] == "checksum_mismatch"
    finally:
        teardown_overrides()


def _use_device_token_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)


def _ota_status_envelope(
    *,
    status: str,
    progress_percent: int = 0,
    phase: str = "download",
    failure_reason: str | None = None,
    message: str = "Downloading firmware",
    current_version: str = "1.1.0",
) -> dict:
    payload = {
        "command_id": "cmd_ota_123",
        "status": status,
        "progress_percent": progress_percent,
        "current_version": current_version,
        "target_version": "1.2.0",
        "firmware_channel": "beta",
        "phase": phase,
        "message": message,
        "release_id": "master-1.2.0",
    }
    if failure_reason is not None:
        payload["failure_reason"] = failure_reason
    return {
        "schema_version": "1.0",
        "message_id": "otamsg_test",
        "device_id": 1,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "OTA_STATUS",
        "sent_at": "2026-05-27T12:01:00Z",
        "payload": payload,
    }


def _start_ota_command_envelope(*, params: dict) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "cmdmsg_ota_test",
        "device_id": 1,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "command_id": "cmd_ota_123",
            "command_type": "START_OTA",
            "target": {
                "node_role": "master",
                "hardware_device_id": "master-01",
            },
            "params": params,
            "timeout_ms": 1800000,
            "priority": "high",
        },
    }
