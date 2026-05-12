from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.db.session import get_session
from app.main import app
from app.models import Command, CommandStatus, Device, DeviceNode, SensorReading, User
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
            json={"moisture": 41.5, "temperature": 22.4, "timestamp": datetime.now(timezone.utc).isoformat()},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["moisture"] == 41.5

        with client.testing_session_local() as session:
            readings = session.query(SensorReading).filter(SensorReading.device_id == device_id).all()
            assert len(readings) == 1
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
            json={"status": "completed", "message": "light on", "light_on": True, "pump_on": False},
            headers={"X-Device-Token": "token-owner"},
        )
        assert done_response.status_code == 200
        assert done_response.json()["status"] == "completed"
        assert done_response.json()["light_on"] is True

        empty_pending = client.get("/api/hardware/commands/pending", headers={"X-Device-Token": "token-owner"})
        assert empty_pending.status_code == 200
        assert empty_pending.json() == []

        with client.testing_session_local() as session:
            command = session.get(Command, command_id)
            device = session.get(Device, device_id)
            assert command.status == CommandStatus.COMPLETED
            assert command.message == "light on"
            assert device.current_light_on is True
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
                "pump_on": False,
                "message": "hardware loop healthy",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "online"
        assert payload["hardware_device_id"] == "master-01"
        assert payload["last_seen_at"] is not None

        with client.testing_session_local() as session:
            device = session.get(Device, device_id)
            node = session.get(DeviceNode, "master-01")
            assert device.current_light_on is True
            assert device.status_message == "hardware loop healthy"
            assert node.status == "online"
            assert node.last_seen_at is not None
    finally:
        teardown_overrides()
