"""Dividend calendar behavior."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.jobs import refresh_dividends
from app.models import Company, DividendEvent
from app.providers.base import DividendSeed
from app.providers.yf import YFinanceProvider


def test_yfinance_handles_millisecond_epochs() -> None:
    from app.providers.yf import _date_from_info

    assert _date_from_info(1767225600000) == date(2026, 1, 1)
    assert _date_from_info(10**20) is None


def test_yfinance_maps_dividend_dates() -> None:
    class FakeTicker:
        info = {
            "exDividendDate": 1767225600,
            "dividendDate": "2026-01-15",
            "dividendRate": 1.25,
        }

    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker())
    seeds = list(provider.get_dividends("AAPL"))

    assert len(seeds) == 1
    assert seeds[0].ex_date == date(2026, 1, 1)
    assert seeds[0].pay_date == date(2026, 1, 15)
    assert seeds[0].amount_per_share == Decimal("1.25")


def test_dividend_ingestion_is_idempotent(db_session: Session) -> None:
    db_session.add(Company(ticker="DIV", name="Dividend Co"))
    db_session.commit()

    class Provider:
        name = "fake"

        def get_dividends(self, ticker: str) -> Any:
            yield DividendSeed(
                ex_date=date.today() + timedelta(days=10),
                pay_date=date.today() + timedelta(days=20),
                amount_per_share=Decimal("0.5"),
            )

    provider = Provider()
    assert refresh_dividends(db_session, provider, ["DIV"]) == 1
    assert refresh_dividends(db_session, provider, ["DIV"]) == 1
    assert db_session.scalar(select(func.count()).select_from(DividendEvent)) == 1


def test_dividend_endpoint_returns_only_upcoming_events(
    client: TestClient, db_session: Session
) -> None:
    company = Company(ticker="DIV", name="Dividend Co")
    db_session.add(company)
    db_session.flush()
    db_session.add_all(
        [
            DividendEvent(
                company_id=company.id,
                ex_date=date.today() + timedelta(days=5),
                amount_per_share=Decimal("0.75"),
                source="fake",
            ),
            DividendEvent(
                company_id=company.id,
                ex_date=date.today() - timedelta(days=5),
                amount_per_share=Decimal("0.50"),
                source="fake",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/dividends", params={"days": 30})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["ticker"] == "DIV"
    assert response.json()[0]["amount_per_share"] == 0.75
