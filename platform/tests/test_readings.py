from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.session import get_session
from app.main import app
from app.models import Device, SensorReading, User
from app.models.base import Base


def build_client_with_data() -> tuple[TestClient, int, int]:
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

        device = Device(user_id=user.id, name="Kitchen Rose")
        other_device = Device(user_id=other_user.id, name="Other Rose")
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
    return TestClient(app), device_id, other_device_id


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def test_ingest_sensor_data_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/data",
        json={"device_id": 1, "moisture": 42.0},
    )

    assert response.status_code == 401


def test_ingest_sensor_data_for_owned_device():
    client, device_id, _ = build_client_with_data()
    try:
        timestamp = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
        response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 42.5,
                "temperature": 22.2,
                "humidity": 51.0,
                "timestamp": timestamp.isoformat(),
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["moisture"] == 42.5
        assert payload["temperature"] == 22.2
        assert payload["humidity"] == 51.0
    finally:
        teardown_overrides()


def test_ingest_sensor_data_rejects_other_users_device():
    client, _, other_device_id = build_client_with_data()
    try:
        response = client.post(
            "/api/data",
            json={"device_id": other_device_id, "moisture": 42.0},
        )

        assert response.status_code == 404
    finally:
        teardown_overrides()
