from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_startup_loads_the_rules() -> None:
    with TestClient(app) as client:  # runs the lifespan, which validates rules.yaml
        assert client.get("/health").status_code == 200
