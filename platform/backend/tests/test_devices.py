from collections.abc import Generator
from base64 import b64encode
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import devices as device_routes
from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import (
    Command,
    CommandAction,
    CommandStatus,
    CommandTarget,
    Device,
    DeviceDiagnosticEvent,
    DeviceDiagnosticSnapshot,
    DeviceNode,
    Event,
    EventType,
    Image,
    SensorReading,
    User,
)
from app.models.base import Base
from app.services import storage as storage_service
from app.services.device_nodes import upsert_device_node
from app.web.routes import _latest_device_activity, _latest_completed_command_state, _reading_chart


def build_client_with_user(set_session_cookie: bool = False) -> tuple[TestClient, User]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
        user = User(email="grower@example.com", google_sub="google-123", name="Grower")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

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
    if set_session_cookie:
        client.cookies.set("session", signed_session_cookie({"user_id": user_id}))

    return client, User(id=user_id, email="grower@example.com", name="Grower")


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def signed_session_cookie(payload: dict) -> str:
    data = b64encode(json.dumps(payload).encode("utf-8"))
    return TimestampSigner(get_settings().session_secret).sign(data).decode("utf-8")


def test_device_api_requires_auth():
    client = TestClient(app)
    response = client.get("/api/devices")

    assert response.status_code == 401


def test_create_list_and_get_device_api():
    client, _ = build_client_with_user()
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == "Kitchen Rose"

        list_response = client.get("/api/devices")
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["status"] == "unknown"
        assert listed[0]["latest_reading"] is None
        assert listed[0]["latest_image"] is None
        assert listed[0]["node_summary"]["overall_status"] == "offline"
        assert listed[0]["node_summary"]["primary"] is None
        assert listed[0]["node_summary"]["cameras"] == []
        assert listed[0]["hardware_health"]["overall_status"] == "offline"
        assert listed[0]["hardware_health"]["master_online"] is False
        assert listed[0]["hardware_health"]["last_heartbeat_at"] is None
        assert listed[0]["hardware_health"]["heartbeat_status"] is None
        assert listed[0]["hardware_health"]["last_reading_at"] is None
        assert listed[0]["hardware_health"]["reading_status"] is None
        assert listed[0]["hardware_health"]["last_image_at"] is None
        assert listed[0]["hardware_health"]["image_status"] is None
        assert listed[0]["hardware_health"]["camera_status"] is None
        assert listed[0]["hardware_health"]["last_command"] is None
        assert listed[0]["hardware_health"]["last_failed_command_reason"] is None
        assert listed[0]["hardware_health"]["last_successful_command_at"] is None

        get_response = client.get(f"/api/devices/{created['id']}")
        assert get_response.status_code == 200
        payload = get_response.json()
        assert payload["location"] == "Kitchen window"
        assert payload["status"] == "unknown"
    finally:
        teardown_overrides()


def test_device_read_status_uses_stale_heartbeat_over_stored_online_node():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]
        stale_seen_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=stale_seen_at,
            )

        list_response = client.get("/api/devices")
        get_response = client.get(f"/api/devices/{device_id}")

        assert list_response.status_code == 200
        assert get_response.status_code == 200
        assert list_response.json()[0]["node_summary"]["primary"]["status"] == "online"
        assert list_response.json()[0]["status"] == "stale"
        assert list_response.json()[0]["hardware_health"]["heartbeat_status"] == "stale"
        assert get_response.json()["status"] == "stale"
        assert get_response.json()["hardware_health"]["primary"]["health_status"] == "stale"
    finally:
        teardown_overrides()


def test_update_device_api():
    client, _ = build_client_with_user()
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]

        update_response = client.patch(
            f"/api/devices/{device_id}",
            json={
                "name": "Kitchen Basil",
                "location": "Desk",
                "plant_type": "Basil",
            },
        )

        assert update_response.status_code == 200
        payload = update_response.json()
        assert payload["name"] == "Kitchen Basil"
        assert payload["location"] == "Desk"
        assert payload["plant_type"] == "Basil"
    finally:
        teardown_overrides()


def test_device_summary_readings_and_latest_image_api():
    client, _ = build_client_with_user()
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]

        client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 42.5,
                "temperature": 22.2,
                "humidity": 51.0,
                "water_temperature_c": 19.7,
                "water_level_raw": 35240,
                "water_level_state": "ok",
                "light_on": True,
                "pump_on": False,
                "pump_status": "idle",
            },
        )

        with next(app.dependency_overrides[get_session]()) as session:
            session.add(Image(device_id=device_id, path="device-1/test.jpg"))
            session.commit()

        summary_response = client.get(f"/api/devices/{device_id}/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["name"] == "Kitchen Rose"
        assert summary["latest_reading"]["moisture"] == 42.5
        assert summary["latest_reading"]["water_temperature_c"] == 19.7
        assert summary["latest_reading"]["water_level_raw"] == 35240
        assert summary["latest_reading"]["water_level_state"] == "ok"
        assert summary["latest_image"]["content_url"].endswith("/api/images/1/content")
        assert summary["hardware_health"]["last_reading_at"] == summary["latest_reading"]["timestamp"]
        assert summary["hardware_health"]["last_image_at"] == summary["latest_image"]["timestamp"]
        assert summary["hardware_health"]["overall_status"] == "offline"

        readings_response = client.get(f"/api/devices/{device_id}/readings")
        assert readings_response.status_code == 200
        readings = readings_response.json()
        assert len(readings) == 1
        assert readings[0]["temperature"] == 22.2
        assert readings[0]["water_temperature_c"] == 19.7
        assert readings[0]["water_level_raw"] == 35240
        assert readings[0]["water_level_state"] == "ok"

        latest_image_response = client.get(f"/api/devices/{device_id}/images/latest")
        assert latest_image_response.status_code == 200
        assert latest_image_response.json()["id"] == 1

        list_response = client.get("/api/devices")
        assert list_response.status_code == 200
        listed = list_response.json()
        assert listed[0]["latest_reading"]["temperature"] == 22.2
        assert listed[0]["latest_reading"]["water_temperature_c"] == 19.7
        assert listed[0]["latest_reading"]["water_level_raw"] == 35240
        assert listed[0]["latest_reading"]["water_level_state"] == "ok"
        assert listed[0]["latest_image"]["content_url"].endswith("/api/images/1/content")
        assert listed[0]["status"] == "online"
        assert listed[0]["hardware_health"]["last_reading_at"] == listed[0]["latest_reading"]["timestamp"]
        assert listed[0]["hardware_health"]["last_image_at"] == listed[0]["latest_image"]["timestamp"]
    finally:
        teardown_overrides()


def test_device_latest_image_api_returns_null_when_missing():
    client, _ = build_client_with_user()
    try:
        create_response = client.post(
            "/api/devices",
            json={"name": "Kitchen Rose"},
        )
        device_id = create_response.json()["id"]

        latest_image_response = client.get(f"/api/devices/{device_id}/images/latest")
        assert latest_image_response.status_code == 200
        assert latest_image_response.json() is None
    finally:
        teardown_overrides()


def test_device_images_api_requires_auth():
    client = TestClient(app)

    response = client.get("/api/devices/1/images")

    assert response.status_code == 401


def test_device_images_api_returns_recent_images_with_limit():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]
        base_time = datetime.now(timezone.utc)

        with next(app.dependency_overrides[get_session]()) as session:
            session.add(
                Image(
                    device_id=device_id,
                    path="device-1/one.jpg",
                    source_hardware_device_id="cam-1",
                    timestamp=base_time,
                )
            )
            session.add(
                Image(
                    device_id=device_id,
                    path="device-1/two.jpg",
                    source_hardware_device_id="cam-2",
                    timestamp=base_time + timedelta(minutes=1),
                )
            )
            session.add(
                Image(
                    device_id=device_id,
                    path="device-1/three.jpg",
                    source_hardware_device_id="cam-3",
                    timestamp=base_time + timedelta(minutes=2),
                )
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/images?limit=2")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 2
        assert payload[0]["content_url"].endswith("/api/images/3/content")
        assert payload[0]["source_hardware_device_id"] == "cam-3"
        assert payload[1]["content_url"].endswith("/api/images/2/content")
        assert payload[1]["source_hardware_device_id"] == "cam-2"
    finally:
        teardown_overrides()


def test_device_image_apis_return_signed_urls_for_gcs_images(monkeypatch):
    signed_calls = []

    def fake_signed_url(bucket_name: str, object_name: str, settings) -> str:
        signed_calls.append((bucket_name, object_name, settings.image_signed_url_ttl_seconds))
        return f"https://storage.googleapis.com/{bucket_name}/{object_name}?X-Goog-Signature=test"

    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("GCS_BUCKET_NAME", "plantlab-images")
    monkeypatch.setenv("PLANTLAB_IMAGE_SIGNED_URL_TTL_SECONDS", "900")
    monkeypatch.delenv("PLANTLAB_IMAGE_URL_STRATEGY", raising=False)
    monkeypatch.setattr(storage_service, "_signed_gcs_image_url", fake_signed_url)
    get_settings.cache_clear()

    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            session.add(Image(device_id=device_id, path="gs://plantlab-images/device-1/newest.jpg"))
            session.commit()

        latest_response = client.get(f"/api/devices/{device_id}/images/latest")
        list_response = client.get(f"/api/devices/{device_id}/images")
        summary_response = client.get(f"/api/devices/{device_id}/summary")

        assert latest_response.status_code == 200
        assert list_response.status_code == 200
        assert summary_response.status_code == 200
        assert latest_response.json()["content_url"].startswith("https://storage.googleapis.com/plantlab-images/")
        assert "/api/images/" not in latest_response.json()["content_url"]
        assert list_response.json()[0]["content_url"] == latest_response.json()["content_url"]
        assert summary_response.json()["latest_image"]["content_url"] == latest_response.json()["content_url"]
        assert signed_calls == [
            ("plantlab-images", "device-1/newest.jpg", 900),
            ("plantlab-images", "device-1/newest.jpg", 900),
            ("plantlab-images", "device-1/newest.jpg", 900),
        ]
    finally:
        teardown_overrides()
        get_settings.cache_clear()


def test_device_images_api_returns_404_when_device_missing():
    client, _ = build_client_with_user()
    try:
        response = client.get("/api/devices/999/images")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "not_found"
    finally:
        teardown_overrides()


def test_device_readings_api_requires_auth():
    client = TestClient(app)

    response = client.get("/api/devices/1/readings")

    assert response.status_code == 401


def test_device_readings_api_uses_default_newest_order_and_limit():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]
        base_time = datetime.now(timezone.utc)

        with next(app.dependency_overrides[get_session]()) as session:
            for offset in range(3):
                session.add(
                    SensorReading(
                        device_id=device_id,
                        temperature=20 + offset,
                        timestamp=base_time + timedelta(hours=offset),
                    )
                )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/readings")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 3
        assert payload[0]["temperature"] == 22
        assert payload[-1]["temperature"] == 20
    finally:
        teardown_overrides()


def test_device_readings_api_supports_limit_date_range_and_oldest_order():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]
        base_time = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)

        with next(app.dependency_overrides[get_session]()) as session:
            for offset in range(5):
                session.add(
                    SensorReading(
                        device_id=device_id,
                        temperature=20 + offset,
                        timestamp=base_time + timedelta(days=offset),
                    )
                )
            session.commit()

        response = client.get(
            f"/api/devices/{device_id}/readings",
            params={
                "start": (base_time + timedelta(days=1)).isoformat(),
                "end": (base_time + timedelta(days=3)).isoformat(),
                "limit": 2,
                "order": "oldest",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 2
        assert payload[0]["temperature"] == 21
        assert payload[1]["temperature"] == 22
    finally:
        teardown_overrides()


def test_device_readings_api_accepts_extended_history_limit():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]

        response = client.get(f"/api/devices/{device_id}/readings", params={"limit": 50000})
        too_large_response = client.get(f"/api/devices/{device_id}/readings", params={"limit": 50001})

        assert response.status_code == 200
        assert too_large_response.status_code == 422
    finally:
        teardown_overrides()


def test_device_readings_api_returns_404_when_device_missing():
    client, _ = build_client_with_user()
    try:
        response = client.get("/api/devices/999/readings")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "not_found"
    finally:
        teardown_overrides()


def test_device_command_wrapper_apis():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device_id = create_response.json()["id"]

        light_response = client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        assert light_response.status_code == 201
        light_payload = light_response.json()
        assert light_payload["status"] == "accepted"
        assert light_payload["device_id"] == device_id
        assert light_payload["command"] == "light"
        assert light_payload["action"] == "on"
        assert light_payload["queued"] is True
        assert light_payload["command_status"] == "pending"

        unsupported_intensity_response = client.post(
            f"/api/devices/{device_id}/commands/light",
            json={"intensity_percent": 65},
        )
        assert unsupported_intensity_response.status_code == 409

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                capabilities={
                    "light_control": True,
                    "light_intensity_control": True,
                    "light_control_modes": ["on_off", "intensity"],
                },
            )

        intensity_response = client.post(
            f"/api/devices/{device_id}/commands/light",
            json={"intensity_percent": 65},
        )
        assert intensity_response.status_code == 201
        intensity_payload = intensity_response.json()
        assert intensity_payload["status"] == "accepted"
        assert intensity_payload["command"] == "light"
        assert intensity_payload["action"] == "set_intensity"
        assert intensity_payload["value"] == "65"

        with next(app.dependency_overrides[get_session]()) as session:
            intensity_command = session.get(Command, intensity_payload["command_id"])
            assert intensity_command is not None
            assert intensity_command.target == CommandTarget.LIGHT
            assert intensity_command.action == CommandAction.SET_INTENSITY
            assert intensity_command.value == "65"

        pump_response = client.post(f"/api/devices/{device_id}/commands/pump", json={"action": "run", "seconds": 7})
        assert pump_response.status_code == 201
        pump_payload = pump_response.json()
        assert pump_payload["status"] == "accepted"
        assert pump_payload["command"] == "pump"
        assert pump_payload["action"] == "run"
        assert pump_payload["queued"] is True
        assert pump_payload["value"] == "7"

        capture_response = client.post(f"/api/devices/{device_id}/commands/capture")
        assert capture_response.status_code == 201
        capture_payload = capture_response.json()
        assert capture_payload["status"] == "accepted"
        assert capture_payload["device_id"] == device_id
        assert capture_payload["command"] == "capture"
        assert capture_payload["action"] == "capture"
        assert capture_payload["queued"] is True
        assert capture_payload["command_status"] == "pending"
        assert capture_payload["message"] == "Capture command queued."

        with next(app.dependency_overrides[get_session]()) as session:
            capture_command = session.get(Command, capture_payload["command_id"])
            assert capture_command is not None
            assert capture_command.target == CommandTarget.CAMERA
            assert capture_command.action == CommandAction.CAPTURE
    finally:
        teardown_overrides()


def test_device_capture_command_api_requires_auth():
    client = TestClient(app)

    response = client.post("/api/devices/1/commands/capture")

    assert response.status_code == 401


def test_device_capture_command_api_returns_404_when_device_missing():
    client, _ = build_client_with_user()
    try:
        response = client.post("/api/devices/999/commands/capture")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "not_found"
    finally:
        teardown_overrides()


def test_device_summary_exposes_hardware_health_and_last_command():
    client, _ = build_client_with_user()
    now = datetime.now(timezone.utc)
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device = create_response.json()
        device_id = device["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=now,
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-cam-1",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="offline",
                last_seen_at=now - timedelta(minutes=6),
            )

        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "hardware_device_id": "pl-esp32-master",
                "moisture": 41.0,
                "temperature": 23.4,
                "humidity": 52.5,
                "light_on": False,
                "pump_on": False,
            },
        )
        assert data_response.status_code == 201

        with next(app.dependency_overrides[get_session]()) as session:
            session.add(
                Image(
                    device_id=device_id,
                    path="device-1/test.jpg",
                    timestamp=now,
                )
            )
            session.commit()

        command_response = client.post(f"/api/devices/{device_id}/commands/light", json={"state": "on"})
        assert command_response.status_code == 201
        command_id = command_response.json()["command_id"]

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        ack_response = client.post(
            f"/api/devices/{device_id}/commands/{command_id}/ack",
            json={"status": "completed", "message": "light turned on", "light_on": True, "pump_on": False},
            headers={"X-Device-Token": device["api_token"]},
        )
        assert ack_response.status_code == 200

        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="grower@example.com", name="Grower")
        app.dependency_overrides[get_optional_current_user] = app.dependency_overrides[get_current_user]
        summary_response = client.get(f"/api/devices/{device_id}/summary")

        assert summary_response.status_code == 200
        payload = summary_response.json()
        assert payload["hardware_health"]["overall_status"] == "degraded"
        assert payload["hardware_health"]["master_status"] == "online"
        assert payload["hardware_health"]["master_online"] is True
        assert payload["hardware_health"]["primary"]["status"] == "online"
        assert payload["hardware_health"]["primary"]["health_status"] == "online"
        assert payload["hardware_health"]["cameras"][0]["status"] == "offline"
        assert payload["hardware_health"]["cameras"][0]["health_status"] == "offline"
        assert payload["hardware_health"]["last_heartbeat_at"] is not None
        assert payload["hardware_health"]["heartbeat_status"] == "online"
        assert payload["hardware_health"]["last_reading_at"] == payload["latest_reading"]["timestamp"]
        assert payload["hardware_health"]["reading_status"] == "online"
        assert payload["hardware_health"]["last_image_at"] is not None
        assert payload["hardware_health"]["image_status"] == "online"
        assert payload["hardware_health"]["camera_status"] == "offline"
        assert payload["hardware_health"]["last_command"]["id"] == command_id
        assert payload["hardware_health"]["last_command"]["status"] == "completed"
        assert payload["hardware_health"]["last_command"]["message"] == "light turned on"
        assert payload["hardware_health"]["last_failed_command_reason"] is None
        assert payload["hardware_health"]["last_successful_command_at"] is not None
    finally:
        teardown_overrides()


def test_device_summary_exposes_diagnostic_snapshot_and_needs_attention_status():
    client, _ = build_client_with_user()
    now = datetime.now(timezone.utc)
    try:
        create_response = client.post("/api/devices", json={"name": "Diagnostics Plant"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                software_version="0.2.3",
                last_seen_at=now,
            )
            session.add(
                DeviceDiagnosticSnapshot(
                    hardware_device_id="pl-esp32-master",
                    device_id=device_id,
                    node_role="master",
                    schema_version=1,
                    reported_status="online",
                    firmware_version="0.2.3",
                    uptime_seconds=420,
                    wifi_rssi_dbm=-81,
                    reboot_reason="power_on",
                    provisioning_state="normal",
                    last_sensor_reading_at=now - timedelta(seconds=9),
                    last_command_id=41,
                    last_command_status="failed",
                    last_command_code="relay_timeout",
                    last_command_message="relay did not settle",
                    last_command_at=now - timedelta(seconds=4),
                    error_counters={"upload_failures": 2, "wifi_reconnects": 0},
                    last_error_code="upload_failed",
                    last_error_message="sensor upload failed",
                    reported_at=now,
                    updated_at=now,
                )
            )
            session.add(
                DeviceDiagnosticEvent(
                    device_id=device_id,
                    hardware_device_id="pl-esp32-master",
                    event_type="upload_failure",
                    severity="warning",
                    code="upload_failures",
                    message="upload_failures increased",
                    count=2,
                    occurred_at=now,
                    created_at=now,
                )
            )
            session.commit()

        summary_response = client.get(f"/api/devices/{device_id}/summary")
        diagnostics_response = client.get(f"/api/devices/{device_id}/diagnostics")

        assert summary_response.status_code == 200
        payload = summary_response.json()
        health = payload["hardware_health"]
        assert health["friendly_status"] == "needs_attention"
        assert "weak_wifi_signal" in health["attention_reasons"]
        assert "upload_failures_reported" in health["attention_reasons"]
        assert "diagnostic_error" in health["attention_reasons"]
        assert health["last_reading_at"] is not None
        assert health["primary"]["diagnostics"]["uptime_seconds"] == 420
        assert health["primary"]["diagnostics"]["wifi_rssi_dbm"] == -81
        assert health["primary"]["diagnostics"]["last_command_code"] == "relay_timeout"
        assert health["recent_events"][0]["event_type"] == "upload_failure"

        assert diagnostics_response.status_code == 200
        diagnostics = diagnostics_response.json()
        assert diagnostics["snapshots"][0]["hardware_device_id"] == "pl-esp32-master"
        assert diagnostics["recent_events"][0]["code"] == "upload_failures"
    finally:
        teardown_overrides()


def test_device_summary_marks_old_heartbeat_offline_without_diagnostics():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Offline Plant"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=datetime.now(timezone.utc) - timedelta(minutes=7),
            )

        summary_response = client.get(f"/api/devices/{device_id}/summary")

        assert summary_response.status_code == 200
        health = summary_response.json()["hardware_health"]
        assert health["heartbeat_status"] == "offline"
        assert health["friendly_status"] == "offline"
        assert health["primary"]["diagnostics"] is None
        assert health["attention_reasons"] == []
    finally:
        teardown_overrides()


def test_device_summary_exposes_stale_diagnostics_and_last_failed_command():
    client, _ = build_client_with_user()
    now = datetime.now(timezone.utc)
    try:
        create_response = client.post("/api/devices", json={"name": "Bench Plant"})
        device = create_response.json()
        device_id = device["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-master",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=now - timedelta(minutes=2),
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-cam-1",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
                last_seen_at=now - timedelta(minutes=7),
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    timestamp=now - timedelta(minutes=6),
                    moisture=42.0,
                    temperature=21.5,
                    humidity=48.2,
                )
            )
            session.add(
                Image(
                    device_id=device_id,
                    path="device-stale/test.jpg",
                    timestamp=now - timedelta(minutes=25),
                    source_hardware_device_id="pl-cam-1",
                )
            )
            session.add(
                Command(
                    device_id=device_id,
                    target=CommandTarget.LIGHT,
                    action=CommandAction.ON,
                    status=CommandStatus.COMPLETED,
                    message="light turned on",
                    created_at=now - timedelta(minutes=10),
                    sent_at=now - timedelta(minutes=10),
                    completed_at=now - timedelta(minutes=9),
                )
            )
            session.add(
                Command(
                    device_id=device_id,
                    target=CommandTarget.PUMP,
                    action=CommandAction.RUN,
                    status=CommandStatus.FAILED,
                    message="pump relay fault",
                    created_at=now - timedelta(minutes=3),
                    sent_at=now - timedelta(minutes=3),
                    completed_at=now - timedelta(minutes=2),
                )
            )
            session.commit()

        summary_response = client.get(f"/api/devices/{device_id}/summary")

        assert summary_response.status_code == 200
        payload = summary_response.json()
        assert payload["hardware_health"]["heartbeat_status"] == "stale"
        assert payload["hardware_health"]["reading_status"] == "stale"
        assert payload["hardware_health"]["image_status"] == "offline"
        assert payload["hardware_health"]["camera_status"] == "offline"
        assert payload["hardware_health"]["primary"]["health_status"] == "stale"
        assert payload["hardware_health"]["cameras"][0]["health_status"] == "offline"
        assert payload["hardware_health"]["last_failed_command_reason"] == "pump relay fault"
        assert payload["hardware_health"]["last_failed_command_at"] is not None
        assert payload["hardware_health"]["last_successful_command_at"] is not None
    finally:
        teardown_overrides()


def test_device_setup_code_api_returns_handoff_urls(monkeypatch):
    client, _ = build_client_with_user()
    monkeypatch.setenv("PLANTLAB_DEVICE_PLATFORM_URL", "http://192.168.0.55:8000")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_PUBLIC_URL", "http://192.168.0.55:3000")
    get_settings.cache_clear()

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "serial_number": "SN-ESP32-001",
                "claim_token": "claim-esp32-001",
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            assert url.endswith("/api/devices/setup-code")
            assert json["serial_number"] == "SN-ESP32-001"
            assert json["device_name"] == "Kitchen Rose"
            assert json["location"] == "Kitchen"
            assert headers["x-plantlab-user-id"] == "1"
            return FakeResponse()

    monkeypatch.setattr(device_routes.httpx, "AsyncClient", FakeAsyncClient)

    try:
        response = client.post(
            "/api/devices/setup-code",
            headers={"Origin": "http://localhost:5173"},
            json={
                "serial_number": "SN-ESP32-001",
                "device_name": "Kitchen Rose",
                "location": "Kitchen",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["serial_number"] == "SN-ESP32-001"
        assert payload["claim_token"] == "claim-esp32-001"
        assert payload["setup_token"] == "claim-esp32-001"
        assert payload["provisioning_api_url"] == "http://192.168.0.55:3000"
        assert payload["platform_url"] == "http://192.168.0.55:8000"
        assert payload["setup_finishing_url"].startswith("http://localhost:5173/devices/setup-finishing?")
        assert "device_name=Kitchen+Rose" in payload["setup_finishing_url"]
        assert payload["continue_setup_url"].startswith("http://10.42.0.1:8080/?")
        assert "setup_code=claim-esp32-001" in payload["continue_setup_url"]
        assert "backend_url=http%3A%2F%2F192.168.0.55%3A3000" in payload["continue_setup_url"]
        assert "platform_url=http%3A%2F%2F192.168.0.55%3A8000" in payload["continue_setup_url"]
        assert "return_url=http%3A%2F%2Flocalhost%3A5173%2Fdevices%2Fsetup-finishing" in payload["continue_setup_url"]
    finally:
        get_settings.cache_clear()
        teardown_overrides()


def test_device_claim_token_api_proxies_ble_identity_and_returns_handoff(monkeypatch):
    client, _ = build_client_with_user()
    monkeypatch.setenv("PLANTLAB_DEVICE_PLATFORM_URL", "http://192.168.0.55:8000")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_PUBLIC_URL", "http://192.168.0.55:3000")
    get_settings.cache_clear()

    class FakeResponse:
        status_code = 201

        @staticmethod
        def json():
            return {
                "claim_token": "claim-ble-001",
                "setup_code": "claim-ble-001",
                "expected_device_id": "pl-esp32-a1b2c3",
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            assert url.endswith("/api/devices/claim-token")
            assert json["device_name"] == "Kitchen Rose"
            assert json["location"] == "Kitchen"
            assert json["device_identity"]["device_id"] == "pl-esp32-a1b2c3"
            assert json["device_identity"]["hardware_device_id"] == "pl-esp32-a1b2c3"
            assert json["device_identity"]["software_version"] == "1.2.3"
            assert json["device_identity"]["ble_name"] == "PlantLab-Setup-a1b2c3"
            assert headers["x-plantlab-user-id"] == "1"
            return FakeResponse()

    monkeypatch.setattr(device_routes.httpx, "AsyncClient", FakeAsyncClient)

    try:
        response = client.post(
            "/api/devices/claim-token",
            headers={"Origin": "http://localhost:5173"},
            json={
                "device_name": "Kitchen Rose",
                "location": "Kitchen",
                "device_identity": {
                    "source": "esp32-ble",
                    "schema_version": 1,
                    "device_id": " pl-esp32-a1b2c3 ",
                    "hardware_device_id": " pl-esp32-a1b2c3 ",
                    "hardware_model": "esp32_master",
                    "hardware_version": "ESP32-S3-DevKitC-1-N32R16V",
                    "software_version": "1.2.3",
                    "node_role": "master",
                    "display_name": "Master",
                    "ble_name": "PlantLab-Setup-a1b2c3",
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["serial_number"] is None
        assert payload["expected_device_id"] == "pl-esp32-a1b2c3"
        assert payload["claim_token"] == "claim-ble-001"
        assert payload["setup_token"] == "claim-ble-001"
        assert payload["provisioning_api_url"] == "http://192.168.0.55:3000"
        assert payload["platform_url"] == "http://192.168.0.55:8000"
        assert "serial_number=pl-esp32-a1b2c3" in payload["continue_setup_url"]
    finally:
        get_settings.cache_clear()
        teardown_overrides()


def test_register_provisioned_log_sanitizer_redacts_tokens_and_wifi_fields():
    sanitized = device_routes._sanitize_registration_log_payload(
        {
            "device_id": "pl-esp32-a1b2c3",
            "claim_token": "claim-secret",
            "device_access_token": "device-secret",
            "wifi_ssid": "HomeNetwork",
            "wifi_password": "wifi-secret",
            "nested": {
                "setup_token": "setup-secret",
                "password": "nested-secret",
                "ssid": "NestedNetwork",
            },
        }
    )

    assert sanitized["device_id"] == "pl-esp32-a1b2c3"
    assert sanitized["claim_token"] == "[redacted]"
    assert sanitized["device_access_token"] == "[redacted]"
    assert sanitized["wifi_ssid"] == "[omitted]"
    assert sanitized["wifi_password"] == "[redacted]"
    assert sanitized["nested"]["setup_token"] == "[redacted]"
    assert sanitized["nested"]["password"] == "[redacted]"
    assert sanitized["nested"]["ssid"] == "[omitted]"


def test_device_setup_code_api_surfaces_upstream_error(monkeypatch):
    client, _ = build_client_with_user()

    class FakeResponse:
        status_code = 404

        @staticmethod
        def json():
            return {"message": "Could not verify this SN."}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            return FakeResponse()

    monkeypatch.setattr(device_routes.httpx, "AsyncClient", FakeAsyncClient)

    try:
        response = client.post(
            "/api/devices/setup-code",
            json={
                "serial_number": "missing",
                "device_name": "Kitchen Rose",
            },
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "setup_code_request_failed"
        assert payload["error"]["message"] == "Could not verify this SN."
    finally:
        teardown_overrides()


def test_delete_device_api_releases_and_archives_device():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device = create_response.json()
        device_id = device["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            reading = SensorReading(device_id=device_id, moisture=42.0, temperature=21.0, humidity=50.0)
            image = Image(
                device_id=device_id,
                path="device-release/test.jpg",
                source_hardware_device_id="pl-esp32-release",
            )
            event = Event(device_id=device_id, type=EventType.PUMP, value="on")
            session.add_all([reading, image, event])
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-release",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.commit()
            reading_id = reading.id
            image_id = image.id
            event_id = event.id

        delete_response = client.delete(f"/api/devices/{device_id}")

        assert delete_response.status_code == 200
        assert delete_response.json() == {
            "status": "released",
            "device_id": device_id,
            "message": "Device released and archived.",
        }

        list_response = client.get("/api/devices")
        assert list_response.status_code == 200
        assert list_response.json() == []

        get_response = client.get(f"/api/devices/{device_id}")
        assert get_response.status_code == 404

        with next(app.dependency_overrides[get_session]()) as session:
            archived = session.get(Device, device_id)
            retained_image = session.get(Image, image_id)

            assert archived is not None
            assert archived.api_token is None
            assert archived.released_at is not None
            assert archived.archived_at is not None
            assert archived.release_reason == "user_removed"
            assert session.get(SensorReading, reading_id) is not None
            assert retained_image is not None
            assert retained_image.source_hardware_device_id is None
            assert session.get(Event, event_id) is not None
            assert session.get(DeviceNode, "pl-esp32-release") is None
    finally:
        teardown_overrides()


def test_release_device_api_revokes_token_detaches_hardware_and_preserves_history():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device = create_response.json()
        device_id = device["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            reading = SensorReading(device_id=device_id, moisture=35.0, temperature=22.0, humidity=45.0)
            image = Image(
                device_id=device_id,
                path="device-transfer/test.jpg",
                source_hardware_device_id="pl-esp32-transfer",
            )
            event = Event(device_id=device_id, type=EventType.LIGHT, value="off")
            session.add_all([reading, image, event])
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-transfer",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.commit()
            reading_id = reading.id
            image_id = image.id
            event_id = event.id

        release_response = client.post(f"/api/devices/{device_id}/release")

        assert release_response.status_code == 200
        payload = release_response.json()
        assert payload["status"] == "released"
        assert payload["device_id"] == device_id
        assert payload["released_at"] is not None
        assert "15 seconds" in payload["message"]

        assert client.get("/api/devices").json() == []
        assert client.get(f"/api/devices/{device_id}").status_code == 404

        with next(app.dependency_overrides[get_session]()) as session:
            released = session.get(Device, device_id)
            retained_image = session.get(Image, image_id)

            assert released is not None
            assert released.api_token is None
            assert released.release_reason == "owner_transfer"
            assert released.released_at is not None
            assert released.archived_at is not None
            assert session.get(DeviceNode, "pl-esp32-transfer") is None
            assert session.get(SensorReading, reading_id) is not None
            assert retained_image is not None
            assert retained_image.source_hardware_device_id is None
            assert session.get(Event, event_id) is not None

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        stale_token_response = client.post(
            f"/api/devices/{device_id}/status",
            json={"message": "should not be accepted"},
            headers={"X-Device-Token": device["api_token"]},
        )
        assert stale_token_response.status_code == 401
    finally:
        teardown_overrides()


def test_device_token_factory_reset_releases_instead_of_deleting_history():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device = create_response.json()
        device_id = device["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            reading = SensorReading(device_id=device_id, moisture=39.0, temperature=23.0, humidity=47.0)
            session.add(reading)
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-local-reset",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.commit()
            reading_id = reading.id

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        reset_response = client.post(
            f"/api/devices/{device_id}/factory-reset",
            headers={"X-Device-Token": device["api_token"]},
        )
        second_reset_response = client.post(
            f"/api/devices/{device_id}/factory-reset",
            headers={"X-Device-Token": device["api_token"]},
        )

        assert reset_response.status_code == 200
        assert reset_response.json() == {"ok": True, "device_id": device_id, "status": "released"}
        assert second_reset_response.status_code == 401

        with next(app.dependency_overrides[get_session]()) as session:
            released = session.get(Device, device_id)
            assert released is not None
            assert released.api_token is None
            assert released.release_reason == "device_factory_reset"
            assert released.released_at is not None
            assert released.archived_at is not None
            assert session.get(SensorReading, reading_id) is not None
            assert session.get(DeviceNode, "pl-esp32-local-reset") is None
    finally:
        teardown_overrides()


def test_setup_status_api_reports_readiness():
    client, _ = build_client_with_user()
    try:
        create_response = client.post(
            "/api/devices",
            json={"name": "Device 1", "location": "Location 1"},
        )
        device_id = create_response.json()["id"]

        pending_response = client.get("/api/setup/status", params={"device_name": "Device 1", "location": "Location 1"})
        assert pending_response.status_code == 200
        pending_payload = pending_response.json()
        assert pending_payload["ready"] is False
        assert pending_payload["device_found"] is True
        assert pending_payload["has_reading"] is False
        assert pending_payload["has_image"] is False

        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 41.0,
                "temperature": 23.4,
                "humidity": 52.5,
                "light_on": False,
                "pump_on": False,
                "pump_status": "idle",
            },
        )
        assert data_response.status_code == 201

        ready_response = client.get(
            "/api/setup/status",
            params={"device_name": "Device 1", "location": "Location 1", "expect_image": "0"},
        )
        assert ready_response.status_code == 200
        ready_payload = ready_response.json()
        assert ready_payload["ready"] is True
        assert ready_payload["device_id"] == device_id
        assert ready_payload["redirect_path"] == f"/devices/{device_id}?setup=complete"
    finally:
        teardown_overrides()


def test_setup_status_api_matches_expected_device_id_and_reports_online():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Smart Planter"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-a1b2c3",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=datetime.now(timezone.utc),
            )

        response = client.get(
            "/api/setup/status",
            params={"expected_device_id": "pl-esp32-a1b2c3", "device_name": "Smart Planter"},
        )

        assert response.status_code == 200
        assert "no-store" in response.headers["cache-control"]
        payload = response.json()
        assert payload["device_found"] is True
        assert payload["device_id"] == device_id
        assert payload["online"] is True
        assert payload["status"] == "online"
        assert payload["last_heartbeat_at"] is not None
        assert payload["ready"] is False
        assert payload["has_reading"] is False
        assert payload["has_image"] is False
        assert payload["expect_image"] is False
        assert payload["redirect_path"] is None
    finally:
        teardown_overrides()


def test_setup_status_api_expected_device_id_requires_primary_node_match():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Smart Planter"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-a1b2c3",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        response = client.get("/api/setup/status", params={"expected_device_id": "pl-esp32-a1b2c3"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is False
        assert payload["device_id"] is None
        assert payload["online"] is False
        assert payload["ready"] is False
    finally:
        teardown_overrides()


def test_setup_status_api_expected_device_id_does_not_fall_back_to_name():
    client, _ = build_client_with_user()
    try:
        create_response = client.post("/api/devices", json={"name": "Smart Planter"})
        device_id = create_response.json()["id"]

        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pl-esp32-existing",
                node_role="master",
                display_name="Master",
                status="online",
                last_seen_at=datetime.now(timezone.utc),
            )

        response = client.get(
            "/api/setup/status",
            params={
                "expected_device_id": "pl-esp32-new",
                "device_name": "Smart Planter",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is False
        assert payload["device_id"] is None
        assert payload["online"] is False
        assert payload["ready"] is False
    finally:
        teardown_overrides()


def test_device_detail_page_shows_latest_data():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]

        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 42.5,
                "temperature": 22.2,
                "humidity": 51.0,
                "water_temperature_c": 19.9,
                "water_level_raw": 35110,
                "water_level_state": "ok",
                "light_on": True,
                "pump_on": False,
                "pump_status": "not_needed",
            },
        )
        assert data_response.status_code == 201
        command_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "pump", "action": "run", "value": "10"},
        )
        assert command_response.status_code == 201

        detail_response = client.get(f"/devices/{device_id}")

        assert detail_response.status_code == 200
        assert "Kitchen Rose" in detail_response.text
        assert f'data-summary-url="/devices/{device_id}/summary.json"' in detail_response.text
        assert "42.5%" in detail_response.text
        assert "Recent Trends" in detail_response.text
        assert "Last 24 hours" in detail_response.text
        assert "?range=1h" in detail_response.text
        assert "?range=7d" in detail_response.text
        assert "Device Controls" in detail_response.text
        assert "Stop" in detail_response.text
        assert "Pump run 10s" in detail_response.text
        assert "data-command-key=\"pump:run:10\"" in detail_response.text
        assert "data-light-switch" in detail_response.text
        assert "light-toggle-switch" in detail_response.text
        assert "light-toggle-slider" in detail_response.text
        assert "data-switch-state" in detail_response.text
        assert "Turn on" not in detail_response.text
        assert "Turn off" not in detail_response.text
        assert "Waiting" in detail_response.text
        assert "Last seen from sensor reading" in detail_response.text
        assert "data-auto-refresh" not in detail_response.text
        assert "Online" in detail_response.text
        assert "42.5%" in detail_response.text
        assert "22.2 C" in detail_response.text
        assert "51.0%" in detail_response.text
        assert "19.9 C" in detail_response.text
        assert "ok (35110)" in detail_response.text
    finally:
        teardown_overrides()


def test_device_detail_page_formats_initial_soil_moisture_value():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]

        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 29.05556,
                "temperature": 23.0,
                "humidity": 53.1,
                "light_on": False,
                "pump_on": False,
                "pump_status": "idle",
            },
        )
        assert data_response.status_code == 201

        detail_response = client.get(f"/devices/{device_id}")

        assert detail_response.status_code == 200
        assert "29.1%" in detail_response.text
        assert "29.05556" not in detail_response.text
    finally:
        teardown_overrides()


def test_device_summary_json_returns_latest_status():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]
        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 41.0,
                "temperature": 23.4,
                "humidity": 52.5,
                "water_temperature_c": 20.2,
                "water_level_raw": 34950,
                "water_level_state": "ok",
                "light_on": False,
                "pump_on": False,
                "pump_status": "not_needed",
            },
        )
        assert data_response.status_code == 201

        response = client.get(f"/devices/{device_id}/summary.json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["latest_reading"]["moisture"] == "41.0%"
        assert payload["latest_reading"]["temperature"] == "23.4 C"
        assert payload["latest_reading"]["water_temperature"] == "20.2 C"
        assert payload["latest_reading"]["water_level"] == "ok (34950)"
        assert payload["latest_reading"]["light"] == "off"
        assert payload["connection"]["label"] == "Online"
        assert payload["connection"]["source"] == "Last seen from sensor reading"
        assert payload["active_command_keys"] == []
        assert payload["recent_images"] == []
    finally:
        teardown_overrides()


def test_device_summary_uses_command_ack_state_without_new_sensor_reading():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={"name": "Kitchen Rose"},
        )
        device_id = create_response.json()["id"]
        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 41.0,
                "temperature": 23.4,
                "humidity": 52.5,
                "light_on": False,
                "pump_on": False,
            },
        )
        assert data_response.status_code == 201
        command_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "light", "action": "on"},
        )
        command_id = command_response.json()["id"]

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        ack_response = client.post(
            f"/api/devices/{device_id}/commands/{command_id}/ack",
            json={"status": "completed", "message": "light turned on", "light_on": True, "pump_on": False},
            headers={"X-Device-Token": create_response.json()["api_token"]},
        )
        assert ack_response.status_code == 200

        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="grower@example.com", name="Grower")
        app.dependency_overrides[get_optional_current_user] = app.dependency_overrides[get_current_user]
        response = client.get(f"/devices/{device_id}/summary.json")

        assert response.status_code == 200
        assert response.json()["latest_reading"]["light"] == "on"
    finally:
        teardown_overrides()


def test_device_status_heartbeat_overrides_stale_reading_state():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post("/api/devices", json={"name": "Kitchen Rose"})
        device = create_response.json()
        device_id = device["id"]
        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 41.0,
                "temperature": 23.4,
                "humidity": 52.5,
                "light_on": False,
                "pump_on": False,
            },
        )
        assert data_response.status_code == 201

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        status_response = client.post(
            f"/api/devices/{device_id}/status",
            json={"light_on": True, "pump_on": False, "message": "device online"},
            headers={"X-Device-Token": device["api_token"]},
        )
        assert status_response.status_code == 200

        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="grower@example.com", name="Grower")
        app.dependency_overrides[get_optional_current_user] = app.dependency_overrides[get_current_user]
        response = client.get(f"/devices/{device_id}/summary.json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["latest_reading"]["light"] == "on"
        assert payload["latest_reading"]["pump"] == "off"
        assert payload["connection"]["source"] == "Last seen from device online"
    finally:
        teardown_overrides()


def test_latest_device_activity_uses_reading_image_and_device_command_timestamps():
    device = SimpleNamespace(status_updated_at=None, status_message=None)
    reading = SimpleNamespace(timestamp=datetime(2026, 4, 13, 19, 0, tzinfo=timezone.utc))
    image = SimpleNamespace(timestamp=datetime(2026, 4, 13, 19, 5, tzinfo=timezone.utc))
    command = SimpleNamespace(
        sent_at=datetime(2026, 4, 13, 19, 8, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 13, 19, 10, tzinfo=timezone.utc),
    )

    activity = _latest_device_activity(device, reading, image, [command])

    assert activity is not None
    assert activity["source"] == "command"
    assert activity["description"] == "command response"


def test_completed_command_overrides_stale_reading_state():
    reading_time = datetime(2026, 4, 16, 19, 0, tzinfo=timezone.utc)
    command = SimpleNamespace(
        target="light",
        action="on",
        status="completed",
        light_on=True,
        pump_on=None,
        created_at=reading_time,
        completed_at=datetime(2026, 4, 16, 19, 1, tzinfo=timezone.utc),
    )

    state = _latest_completed_command_state([command], reading_time)

    assert state["light"] is True


def test_reading_chart_summarizes_available_readings():
    readings = [
        SimpleNamespace(
            moisture=float(index),
            temperature=20.0 + index,
            humidity=40.0 + index,
            water_temperature_c=18.0 + index,
            water_level_raw=35000 + index,
            timestamp=datetime(2026, 4, 13, 19, index, tzinfo=timezone.utc),
        )
        for index in range(25)
    ]

    chart = _reading_chart(readings)
    chart_keys = {metric["key"] for metric in chart}
    moisture_chart = chart[0]
    water_temperature_chart = next(metric for metric in chart if metric["key"] == "water_temperature_c")

    assert "water_level_raw" not in chart_keys
    assert len(moisture_chart["points"]) == 25
    assert moisture_chart["points"][0]["value"] == 24.0
    assert moisture_chart["points"][-1]["value"] == 0.0
    assert moisture_chart["minimum"] == 0.0
    assert moisture_chart["maximum"] == 24.0
    assert moisture_chart["average"] == 12.0
    assert len(water_temperature_chart["points"]) == 25
    assert water_temperature_chart["points"][0]["value"] == 42.0
    assert water_temperature_chart["points"][-1]["value"] == 18.0


def test_reading_chart_downsamples_large_ranges():
    readings = [
        SimpleNamespace(
            moisture=float(index),
            temperature=20.0 + index,
            humidity=40.0 + index,
            timestamp=datetime(2026, 4, 13, 19, index % 60, tzinfo=timezone.utc),
        )
        for index in range(75)
    ]

    chart = _reading_chart(readings, max_points=20)
    moisture_chart = chart[0]

    assert len(moisture_chart["points"]) == 20
    assert moisture_chart["point_count"] == 20
    assert moisture_chart["points"][0]["value"] == 74.0
    assert moisture_chart["points"][-1]["value"] == 0.0


def test_devices_page_renders_for_signed_in_user():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        response = client.get("/devices")
        assert response.status_code == 200
        assert "Legacy web:" in response.text
        assert "Your Plant Devices" in response.text
    finally:
        teardown_overrides()


def test_devices_page_shows_latest_values_on_cards():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Kitchen Rose",
                "plant_type": "Rose",
                "location": "Kitchen window",
            },
        )
        device_id = create_response.json()["id"]
        data_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 44.4,
                "temperature": 21.8,
                "humidity": 53.2,
                "light_on": True,
                "pump_on": False,
            },
        )
        assert data_response.status_code == 201

        response = client.get("/devices")

        assert response.status_code == 200
        assert "Kitchen Rose" in response.text
        assert "44.4%" in response.text
        assert "21.8 C" in response.text
        assert "53.2%" in response.text
        assert "No image yet" in response.text
        assert "Online" in response.text
    finally:
        teardown_overrides()


def test_legacy_devices_add_page_redirects_to_device_list():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        create_response = client.post(
            "/api/devices",
            json={
                "name": "Device 1",
                "plant_type": "Plant 1",
            },
        )
        assert create_response.status_code == 201

        response = client.get("/devices/add", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/devices"
    finally:
        teardown_overrides()
