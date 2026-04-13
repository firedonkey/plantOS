from fastapi.testclient import TestClient

from platform_app.main import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_page():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "PlantLab Platform" in response.text


def test_login_page():
    client = TestClient(app)
    response = client.get("/login")

    assert response.status_code == 200
    assert "Welcome Back" in response.text
    assert "Sign in with Google" in response.text or "Google sign-in is not configured" in response.text
