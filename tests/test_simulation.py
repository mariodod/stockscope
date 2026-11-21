"""Returns simulator behavior."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Company, Quote
from app.seed.metrics import seed_metrics


def _seed_prices(db: Session) -> None:
    seed_metrics(db)
    for ticker in ("AAPL", "SPY"):
        company = Company(ticker=ticker, name=ticker, sector="Technology")
        db.add(company)
        db.flush()
        for day, price in (
            (date(2025, 1, 2), 100),
            (date(2025, 2, 3), 110),
        ):
            db.add(
                Quote(
                    company_id=company.id,
                    date=day,
                    price=Decimal(str(price)),
                    adjusted_close=Decimal(str(price)),
                    source="test",
                )
            )
    db.commit()


def test_lump_sum_simulation(client: TestClient, db_session: Session) -> None:
    _seed_prices(db_session)

    response = client.post(
        "/api/v1/simulate",
        json={
            "tickers": ["AAPL"],
            "start": "2025-01-01",
            "end": "2025-12-31",
            "initial": 1000,
            "strategy": "lump_sum",
            "benchmark": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["performance"]["final_value"] == 1100
    assert body["performance"]["total_return_pct"] == 10
    assert len(body["series"]) == 2


def test_dca_simulation(client: TestClient, db_session: Session) -> None:
    _seed_prices(db_session)

    response = client.post(
        "/api/v1/simulate",
        json={
            "tickers": ["AAPL"],
            "start": "2025-01-01",
            "end": "2025-12-31",
            "initial": 0,
            "contribution": 100,
            "strategy": "dca",
            "benchmark": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["performance"]["total_contributed"] == 200
    assert round(body["performance"]["final_value"], 2) == 210


def test_simulation_reports_missing_history(client: TestClient, db_session: Session) -> None:
    _seed_prices(db_session)

    response = client.post(
        "/api/v1/simulate",
        json={
            "tickers": ["NOPE"],
            "start": "2025-01-01",
            "end": "2025-12-31",
            "initial": 1000,
        },
    )

    assert response.status_code == 400
    assert "NOPE" in response.json()["detail"]
