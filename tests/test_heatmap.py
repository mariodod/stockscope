"""Sector heatmap data."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Company, Quote


def _seed(db: Session) -> None:
    tech = Company(ticker="TECH", name="Tech", sector="Technology")
    energy = Company(ticker="ENRG", name="Energy", sector="Energy")
    db.add_all([tech, energy])
    db.flush()
    for company, first, last in ((tech, 100, 110), (energy, 100, 95)):
        db.add_all(
            [
                Quote(
                    company_id=company.id,
                    date=date.today() - timedelta(days=60),
                    adjusted_close=Decimal(str(first)),
                    market_cap=Decimal("1000000"),
                    pe_ratio=Decimal("20"),
                    source="test",
                ),
                Quote(
                    company_id=company.id,
                    date=date.today(),
                    adjusted_close=Decimal(str(last)),
                    source="test",
                ),
            ]
        )
    db.commit()


def test_heatmap_uses_latest_valuation(client: TestClient, db_session: Session) -> None:
    company = Company(ticker="LATE", name="Latest", sector="Technology")
    db_session.add(company)
    db_session.flush()
    db_session.add_all(
        [
            Quote(
                company_id=company.id,
                date=date.today() - timedelta(days=30),
                adjusted_close=Decimal("100"),
                market_cap=Decimal("1000000"),
                pe_ratio=Decimal("10"),
                source="test",
            ),
            Quote(
                company_id=company.id,
                date=date.today(),
                adjusted_close=Decimal("110"),
                market_cap=Decimal("9000000"),
                pe_ratio=Decimal("90"),
                source="test",
            ),
        ]
    )
    db_session.commit()

    body = client.get("/api/v1/sector-performance", params={"days": 60}).json()
    tech = next(item for item in body if item["sector"] == "Technology")

    assert tech["total_market_cap"] == 9000000
    assert tech["avg_pe"] == 90


def test_sector_performance(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.get("/api/v1/sector-performance", params={"days": 90})

    assert response.status_code == 200
    body = response.json()
    assert [item["sector"] for item in body] == ["Technology", "Energy"]
    assert body[0]["return_pct"] == 10
    assert body[1]["return_pct"] == -5
    assert body[0]["avg_pe"] == 20
