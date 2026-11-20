"""Health endpoint contract."""

import asyncio

from fastapi.testclient import TestClient
from starlette.requests import Request

from app import __version__
from app.main import unhandled_error_handler


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
    assert response.headers["X-Request-ID"]


def test_request_id_is_propagated(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-id-123"})

    assert response.headers["X-Request-ID"] == "test-id-123"


def test_unhandled_error_keeps_request_id() -> None:
    scope = {"type": "http", "method": "GET", "path": "/boom", "headers": []}
    request = Request(scope)
    request.state.request_id = "caller-id"

    response = asyncio.run(unhandled_error_handler(request, RuntimeError("boom")))

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "caller-id"


def test_openapi_docs_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200

    schema = client.get("/openapi.json").json()
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/metrics" in schema["paths"]
