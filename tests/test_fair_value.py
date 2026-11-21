"""Fair value scenarios from forward EPS estimates."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact, Quote
from app.seed.metrics import seed_metrics


def _seed(db: Session) -> None:
    seed_metrics(db)
    company = Company(ticker="EST", name="Estimate Co")
    db.add(company)
    db.flush()
    for key, value in (
        ("forward_eps", 5),
        ("earnings_growth_estimate", 0.2),
        ("forward_pe", 20),
    ):
        db.add(
            FundamentalFact(
                company_id=company.id,
                metric_key=key,
                period="TTM",
                value=Decimal(str(value)),
                unit="ratio",
                source="test",
                as_of_date=date(2026, 1, 1),
            )
        )
    db.add(
        Quote(
            company_id=company.id,
            date=date(2026, 1, 2),
            price=Decimal("100"),
            source="test",
        )
    )
    db.commit()


def test_fair_value_uses_forward_pe_when_available(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.get("/api/v1/companies/EST/fair-value")

    assert response.status_code == 200
    body = response.json()
    assert body["base_pe"] == 20
    base = next(scenario for scenario in body["scenarios"] if scenario["name"] == "Base")
    assert base["fair_value"] == 100
    assert base["upside_pct"] == 0


def test_fair_value_accepts_custom_multiples(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.get(
        "/api/v1/companies/EST/fair-value", params={"low_pe": 10, "base_pe": 15, "high_pe": 25}
    )

    assert response.status_code == 200
    values = {item["name"]: item["fair_value"] for item in response.json()["scenarios"]}
    assert values == {"Bear": 50, "Base": 75, "Bull": 125}


def test_fair_value_uses_filed_at_to_break_same_date_ties(
    client: TestClient, db_session: Session
) -> None:
    seed_metrics(db_session)
    company = Company(ticker="TIE", name="Tie Co")
    db_session.add(company)
    db_session.flush()
    for value, filed_day in ((3, date(2026, 1, 1)), (6, date(2026, 2, 1))):
        db_session.add(
            FundamentalFact(
                company_id=company.id,
                metric_key="forward_eps",
                period="TTM",
                value=Decimal(str(value)),
                unit="currency",
                source=f"test-{filed_day.isoformat()}",
                as_of_date=date(2026, 1, 1),
                filed_at=datetime.combine(filed_day, time.min, tzinfo=UTC),
            )
        )
    db_session.commit()

    response = client.get("/api/v1/companies/TIE/fair-value", params={"base_pe": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["forward_eps"] == 6
    assert next(item for item in body["scenarios"] if item["name"] == "Base")[
        "fair_value"
    ] == 120


def test_fair_value_honours_partial_multiples(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.get(
        "/api/v1/companies/EST/fair-value", params={"low_pe": 10, "high_pe": 30}
    )

    assert response.status_code == 200
    values = {item["name"]: item["fair_value"] for item in response.json()["scenarios"]}
    assert values == {"Bear": 50, "Base": 100, "Bull": 150}


def test_fair_value_rejects_invalid_multiples(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.get(
        "/api/v1/companies/EST/fair-value", params={"low_pe": 30, "base_pe": 20}
    )

    assert response.status_code == 400


def test_fair_value_requires_estimate(client: TestClient, db_session: Session) -> None:
    seed_metrics(db_session)
    db_session.add(Company(ticker="NOEST", name="No estimate"))
    db_session.commit()

    response = client.get("/api/v1/companies/NOEST/fair-value")

    assert response.status_code == 400
