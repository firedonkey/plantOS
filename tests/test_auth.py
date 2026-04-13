from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_app.models.base import Base
from platform_app.services.users import upsert_google_user
from platform_app.main import app
from fastapi.testclient import TestClient


def test_google_login_reports_missing_config():
    client = TestClient(app)
    response = client.get("/auth/login")

    assert response.status_code == 503
    assert "Google sign-in is not configured" in response.json()["detail"]


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
