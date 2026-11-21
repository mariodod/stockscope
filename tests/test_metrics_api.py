"""Metric registry endpoint behavior."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.metrics import seed_metrics


def test_metrics_lists_catalog(client: TestClient, db_session: Session) -> None:
    seed_metrics(db_session)

    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 40
    assert set(data[0]) == {
        "key",
        "label",
        "category",
        "unit",
        "direction",
        "formula",
        "description",
        "is_derived",
    }
    assert any(metric["key"] == "ebitda" and metric["is_derived"] for metric in data)


def test_metrics_can_filter_by_category(client: TestClient, db_session: Session) -> None:
    seed_metrics(db_session)

    response = client.get("/api/v1/metrics", params={"category": "valuation"})

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(metric["category"] == "valuation" for metric in data)
