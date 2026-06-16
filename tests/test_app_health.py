from fastapi.testclient import TestClient

from edgelab.app.main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint_returns_phase_metadata() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["app"] == "EdgeLab"
    assert response.json()["phase"] == "Phase 7X-2L structured AI idea batch testing"
