from datetime import datetime, timezone

from app.models import DeviceDiagnosticEvent, DeviceNode, SensorReading
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_setup_status_emits_provisioning_started_once():
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
                )
            )
            session.commit()

        params = {"expected_device_id": "master-01", "expect_image": "false"}
        first = client.get("/api/setup/status", params=params)
        second = client.get("/api/setup/status", params=params)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["ready"] is False
        with client.testing_session_local() as session:
            events = session.query(DeviceDiagnosticEvent).filter_by(event_type="PROVISIONING_STARTED").all()
            assert len(events) == 1
            assert events[0].hardware_device_id == "master-01"
            assert events[0].metadata_json["data"]["status"] == "online"
    finally:
        teardown_overrides()


def test_setup_status_emits_provisioning_success_once():
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
                )
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    temperature=22.5,
                    humidity=45.0,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            session.commit()

        params = {"expected_device_id": "master-01", "expect_image": "false"}
        first = client.get("/api/setup/status", params=params)
        second = client.get("/api/setup/status", params=params)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["ready"] is True
        with client.testing_session_local() as session:
            events = session.query(DeviceDiagnosticEvent).filter_by(event_type="PROVISIONING_SUCCESS").all()
            assert len(events) == 1
            assert events[0].metadata_json["data"]["status"] == "online"
    finally:
        teardown_overrides()


def test_setup_status_emits_provisioning_failed_for_error_node():
    client, device_id, _ = build_client_with_devices()
    try:
        with client.testing_session_local() as session:
            session.add(
                DeviceNode(
                    device_id=device_id,
                    hardware_device_id="master-01",
                    node_role="master",
                    display_name="Master",
                    status="error",
                )
            )
            session.commit()

        response = client.get("/api/setup/status", params={"expected_device_id": "master-01", "expect_image": "false"})

        assert response.status_code == 200
        with client.testing_session_local() as session:
            event = session.query(DeviceDiagnosticEvent).filter_by(event_type="PROVISIONING_FAILED").one()
            assert event.severity == "warning"
            assert event.metadata_json["data"]["status"] == "error"
    finally:
        teardown_overrides()
