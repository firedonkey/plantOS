from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import (
    Command,
    Device,
    DeviceDiagnosticEvent,
    DeviceDiagnosticSnapshot,
    DeviceNode,
    FirmwareRelease,
    Image,
    SensorReading,
    User,
)
from app.models.base import Base


def build_admin_client(current_email: str) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    now = datetime.now(timezone.utc)
    with TestingSessionLocal() as session:
        admin = User(email="admin@example.com", name="Admin")
        grower = User(email="grower@example.com", name="Grower")
        session.add_all([admin, grower])
        session.commit()
        session.refresh(admin)
        session.refresh(grower)

        device = Device(
            user_id=grower.id,
            name="Kitchen PlantLab",
            location="Kitchen",
            plant_type="Basil",
            api_token="secret-device-token",
        )
        session.add(device)
        session.commit()
        session.refresh(device)

        session.add_all(
            [
                DeviceNode(
                    hardware_device_id="pl-esp32-test",
                    device_id=device.id,
                    node_role="master",
                    hardware_model="esp32_master",
                    software_version="0.1.2",
                    status="online",
                    last_seen_at=now,
                ),
                SensorReading(device_id=device.id, timestamp=now - timedelta(minutes=1), temperature=23.5, humidity=45.0),
                Image(device_id=device.id, path="device/image.jpg", timestamp=now - timedelta(minutes=2)),
                Command(
                    device_id=device.id,
                    target="grow_light",
                    action="set_intensity",
                    value="80",
                    status="completed",
                    message="Brightness set",
                    created_at=now - timedelta(seconds=30),
                    completed_at=now - timedelta(seconds=25),
                ),
                DeviceDiagnosticSnapshot(
                    hardware_device_id="pl-esp32-test",
                    device_id=device.id,
                    node_role="master",
                    reported_status="online",
                    firmware_version="0.1.2",
                    last_error_code="wifi_reconnects",
                    last_error_message="Wi-Fi recovered",
                    reported_at=now,
                    updated_at=now,
                ),
                DeviceDiagnosticEvent(
                    device_id=device.id,
                    hardware_device_id="pl-esp32-test",
                    event_type="reconnect",
                    severity="warning",
                    code="wifi_reconnects",
                    message="Wi-Fi recovered",
                    occurred_at=now,
                    created_at=now,
                ),
                FirmwareRelease(
                    release_id="master-0.1.2-test",
                    node_role="master",
                    hardware_model="esp32_master",
                    version="0.1.2",
                    version_code=102,
                    artifact_path="firmware/master.bin",
                    artifact_size_bytes=128,
                    sha256="a" * 64,
                    status="published",
                    published_at=now,
                ),
            ]
        )
        session.commit()

        current_user_id = admin.id if current_email == admin.email else grower.id

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    def override_current_user() -> User:
        with TestingSessionLocal() as session:
            return session.get(User, current_user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_optional_current_user] = override_current_user
    return TestClient(app)


def test_admin_diagnostics_requires_admin_email(monkeypatch):
    monkeypatch.setenv("PLANTLAB_ADMIN_EMAILS", "admin@example.com")
    get_settings.cache_clear()
    client = build_admin_client("grower@example.com")
    try:
        response = client.get("/api/admin/diagnostics")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_admin_diagnostics_summarizes_all_users_without_tokens(monkeypatch):
    monkeypatch.setenv("PLANTLAB_ADMIN_EMAILS", "admin@example.com")
    get_settings.cache_clear()
    client = build_admin_client("admin@example.com")
    try:
        response = client.get("/api/admin/diagnostics")
        assert response.status_code == 200
        payload = response.json()
        assert payload["requested_by"]["email"] == "admin@example.com"
        assert payload["summary"]["users"] == 2
        assert payload["summary"]["active_users"] == 1
        assert payload["summary"]["devices"] == 1
        assert payload["summary"]["hardware_nodes"] == 1
        assert payload["summary"]["recent_warning_events"] == 1
        grower = next(user for user in payload["users"] if user["email"] == "grower@example.com")
        assert grower["recent_command_count"] == 1
        assert grower["recent_warning_event_count"] == 1
        assert payload["devices"][0]["owner_email"] == "grower@example.com"
        assert payload["devices"][0]["status"] == "online"
        assert payload["devices"][0]["last_error_code"] == "wifi_reconnects"
        assert payload["recent_events"][0]["code"] == "wifi_reconnects"
        assert payload["recent_commands"][0]["action"] == "set_intensity"
        assert payload["recent_commands"][0]["owner_email"] == "grower@example.com"
        assert payload["firmware_releases"][0]["channel"] == "stable"
        assert payload["firmware_releases"][0]["rollout_percentage"] == 100
        assert "secret-device-token" not in response.text
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
