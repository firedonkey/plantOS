from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.api.routes.auth as auth_routes
from app.core.settings import get_settings
from app.main import app
from app.models.base import Base
from app.services.users import upsert_google_user


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
