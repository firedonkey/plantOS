from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from platform_app.api.deps import get_current_user
from platform_app.core.settings import get_settings
from platform_app.db.session import get_session
from platform_app.main import app
from platform_app.models import Device, User
from platform_app.models.base import Base


def build_client_with_device(upload_dir: str) -> tuple[TestClient, int, int]:
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
    get_settings.cache_clear()
    return TestClient(app), device_id, other_device_id


def teardown_overrides() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_image_upload_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/image",
        data={"device_id": "1"},
        files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 401


def test_upload_image_for_owned_device(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        saved_path = tmp_path / f"device-{device_id}"
        assert saved_path.exists()
        assert len(list(saved_path.glob("*.jpg"))) == 1
    finally:
        teardown_overrides()


def test_upload_image_rejects_other_users_device(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, _, other_device_id = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(other_device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
        )

        assert response.status_code == 404
    finally:
        teardown_overrides()


def test_upload_image_rejects_non_image_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("notes.txt", b"not-an-image", "text/plain")},
        )

        assert response.status_code == 400
    finally:
        teardown_overrides()
