import os

os.environ["PLANTLAB_SKIP_DOTENV"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_session
from app.main import app
from app.models import Command, Device, User
from app.models.base import Base
from app.services.demo import DEMO_DEVICE_ID, reset_demo_states_for_tests


def make_demo_client():
    reset_demo_states_for_tests()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), override_session


def teardown() -> None:
    app.dependency_overrides.clear()
    reset_demo_states_for_tests()


def demo_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "standalone"
    assert payload["user"]["email"] == "demo@plantlab.local"
    assert payload["user"]["is_demo_user"] is True
    assert payload["access_token"]
    assert payload["refresh_token"]
    return {"Authorization": f"Bearer {payload['access_token']}"}


def test_demo_login_marks_user_and_exposes_one_synthetic_device():
    client, override_session = make_demo_client()
    try:
        headers = demo_headers(client)

        me_response = client.get("/api/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["user"]["is_demo_user"] is True

        list_response = client.get("/api/devices", headers=headers)
        assert list_response.status_code == 200
        devices = list_response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == DEMO_DEVICE_ID
        assert devices[0]["name"] == "PlantLab Demo Garden"
        assert devices[0]["plant_type"] == "Genovese basil"
        assert devices[0]["status"] == "online"

        with next(override_session()) as session:
            user = session.query(User).filter(User.email == "demo@plantlab.local").one()
            assert user.is_demo_user is True
            assert session.query(Device).count() == 0
            assert session.query(Command).count() == 0
    finally:
        teardown()


def test_demo_account_blocks_real_provisioning_deletion_ota_and_account_delete():
    client, _override_session = make_demo_client()
    try:
        headers = demo_headers(client)

        blocked_requests = [
            client.post("/api/devices", json={"name": "Real Plant"}, headers=headers),
            client.post("/api/devices/setup-code", json={"serial_number": "SN123", "device_name": "Real Plant"}, headers=headers),
            client.post(
                "/api/devices/claim-token",
                json={
                    "device_name": "Real Plant",
                    "device_identity": {
                        "source": "ble",
                        "schema_version": 1,
                        "device_id": "pl-esp32-real",
                        "hardware_device_id": "pl-esp32-real",
                    },
                },
                headers=headers,
            ),
            client.delete(f"/api/devices/{DEMO_DEVICE_ID}", headers=headers),
            client.post(f"/api/devices/{DEMO_DEVICE_ID}/commands", json={"target": "ota", "action": "start"}, headers=headers),
            client.delete("/api/me", headers=headers),
        ]

        for response in blocked_requests:
            assert response.status_code == 403
    finally:
        teardown()


def test_demo_static_product_data_covers_dashboard_history_images_diagnostics_and_timeline():
    client, _override_session = make_demo_client()
    try:
        headers = demo_headers(client)

        summary = client.get(f"/api/devices/{DEMO_DEVICE_ID}/summary", headers=headers)
        assert summary.status_code == 200
        summary_payload = summary.json()
        assert summary_payload["latest_reading"]["water_level_state"] == "ok"
        assert summary_payload["latest_reading"]["temperature"] is not None
        assert summary_payload["latest_reading"]["humidity"] is not None
        assert summary_payload["current_light_intensity_percent"] == 72
        assert summary_payload["hardware_health"]["overall_status"] == "online"
        assert summary_payload["hardware_health"]["primary"]["capabilities"]["light_intensity_control"] is True
        assert summary_payload["hardware_health"]["cameras"]

        readings = client.get(f"/api/devices/{DEMO_DEVICE_ID}/readings?limit=8", headers=headers)
        assert readings.status_code == 200
        reading_rows = readings.json()
        assert len(reading_rows) == 8
        assert len({row["water_level_raw"] for row in reading_rows}) > 1

        images = client.get(f"/api/devices/{DEMO_DEVICE_ID}/images?limit=6", headers=headers)
        assert images.status_code == 200
        assert len(images.json()) == 6

        image_response = client.get(f"/api/devices/demo/images/{images.json()[0]['id']}")
        assert image_response.status_code == 200
        assert image_response.headers["content-type"] == "image/png"

        timelapse = client.get(f"/api/devices/{DEMO_DEVICE_ID}/timelapse", headers=headers)
        assert timelapse.status_code == 200
        assert timelapse.json()["frame_count"] >= 2

        diagnostics = client.get(f"/api/devices/{DEMO_DEVICE_ID}/diagnostics", headers=headers)
        assert diagnostics.status_code == 200
        assert len(diagnostics.json()["snapshots"]) == 2
        assert diagnostics.json()["recent_events"]

        timeline = client.get(f"/api/devices/{DEMO_DEVICE_ID}/timeline", headers=headers)
        assert timeline.status_code == 200
        event_types = {event["event_type"] for event in timeline.json()["events"]}
        assert "GROWTH_MILESTONE" in event_types
        assert "WATERING_EVENT" in event_types
        assert "ALERT_RESOLVED" in event_types
    finally:
        teardown()


def test_demo_simulated_commands_update_fake_state_without_real_command_rows():
    client, override_session = make_demo_client()
    try:
        headers = demo_headers(client)

        light_response = client.post(
            f"/api/devices/{DEMO_DEVICE_ID}/commands/light",
            json={"intensity_percent": 35},
            headers=headers,
        )
        assert light_response.status_code == 201
        assert light_response.json()["command_status"] == "completed"

        summary_response = client.get(f"/api/devices/{DEMO_DEVICE_ID}/summary", headers=headers)
        assert summary_response.status_code == 200
        assert summary_response.json()["current_light_intensity_percent"] == 35

        capture_response = client.post(f"/api/devices/{DEMO_DEVICE_ID}/commands/capture", headers=headers)
        assert capture_response.status_code == 201
        assert capture_response.json()["command_status"] == "completed"

        commands_response = client.get(f"/api/devices/{DEMO_DEVICE_ID}/commands", headers=headers)
        assert commands_response.status_code == 200
        commands = commands_response.json()
        assert commands[0]["target"] == "camera"
        assert commands[0]["status"] == "completed"
        assert any(command["target"] == "grow_light" for command in commands)

        diagnostics_response = client.post(
            f"/api/devices/{DEMO_DEVICE_ID}/commands",
            json={"target": "diagnostics", "action": "request"},
            headers=headers,
        )
        assert diagnostics_response.status_code == 201
        assert diagnostics_response.json()["target"] == "diagnostics"

        timeline_response = client.get(f"/api/devices/{DEMO_DEVICE_ID}/timeline", headers=headers)
        assert timeline_response.status_code == 200
        assert timeline_response.json()["events"][0]["event_type"] == "DIAGNOSTICS_RECEIVED"

        with next(override_session()) as session:
            assert session.query(Device).count() == 0
            assert session.query(Command).count() == 0
    finally:
        teardown()
