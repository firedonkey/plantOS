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
