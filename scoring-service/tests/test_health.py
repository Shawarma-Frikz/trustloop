from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_unhealthy_without_a_model():
    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "modelLoaded": False}
