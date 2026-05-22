from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.api.routes.auth as auth_routes
from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import Device, SensorReading, User
from app.models.base import Base
from app.services.standalone_auth import create_handoff_code, create_refresh_session, issue_access_token
from app.services.users import get_user_by_id, upsert_google_user


def make_test_client():
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
    return TestClient(app), override_session


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


def test_standalone_google_start_reports_missing_config(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client = TestClient(app)
    response = client.get("/api/auth/google/start?client=web&return_to=/login")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "google_auth_not_configured",
            "message": "Google sign-in is not configured for standalone auth.",
            "details": {},
        }
    }
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

    client, override_session = make_test_client()
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

    client, _override_session = make_test_client()
    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "dev@plantlab.local", "password": "password"},
        )
        assert response.status_code == 403
        assert response.json() == {
            "error": {
                "code": "dev_token_auth_disabled",
                "message": "Dev-only token auth is disabled.",
                "details": {},
            }
        }
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_api_validation_errors_use_standard_error_shape(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DEV_TOKEN_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, _override_session = make_test_client()
    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "dev@plantlab.local"},
        )
        assert response.status_code == 422
        payload = response.json()
        assert payload["error"]["code"] == "validation_error"
        assert payload["error"]["message"] == "Request validation failed."
        assert payload["error"]["details"]["errors"]
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_dev_bearer_token_can_access_device_endpoints(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DEV_TOKEN_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, _override_session = make_test_client()
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


def test_mobile_apple_login_returns_standalone_session(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    monkeypatch.setenv("PLANTLAB_APPLE_CLIENT_ID", "com.plantlab.mobile")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    def fake_verify_apple_identity_token(identity_token: str, *, audience: str):
        assert identity_token == "apple.identity.token"
        assert audience == "com.plantlab.mobile"
        return SimpleNamespace(sub="apple-sub-123", email="apple@example.com", email_verified=True)

    monkeypatch.setattr(auth_routes, "verify_apple_identity_token", fake_verify_apple_identity_token)
    client, override_session = make_test_client()
    try:
        response = client.post(
            "/api/auth/apple/mobile",
            json={
                "identity_token": "apple.identity.token",
                "full_name": "Apple Grower",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["access_token"]
        assert payload["refresh_token"]
        assert payload["user"]["email"] == "apple@example.com"
        assert payload["user"]["name"] == "Apple Grower"

        with next(override_session()) as session:
            user = session.query(User).filter(User.email == "apple@example.com").one()
            assert user.apple_sub == "apple-sub-123"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_mobile_apple_login_requires_email_for_first_login(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    def fake_verify_apple_identity_token(identity_token: str, *, audience: str):
        return SimpleNamespace(sub="apple-no-email", email=None, email_verified=False)

    monkeypatch.setattr(auth_routes, "verify_apple_identity_token", fake_verify_apple_identity_token)
    client, _override_session = make_test_client()
    try:
        response = client.post(
            "/api/auth/apple/mobile",
            json={"identity_token": "apple.identity.token"},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "apple_email_required"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_refresh_rotates_cookie_and_old_token_fails(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    monkeypatch.setenv("PLANTLAB_STANDALONE_REFRESH_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="grower@example.com", name="Grower")
            session.add(user)
            session.commit()
            session.refresh(user)
            refresh_bundle = create_refresh_session(get_settings(), session, user.id)

        client.cookies.set(get_settings().standalone_refresh_cookie_name, refresh_bundle.token)
        response = client.post("/api/auth/refresh")

        assert response.status_code == 200
        payload = response.json()
        assert payload["access_token"]
        assert payload["token_type"] == "bearer"
        assert payload["mode"] == "standalone"
        assert payload["user"]["email"] == "grower@example.com"
        assert payload["refresh_token"] is None

        client.cookies.set(get_settings().standalone_refresh_cookie_name, refresh_bundle.token)
        old_response = client.post("/api/auth/refresh")
        assert old_response.status_code == 401
        assert old_response.json()["error"]["code"] == "invalid_refresh"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_refresh_accepts_body_token_for_mobile(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="mobile@example.com", name="Mobile User")
            session.add(user)
            session.commit()
            session.refresh(user)
            refresh_bundle = create_refresh_session(get_settings(), session, user.id)

        response = client.post("/api/auth/refresh", json={"refresh_token": refresh_bundle.token})

        assert response.status_code == 200
        payload = response.json()
        assert payload["access_token"]
        assert payload["mode"] == "standalone"
        assert payload["user"]["email"] == "mobile@example.com"
        assert payload["refresh_token"]
        assert payload["refresh_token"] != refresh_bundle.token

        old_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_bundle.token})
        assert old_response.status_code == 401
        assert old_response.json()["error"]["code"] == "invalid_refresh"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_refresh_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, _override_session = make_test_client()
    try:
        response = client.post("/api/auth/refresh")

        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "invalid_refresh",
                "message": "Refresh session is missing, expired, or revoked.",
                "details": {},
            }
        }
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_refresh_exchanges_handoff_code_once(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="handoff@example.com", name="Handoff User")
            session.add(user)
            session.commit()
            session.refresh(user)
            handoff_code = create_handoff_code(session, user.id)

        response = client.post("/api/auth/refresh", json={"handoff_code": handoff_code})

        assert response.status_code == 200
        payload = response.json()
        assert payload["access_token"]
        assert payload["refresh_token"]
        assert payload["user"]["email"] == "handoff@example.com"

        repeat_response = client.post("/api/auth/refresh", json={"handoff_code": handoff_code})
        assert repeat_response.status_code == 401
        assert repeat_response.json()["error"]["code"] == "invalid_refresh"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_logout_is_idempotent_and_revokes_refresh(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    monkeypatch.setenv("PLANTLAB_STANDALONE_REFRESH_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="logout@example.com", name="Logout")
            session.add(user)
            session.commit()
            session.refresh(user)
            refresh_bundle = create_refresh_session(get_settings(), session, user.id)

        client.cookies.set(get_settings().standalone_refresh_cookie_name, refresh_bundle.token)
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        repeat_response = client.post("/api/auth/logout")
        assert repeat_response.status_code == 200
        assert repeat_response.json() == {"ok": True}

        client.cookies.set(get_settings().standalone_refresh_cookie_name, refresh_bundle.token)
        refresh_response = client.post("/api/auth/refresh")
        assert refresh_response.status_code == 401
        assert refresh_response.json()["error"]["code"] == "invalid_refresh"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_standalone_logout_revokes_body_refresh_token(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="mobile-logout@example.com", name="Mobile Logout")
            session.add(user)
            session.commit()
            session.refresh(user)
            refresh_bundle = create_refresh_session(get_settings(), session, user.id)

        response = client.post("/api/auth/logout", json={"refresh_token": refresh_bundle.token})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        repeat_response = client.post("/api/auth/logout", json={"refresh_token": refresh_bundle.token})
        assert repeat_response.status_code == 200
        assert repeat_response.json() == {"ok": True}

        refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_bundle.token})
        assert refresh_response.status_code == 401
        assert refresh_response.json()["error"]["code"] == "invalid_refresh"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_me_accepts_standalone_access_token(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="token@example.com", name="Token User")
            session.add(user)
            session.commit()
            session.refresh(user)
            access = issue_access_token(get_settings(), user.id)

        response = client.get("/api/me", headers={"Authorization": f"Bearer {access.token}"})

        assert response.status_code == 200
        assert response.json()["authenticated"] is True
        assert response.json()["user"]["email"] == "token@example.com"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_delete_me_removes_user_devices_and_revokes_refresh_sessions(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "standalone-test-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    client, override_session = make_test_client()
    try:
        with next(override_session()) as session:
            user = User(email="delete-me@example.com", name="Delete Me")
            session.add(user)
            session.commit()
            session.refresh(user)
            device = Device(user_id=user.id, name="Delete Test", api_token="delete-token")
            session.add(device)
            session.commit()
            session.refresh(device)
            session.add(SensorReading(device_id=device.id, temperature=22.0))
            refresh_bundle = create_refresh_session(get_settings(), session, user.id)
            access = issue_access_token(get_settings(), user.id)
            session.commit()
            user_id = user.id
            device_id = device.id

        response = client.delete("/api/me", headers={"Authorization": f"Bearer {access.token}"})

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_bundle.token})
        assert refresh_response.status_code == 401

        with next(override_session()) as session:
            assert session.get(User, user_id) is None
            assert session.get(Device, device_id) is None
            assert session.query(SensorReading).filter(SensorReading.device_id == device_id).count() == 0
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()


def test_old_google_callback_still_sets_session_auth(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "google-secret")
    get_settings.cache_clear()
    auth_routes.get_settings.cache_clear()

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "sub": "google-old-session",
                "email": "old-session@example.com",
                "name": "Old Session",
                "picture": "https://example.com/avatar.png",
            }
        }

    monkeypatch.setattr(auth_routes.oauth, "_clients", {}, raising=False)
    auth_routes._register_google_client()
    monkeypatch.setattr(auth_routes.oauth.google, "authorize_access_token", fake_authorize_access_token)

    client, _override_session = make_test_client()
    try:
        callback_response = client.get("/auth/callback", follow_redirects=False)
        assert callback_response.status_code == 303
        assert callback_response.headers["location"] == "/"

        me_response = client.get("/api/me")
        assert me_response.status_code == 200
        assert me_response.json()["authenticated"] is True
        assert me_response.json()["user"]["email"] == "old-session@example.com"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        auth_routes.get_settings.cache_clear()
