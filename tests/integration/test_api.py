from ai.config.settings import Settings
from ai.main import create_app
from fastapi.testclient import TestClient


def test_health_endpoint(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
