"""Saved screens can be created, read back, and are token-addressed."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_saved_screen_roundtrip(client: TestClient, db_session: Session) -> None:
    state = {
        "filters": [{"metric": "pe_ratio", "op": "lte", "value": 20}],
        "sort": [{"metric": "roe", "dir": "desc"}],
        "weights": {"roe": 1.0},
        "limit": 25,
        "offset": 0,
    }

    created = client.post("/api/v1/screens", json=state)
    assert created.status_code == 201
    token = created.json()["token"]
    assert len(token) >= 16

    loaded = client.get(f"/api/v1/screens/{token}")
    assert loaded.status_code == 200
    assert loaded.json() == state

    assert client.get("/api/v1/screens/no-such-token").status_code == 404


def test_saved_screen_rejects_non_finite_weights(client: TestClient) -> None:
    response = client.post(
        "/api/v1/screens",
        content=b'{"weights":{"roe":NaN}}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
