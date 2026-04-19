from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.db.session import get_session
from app.main import app
from app.models import Command, Device, User
from app.models.base import Base
from app.services.commands import DEFAULT_COMMAND_TIMEOUT_SECONDS


def test_default_command_timeout_is_20_seconds():
    assert DEFAULT_COMMAND_TIMEOUT_SECONDS == 20


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


def test_owner_can_create_and_list_command():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "pump", "action": "run", "value": "5"},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["target"] == "pump"
        assert created["action"] == "run"
        assert created["status"] == "pending"

        list_response = client.get(f"/api/devices/{device_id}/commands")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
    finally:
        teardown_overrides()


def test_duplicate_active_command_returns_existing_command():
    client, device_id, _ = build_client_with_devices()
    try:
        first_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "on"},
        )
        second_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "on"},
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert second_response.json()["id"] == first_response.json()["id"]

        list_response = client.get(f"/api/devices/{device_id}/commands")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
    finally:
        teardown_overrides()


def test_command_rejects_invalid_target_action():
    client, device_id, _ = build_client_with_devices()
    try:
        response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "pump", "action": "on"},
        )

        assert response.status_code == 422
    finally:
        teardown_overrides()


def test_device_can_poll_and_ack_pending_command():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "on"},
        )
        command_id = create_response.json()["id"]

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)

        poll_response = client.get(
            f"/api/devices/{device_id}/commands/pending",
            headers={"X-Device-Token": "token-owner"},
        )
        assert poll_response.status_code == 200
        commands = poll_response.json()
        assert len(commands) == 1
        assert commands[0]["id"] == command_id
        assert commands[0]["status"] == "sent"

        empty_poll_response = client.get(
            f"/api/devices/{device_id}/commands/pending",
            headers={"X-Device-Token": "token-owner"},
        )
        assert empty_poll_response.status_code == 200
        assert empty_poll_response.json() == []

        ack_response = client.post(
            f"/api/devices/{device_id}/commands/{command_id}/ack",
            json={"status": "completed", "message": "light on", "light_on": True, "pump_on": False},
            headers={"X-Device-Token": "token-owner"},
        )
        assert ack_response.status_code == 200
        assert ack_response.json()["status"] == "completed"
        assert ack_response.json()["message"] == "light on"
        assert ack_response.json()["light_on"] is True
        assert ack_response.json()["pump_on"] is False
    finally:
        teardown_overrides()


def test_device_token_cannot_poll_other_device_commands():
    client, _, other_device_id = build_client_with_devices()
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        response = client.get(
            f"/api/devices/{other_device_id}/commands/pending",
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 403
    finally:
        teardown_overrides()


def test_pending_command_times_out_when_device_does_not_pick_it_up():
    client, device_id, _ = build_client_with_devices()
    try:
        create_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "off"},
        )
        command_id = create_response.json()["id"]

        with client.testing_session_local() as session:
            command = session.scalar(select(Command).where(Command.id == command_id))
            command.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            session.commit()

        list_response = client.get(f"/api/devices/{device_id}/commands")

        assert list_response.status_code == 200
        payload = list_response.json()
        assert payload[0]["id"] == command_id
        assert payload[0]["status"] == "timed_out"
        assert payload[0]["message"] == "Timed out waiting for device pickup."
    finally:
        teardown_overrides()
