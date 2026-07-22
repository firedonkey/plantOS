from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.db.session import get_session
from app.main import app
from app.models import Command, CommandStatus, Device, DeviceDiagnosticEvent, DeviceDiagnosticSnapshot, DeviceNode, SensorReading, User
from app.models.base import Base


def build_client_with_devices() -> tuple[TestClient, int, int]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
        user = User(email="owner@example.com", google_sub="owner-google")
        other_user = User(email="other@example.com", google_sub="other-google")
        session.add_all([user, other_user])
        session.commit()
        session.refresh(user)
        session.refresh(other_user)

        device = Device(user_id=user.id, name="Kitchen Rose", api_token="token-owner")
        other_device = Device(user_id=other_user.id, name="Other Rose", api_token="token-other")
        session.add_all([device, other_device])
        session.commit()
        session.refresh(device)
        session.refresh(other_device)
        user_id = user.id
        device_id = device.id
        other_device_id = other_device.id

    def override_session() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    def override_current_user() -> User:
        with TestingSessionLocal() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_optional_current_user] = override_current_user
    client = TestClient(app)
    client.testing_session_local = TestingSessionLocal
    return client, device_id, other_device_id


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def test_hardware_readings_accept_valid_device_token():
    client, device_id, _ = build_client_with_devices()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        response = client.post(
            "/api/hardware/readings",
            json={
                "moisture": 41.5,
                "temperature": 22.4,
                "water_temperature_c": 20.1,
                "water_level_raw": 34890,
                "water_level_state": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["moisture"] == 41.5
        assert payload["water_temperature_c"] == 20.1
        assert payload["water_level_raw"] == 34890
        assert payload["water_level_state"] == "ok"

        with client.testing_session_local() as session:
            readings = session.query(SensorReading).filter(SensorReading.device_id == device_id).all()
            assert len(readings) == 1
            assert readings[0].water_temperature_c == 20.1
            assert readings[0].water_level_raw == 34890
            assert readings[0].water_level_state == "ok"
    finally:
        teardown_overrides()


def test_hardware_readings_reject_invalid_device_token():
    client, _, _ = build_client_with_devices()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        response = client.post(
            "/api/hardware/readings",
            json={"moisture": 41.5},
            headers={"X-Device-Token": "bad-token"},
        )

        assert response.status_code == 401
    finally:
        teardown_overrides()


def test_hardware_pending_commands_are_scoped_to_device():
    client, device_id, other_device_id = build_client_with_devices()
    try:
        client.post(f"/api/devices/{device_id}/commands", json={"target": "light", "action": "on"})
        client.post(f"/api/devices/{other_device_id}/commands", json={"target": "pump", "action": "run", "value": "5"})
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)

        response = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["device_id"] == device_id
        assert payload[0]["status"] == "in_progress"
    finally:
        teardown_overrides()


def test_hardware_pending_commands_include_light_intensity_contract():
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
                    capabilities={
                        "light_control": True,
                        "light_intensity_control": True,
                        "light_control_modes": ["on_off", "intensity"],
                    },
                )
            )
            session.commit()

        create_response = client.post(
            f"/api/devices/{device_id}/commands/light",
            json={"intensity_percent": 65},
        )
        assert create_response.status_code == 201
        command_id = create_response.json()["command_id"]

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["id"] == command_id
        assert payload[0]["device_id"] == device_id
        assert payload[0]["target"] == "grow_light"
        assert payload[0]["action"] == "set_intensity"
        assert payload[0]["value"] == "65"
        assert payload[0]["status"] == "in_progress"
    finally:
        teardown_overrides()


def test_hardware_command_result_updates_status_and_hides_completed_from_pending():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(f"/api/devices/{device_id}/commands", json={"target": "light", "action": "on"})
        command_id = create_response.json()["id"]
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)

        poll_response = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})
        assert poll_response.status_code == 200
        assert poll_response.json()[0]["id"] == command_id

        progress_response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json={"status": "in_progress", "message": "relay enabled"},
            headers={"X-Device-Token": "token-owner"},
        )
        assert progress_response.status_code == 200
        assert progress_response.json()["status"] == "in_progress"

        done_response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json={
                "status": "completed",
                "message": "light on",
                "light_on": True,
                "light_intensity_percent": 80,
                "pump_on": False,
            },
            headers={"X-Device-Token": "token-owner"},
        )
        assert done_response.status_code == 200
        assert done_response.json()["status"] == "completed"
        assert done_response.json()["light_on"] is True
        assert done_response.json()["light_intensity_percent"] == 80

        empty_pending = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})
        assert empty_pending.status_code == 200
        assert empty_pending.json() == []

        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            device = session.get(Device, device_id)
            assert command.status == CommandStatus.COMPLETED
            assert command.message == "light on"
            assert command.light_intensity_percent == 80
            assert device.current_light_on is True
            assert device.current_light_intensity_percent == 80
    finally:
        teardown_overrides()


def test_hardware_failed_command_stores_error_message():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(f"/api/devices/{device_id}/commands", json={"target": "pump", "action": "run", "value": "5"})
        command_id = create_response.json()["id"]
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)

        client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})
        result_response = client.post(
            f"/api/hardware/commands/{command_id}/result",
            json={"status": "failed", "error": "pump jam detected"},
            headers={"X-Device-Token": "token-owner"},
        )

        assert result_response.status_code == 200
        payload = result_response.json()
        assert payload["status"] == "failed"
        assert payload["message"] == "pump jam detected"

        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            assert command.status == CommandStatus.FAILED
            assert command.message == "pump jam detected"
    finally:
        teardown_overrides()


def test_hardware_heartbeat_updates_device_and_node_status():
    client, device_id, _ = build_client_with_devices()
    try:
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

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "light_on": True,
                "light_intensity_percent": 55,
                "pump_on": False,
                "message": "hardware loop healthy",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "online"
        assert payload["hardware_device_id"] == "master-01"
        assert payload["light_intensity_percent"] == 55
        assert payload["last_seen_at"] is not None
        assert payload["diagnostics"] is None

        with client.testing_session_local() as session:
            device = session.get(Device, device_id)
            node = session.get(DeviceNode, "master-01")
            assert device.current_light_on is True
            assert device.current_light_intensity_percent == 55
            assert device.status_message == "hardware loop healthy"
            assert node.status == "online"
            assert node.last_seen_at is not None
            assert session.get(DeviceDiagnosticSnapshot, "master-01") is None
    finally:
        teardown_overrides()


def test_hardware_heartbeat_accepts_diagnostics_and_stores_bounded_events():
    client, device_id, _ = build_client_with_devices()
    try:
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

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        payload = {
            "hardware_device_id": "master-01",
            "node_role": "master",
            "status": "online",
            "software_version": "0.2.3",
            "message": "hardware loop healthy",
            "diagnostics": {
                "schema_version": 1,
                "uptime_seconds": 1234,
                "wifi_rssi_dbm": -76,
                "reboot_reason": "power_on",
                "provisioning_state": "normal",
                "last_sensor_reading_age_seconds": 7,
                "last_command": {
                    "id": 17,
                    "status": "completed",
                    "code": "ok",
                    "message": "light command completed",
                    "age_seconds": 4,
                },
                "error_counters": {
                    "wifi_reconnects": 1,
                    "upload_failures": 1,
                    "ble_provisioning_failures": 0,
                    "espnow_failures": 0,
                },
                "last_error": {
                    "code": "upload_failed",
                    "message": "sensor upload failed",
                },
            },
        }
        response = client.post("/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"})

        assert response.status_code == 200
        diagnostics = response.json()["diagnostics"]
        assert diagnostics["hardware_device_id"] == "master-01"
        assert diagnostics["firmware_version"] == "0.2.3"
        assert diagnostics["uptime_seconds"] == 1234
        assert diagnostics["wifi_rssi_dbm"] == -76
        assert diagnostics["last_command_status"] == "completed"
        assert diagnostics["error_counters"]["wifi_reconnects"] == 1

        repeat_response = client.post("/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"})
        assert repeat_response.status_code == 200

        payload["diagnostics"]["error_counters"]["upload_failures"] = 2
        increment_response = client.post("/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"})
        assert increment_response.status_code == 200

        payload["diagnostics"]["last_error"] = {
            "code": "wifi_connect_timeout",
            "message": "wifi reconnect timed out",
        }
        changed_error_response = client.post(
            "/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"}
        )
        assert changed_error_response.status_code == 200

        payload["diagnostics"]["uptime_seconds"] = 12
        payload["diagnostics"]["reboot_reason"] = "software_reset"
        reboot_response = client.post("/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"})
        assert reboot_response.status_code == 200

        with client.testing_session_local() as session:
            snapshot = session.get(DeviceDiagnosticSnapshot, "master-01")
            assert snapshot is not None
            assert snapshot.device_id == device_id
            assert snapshot.provisioning_state == "normal"
            assert snapshot.error_counters["upload_failures"] == 2
            assert snapshot.last_error_code == "wifi_connect_timeout"
            assert snapshot.uptime_seconds == 12

            events = session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()
            assert [event.event_type for event in events].count("upload_failure") == 2
            assert [event.event_type for event in events].count("wifi_reconnect") == 1
            assert [event.event_type for event in events].count("last_error") == 2
            assert [event.event_type for event in events].count("reboot") == 1
    finally:
        teardown_overrides()


def test_hardware_heartbeat_rejects_unsupported_diagnostic_counter():
    client, device_id, _ = build_client_with_devices()
    try:
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

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "diagnostics": {
                    "error_counters": {
                        "wifi_reconnects": 1,
                        "device_token_failures": 1,
                    },
                },
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 422
    finally:
        teardown_overrides()


def test_hardware_heartbeat_rejects_diagnostics_for_foreign_node():
    client, _, other_device_id = build_client_with_devices()
    try:
        with client.testing_session_local() as session:
            session.add(
                DeviceNode(
                    device_id=other_device_id,
                    hardware_device_id="other-master",
                    node_role="master",
                    display_name="Other Master",
                    status="online",
                )
            )
            session.commit()

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "other-master",
                "node_role": "master",
                "status": "online",
                "diagnostics": {"uptime_seconds": 12},
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 404
        with client.testing_session_local() as session:
            assert session.get(DeviceDiagnosticSnapshot, "other-master") is None
    finally:
        teardown_overrides()
