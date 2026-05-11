from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.api.routes.auth as auth_routes
from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import User
from app.models.base import Base
from app.services.users import get_user_by_id, upsert_google_user


def test_google_login_reports_missing_config(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client = TestClient(app)
    response = client.get("/auth/login")

    assert response.status_code == 503
    assert "Google sign-in is not configured" in response.json()["detail"]
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()


def test_me_reports_anonymous_user():
    client = TestClient(app)
    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


def test_dev_login_returns_bearer_token_and_me_works(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DEV_TOKEN_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)

    client = TestClient(app)
    try:
        login_response = client.post(
            "/api/auth/login",
            json={"email": "dev@plantlab.local", "password": "password"},
        )

        assert login_response.status_code == 200
        payload = login_response.json()
        assert payload["mode"] == "api"
        assert payload["email"] == "dev@plantlab.local"
        assert payload["token"]

        with next(override_session()) as session:
            user = session.query(User).filter(User.email == "dev@plantlab.local").one()
            assert user.name == "Dev"

        me_response = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["authenticated"] is True
        assert me_response.json()["user"]["email"] == "dev@plantlab.local"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_dev_login_rejected_when_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLANTLAB_DEV_TOKEN_AUTH_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.setenv("APP_SECRET_KEY", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "dev@plantlab.local", "password": "password"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Dev-only token auth is disabled."
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_dev_bearer_token_can_access_device_endpoints(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DEV_TOKEN_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)

    client = TestClient(app)
    try:
        login_response = client.post(
            "/api/auth/login",
            json={"email": "dev@plantlab.local", "password": "password"},
        )
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = client.post(
            "/api/devices",
            json={"name": "Mobile Rose", "location": "Desk"},
            headers=headers,
        )
        assert create_response.status_code == 201
        device_id = create_response.json()["id"]

        reading_response = client.post(
            "/api/data",
            json={
                "device_id": device_id,
                "moisture": 41.0,
                "temperature": 21.5,
                "humidity": 49.5,
                "light_on": False,
                "pump_on": False,
            },
            headers=headers,
        )
        assert reading_response.status_code == 201

        list_response = client.get("/api/devices", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        summary_response = client.get(f"/api/devices/{device_id}/summary", headers=headers)
        assert summary_response.status_code == 200
        assert summary_response.json()["latest_reading"]["temperature"] == 21.5
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_upsert_google_user_creates_and_updates_user():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = upsert_google_user(
            session,
            google_sub="google-123",
            email="grower@example.com",
            name="Plant Grower",
            avatar_url="https://example.com/avatar.jpg",
        )
        assert user.id is not None
        assert user.password_hash is None

        updated = upsert_google_user(
            session,
            google_sub="google-123",
            email="grower@example.com",
            name="Rose Grower",
            avatar_url="https://example.com/rose.jpg",
        )

        assert updated.id == user.id
        assert updated.name == "Rose Grower"
        assert updated.avatar_url == "https://example.com/rose.jpg"
