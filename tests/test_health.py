"""Health endpoint contract."""

from fastapi.testclient import TestClient

from app import __version__


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_openapi_docs_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200

    schema = client.get("/openapi.json").json()
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/metrics" in schema["paths"]
