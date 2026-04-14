from collections.abc import Generator
from base64 import b64encode
from datetime import datetime, timezone
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import User
from app.models.base import Base
from app.web.routes import _latest_device_activity, _reading_chart


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
        assert len(list_response.json()) == 1

        get_response = client.get(f"/api/devices/{created['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["location"] == "Kitchen window"
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
                "light_on": True,
                "pump_on": False,
                "pump_status": "not_needed",
            },
        )
        assert data_response.status_code == 201
        command_response = client.post(
            f"/api/devices/{device_id}/commands",
            json={"target": "pump", "action": "run", "value": "5"},
        )
        assert command_response.status_code == 201

        detail_response = client.get(f"/devices/{device_id}")

        assert detail_response.status_code == 200
        assert "Kitchen Rose" in detail_response.text
        assert "42.5%" in detail_response.text
        assert "Recent Trends" in detail_response.text
        assert "Device Controls" in detail_response.text
        assert "Stop" in detail_response.text
        assert "Pump run 5s" in detail_response.text
        assert "Waiting" in detail_response.text
        assert "Last seen from sensor reading" in detail_response.text
        assert "data-auto-refresh=\"5000\"" in detail_response.text
        assert "Auto refresh every 5 seconds" not in detail_response.text
    finally:
        teardown_overrides()


def test_latest_device_activity_uses_reading_image_and_device_command_timestamps():
    reading = SimpleNamespace(timestamp=datetime(2026, 4, 13, 19, 0, tzinfo=timezone.utc))
    image = SimpleNamespace(timestamp=datetime(2026, 4, 13, 19, 5, tzinfo=timezone.utc))
    command = SimpleNamespace(
        sent_at=datetime(2026, 4, 13, 19, 8, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 13, 19, 10, tzinfo=timezone.utc),
    )

    activity = _latest_device_activity(reading, image, [command])

    assert activity is not None
    assert activity["source"] == "command"
    assert activity["description"] == "command response"


def test_reading_chart_uses_last_20_readings_and_summaries():
    readings = [
        SimpleNamespace(
            moisture=float(index),
            temperature=20.0 + index,
            humidity=40.0 + index,
            timestamp=datetime(2026, 4, 13, 19, index, tzinfo=timezone.utc),
        )
        for index in range(25)
    ]

    chart = _reading_chart(readings)
    moisture_chart = chart[0]

    assert len(moisture_chart["points"]) == 20
    assert moisture_chart["points"][0]["value"] == 19.0
    assert moisture_chart["points"][-1]["value"] == 0.0
    assert moisture_chart["minimum"] == 0.0
    assert moisture_chart["maximum"] == 19.0
    assert moisture_chart["average"] == 9.5


def test_devices_page_renders_for_signed_in_user():
    client, _ = build_client_with_user(set_session_cookie=True)
    try:
        response = client.get("/devices")
        assert response.status_code == 200
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


def test_devices_page_prefills_next_device_defaults():
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

        response = client.get("/devices")

        assert response.status_code == 200
        assert 'value="Device 2"' in response.text
        assert 'value="Plant 2"' in response.text
        assert 'value="Location 2"' in response.text
    finally:
        teardown_overrides()
