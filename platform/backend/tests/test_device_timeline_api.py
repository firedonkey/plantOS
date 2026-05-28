from datetime import datetime, timedelta, timezone

from app.models import DeviceDiagnosticEvent
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_device_timeline_returns_newest_first_with_summaries_and_pagination():
    client, device_id, _ = build_client_with_devices()
    try:
        now = datetime.now(timezone.utc)
        with client.testing_session_local() as session:
            session.add_all(
                [
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="HEARTBEAT_RECEIVED",
                        severity="info",
                        message="Heartbeat Received",
                        metadata_json={
                            "schema_version": "1.0",
                            "correlation_id": "hb_1",
                            "node_role": "master",
                            "data": {"wifi_rssi_dbm": -58},
                        },
                        occurred_at=now - timedelta(minutes=3),
                        created_at=now - timedelta(minutes=3),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="COMMAND_SENT",
                        severity="info",
                        code="COMMAND_SENT",
                        metadata_json={
                            "schema_version": "1.0",
                            "correlation_id": "cmd_9",
                            "command_id": "cmd_9",
                            "command_type": "START_OTA",
                            "target_node_role": "master",
                            "status": "sent",
                        },
                        occurred_at=now - timedelta(minutes=2),
                        created_at=now - timedelta(minutes=2),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="OTA_FAILED",
                        severity="warning",
                        code="checksum_mismatch",
                        metadata_json={
                            "schema_version": "1.0",
                            "correlation_id": "cmd_9",
                            "node_role": "master",
                            "data": {
                                "target_version": "1.2.0",
                                "progress_percent": 37,
                                "failure_reason": "checksum_mismatch",
                            },
                        },
                        occurred_at=now - timedelta(minutes=1),
                        created_at=now - timedelta(minutes=1),
                    ),
                ]
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timeline?limit=2")

        assert response.status_code == 200
        body = response.json()
        assert [event["event_type"] for event in body["events"]] == ["OTA_FAILED", "COMMAND_SENT"]
        assert body["events"][0]["summary"] == "OTA failed: checksum mismatch"
        assert body["events"][1]["summary"] == "START_OTA sent to master node"
        assert body["events"][0]["correlation_id"] == "cmd_9"
        assert body["events"][0]["node_role"] == "master"
        assert body["events"][0]["data"]["failure_reason"] == "checksum_mismatch"
        assert body["next_before"] is not None
    finally:
        teardown_overrides()


def test_device_timeline_filters_by_type_severity_node_role_and_correlation():
    client, device_id, _ = build_client_with_devices()
    try:
        now = datetime.now(timezone.utc)
        with client.testing_session_local() as session:
            session.add_all(
                [
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="COMMAND_SENT",
                        severity="info",
                        metadata_json={
                            "correlation_id": "cmd_1",
                            "command_type": "CAPTURE_IMAGE",
                            "target_node_role": "camera",
                            "node_role": "master",
                        },
                        occurred_at=now - timedelta(minutes=2),
                        created_at=now - timedelta(minutes=2),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="COMMAND_FAILED",
                        severity="warning",
                        code="DEVICE_BUSY",
                        metadata_json={
                            "correlation_id": "cmd_2",
                            "command_type": "CAPTURE_IMAGE",
                            "target_node_role": "camera",
                            "node_role": "master",
                        },
                        occurred_at=now - timedelta(minutes=1),
                        created_at=now - timedelta(minutes=1),
                    ),
                ]
            )
            session.commit()

        response = client.get(
            f"/api/devices/{device_id}/timeline",
            params={
                "event_type": "COMMAND_FAILED",
                "severity": "warning",
                "node_role": "master",
                "correlation_id": "cmd_2",
            },
        )

        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) == 1
        assert events[0]["event_type"] == "COMMAND_FAILED"
        assert events[0]["summary"] == "CAPTURE_IMAGE failed: device busy"

        target_response = client.get(
            f"/api/devices/{device_id}/timeline",
            params={
                "event_type": "COMMAND_SENT",
                "node_role": "camera",
                "correlation_id": "cmd_1",
            },
        )
        assert target_response.status_code == 200
        target_events = target_response.json()["events"]
        assert len(target_events) == 1
        assert target_events[0]["summary"] == "CAPTURE_IMAGE sent to camera node"
    finally:
        teardown_overrides()


def test_device_timeline_handles_unknown_event_type_safely():
    client, device_id, _ = build_client_with_devices()
    try:
        now = datetime.now(timezone.utc)
        with client.testing_session_local() as session:
            session.add(
                DeviceDiagnosticEvent(
                    device_id=device_id,
                    hardware_device_id="master-01",
                    event_type="FUTURE_EVENT_TYPE",
                    severity="info",
                    metadata_json={"node_role": "master"},
                    occurred_at=now,
                    created_at=now,
                )
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timeline")

        assert response.status_code == 200
        assert response.json()["events"][0]["summary"] == "future event type"
    finally:
        teardown_overrides()


def test_device_timeline_summarizes_image_upload_events():
    client, device_id, _ = build_client_with_devices()
    try:
        now = datetime.now(timezone.utc)
        with client.testing_session_local() as session:
            session.add_all(
                [
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="cam-01",
                        event_type="IMAGE_UPLOADED",
                        severity="info",
                        metadata_json={
                            "correlation_id": "img_1",
                            "node_role": "camera",
                            "data": {
                                "image_id": 91,
                                "upload_reason": "manual",
                                "source_hardware_device_id": "cam-01",
                            },
                        },
                        occurred_at=now - timedelta(seconds=2),
                        created_at=now - timedelta(seconds=2),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="cam-01",
                        event_type="IMAGE_CAPTURE_STARTED",
                        severity="info",
                        metadata_json={"correlation_id": "cmd_91", "node_role": "camera", "data": {}},
                        occurred_at=now - timedelta(seconds=4),
                        created_at=now - timedelta(seconds=4),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="cam-01",
                        event_type="IMAGE_CAPTURED",
                        severity="info",
                        metadata_json={"correlation_id": "img_1", "node_role": "camera", "data": {"image_id": 91}},
                        occurred_at=now - timedelta(seconds=3),
                        created_at=now - timedelta(seconds=3),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="cam-01",
                        event_type="IMAGE_UPLOAD_STARTED",
                        severity="info",
                        metadata_json={"correlation_id": "img_1", "node_role": "camera", "data": {}},
                        occurred_at=now - timedelta(seconds=2, milliseconds=500),
                        created_at=now - timedelta(seconds=2, milliseconds=500),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="cam-01",
                        event_type="IMAGE_UPLOAD_FAILED",
                        severity="warning",
                        metadata_json={
                            "correlation_id": "img_2",
                            "node_role": "camera",
                            "data": {
                                "failure_reason": "camera_timeout",
                                "source_hardware_device_id": "cam-01",
                            },
                        },
                        occurred_at=now - timedelta(seconds=1),
                        created_at=now - timedelta(seconds=1),
                    ),
                ]
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timeline")

        assert response.status_code == 200
        summaries = [event["summary"] for event in response.json()["events"]]
        assert summaries == [
            "Image upload failed: camera timeout",
            "Image uploaded #91 (manual)",
            "Image upload started",
            "Image captured #91",
            "Image capture started",
        ]
    finally:
        teardown_overrides()


def test_device_timeline_summarizes_provisioning_events():
    client, device_id, _ = build_client_with_devices()
    try:
        now = datetime.now(timezone.utc)
        with client.testing_session_local() as session:
            session.add_all(
                [
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="PROVISIONING_STARTED",
                        severity="info",
                        metadata_json={"correlation_id": "provisioning:1", "node_role": "master", "data": {}},
                        occurred_at=now - timedelta(seconds=3),
                        created_at=now - timedelta(seconds=3),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="PROVISIONING_SUCCESS",
                        severity="info",
                        metadata_json={"correlation_id": "provisioning:1", "node_role": "master", "data": {}},
                        occurred_at=now - timedelta(seconds=2),
                        created_at=now - timedelta(seconds=2),
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="PROVISIONING_FAILED",
                        severity="warning",
                        metadata_json={
                            "correlation_id": "provisioning:2",
                            "node_role": "master",
                            "data": {"failure_reason": "claim_token_expired"},
                        },
                        occurred_at=now - timedelta(seconds=1),
                        created_at=now - timedelta(seconds=1),
                    ),
                ]
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timeline")

        assert response.status_code == 200
        summaries = [event["summary"] for event in response.json()["events"]]
        assert summaries == [
            "Provisioning failed: claim token expired",
            "Provisioning completed",
            "Provisioning started",
        ]
    finally:
        teardown_overrides()
