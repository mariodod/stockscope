"""End-to-end screening API tests against seeded fixture data."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact, Quote
from app.seed.metrics import seed_metrics

FIXTURES = (
    (
        "AAA",
        "Alpha",
        "Technology",
        "NASDAQ",
        {"pe_ratio": 10, "roe": 0.30, "revenue_growth_yoy": 0.20},
        1_000_000_000_000,
        10,
    ),
    (
        "BBB",
        "Beta",
        "Technology",
        "NASDAQ",
        {"pe_ratio": 40, "roe": 0.10, "revenue_growth_yoy": 0.50},
        500_000_000_000,
        40,
    ),
    (
        "CCC",
        "Gamma",
        "Energy",
        "NYSE",
        {"pe_ratio": 15, "roe": 0.20, "revenue_growth_yoy": 0.05},
        2_000_000_000_000,
        15,
    ),
    ("DDD", "Delta", "Technology", "NYSE", {}, 100_000_000_000, None),
)


def _seed(db: Session) -> None:
    seed_metrics(db)
    for ticker, name, sector, exchange, facts, market_cap, pe in FIXTURES:
        company = Company(ticker=ticker, name=name, sector=sector, exchange=exchange)
        db.add(company)
        db.flush()
        for metric_key, value in facts.items():
            db.add(
                FundamentalFact(
                    company_id=company.id,
                    metric_key=metric_key,
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
                market_cap=Decimal(str(market_cap)),
                pe_ratio=Decimal(str(pe)) if pe is not None else None,
                source="test",
            )
        )
    db.commit()


def _screen(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/v1/screen", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_companies_are_filtered_sorted_and_paginated(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    response = client.get(
        "/api/v1/companies", params={"sector": "Technology", "limit": 2, "offset": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["ticker"] for item in body["items"]] == ["BBB", "DDD"]


def test_companies_sort_with_nulls_last(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    body = _screen(client, {"sort": [{"metric": "pe_ratio", "dir": "asc"}]})

    assert [item["ticker"] for item in body["items"]] == ["AAA", "CCC", "BBB", "DDD"]


def test_filters_support_between_in_and_is_null(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    between = _screen(
        client,
        {"filters": [{"metric": "pe_ratio", "op": "between", "value": [10, 20]}]},
    )
    assert sorted(item["ticker"] for item in between["items"]) == ["AAA", "CCC"]

    in_filter = _screen(
        client,
        {"filters": [{"metric": "sector", "op": "in", "value": ["Energy"]}]},
    )
    assert [item["ticker"] for item in in_filter["items"]] == ["CCC"]

    nulls = _screen(
        client,
        {"filters": [{"metric": "pe_ratio", "op": "is_null", "value": True}]},
    )
    assert [item["ticker"] for item in nulls["items"]] == ["DDD"]


def test_composite_ranking_is_correct_and_stable(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    payload = {
        "ranking": {"weights": {"pe_ratio": 0.5, "roe": 0.5}},
        "filters": [{"metric": "sector", "op": "neq", "value": "Energy"}],
    }

    first = _screen(client, payload)
    second = _screen(client, payload)

    assert [item["ticker"] for item in first["items"]] == [
        item["ticker"] for item in second["items"]
    ]
    assert first["items"][0]["ticker"] == "AAA"
    assert 0 <= (first["items"][0]["score"] or 0) <= 1
    assert set(first["items"][0]["score_components"]) == {"pe_ratio", "roe"}


def test_missing_values_score_neutrally_and_are_flagged(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    body = _screen(client, {"ranking": {"weights": {"revenue_growth_yoy": 1.0}}})

    delta = next(item for item in body["items"] if item["ticker"] == "DDD")
    assert "revenue_growth_yoy" in delta["missing_metrics"]
    assert delta["score_components"]["revenue_growth_yoy"] == 0.5


def test_newer_quote_wins_over_older_fact(client: TestClient, db_session: Session) -> None:
    seed_metrics(db_session)
    company = Company(ticker="NEW", name="Newest wins")
    db_session.add(company)
    db_session.flush()
    db_session.add(
        FundamentalFact(
            company_id=company.id,
            metric_key="pe_ratio",
            period="TTM",
            value=Decimal("60"),
            unit="ratio",
            source="older",
            as_of_date=date(2026, 1, 1),
        )
    )
    db_session.add(
        Quote(
            company_id=company.id,
            date=date(2026, 1, 2),
            pe_ratio=Decimal("50"),
            source="newer",
        )
    )
    db_session.commit()

    body = _screen(client, {"columns": ["pe_ratio"]})
    item = next(row for row in body["items"] if row["ticker"] == "NEW")

    assert item["metrics"]["pe_ratio"] == "50.000000"


def test_unknown_metric_is_rejected(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.post(
        "/api/v1/screen",
        json={"filters": [{"metric": "not_a_metric", "op": "eq", "value": 1}]},
    )

    assert response.status_code == 400
    assert "Unknown metric keys" in response.json()["detail"]


def test_non_finite_weights_are_rejected(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    response = client.post(
        "/api/v1/screen",
        content=b'{"ranking":{"weights":{"pe_ratio":NaN}}}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


def test_data_quality_reports_coverage_and_staleness(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    response = client.get("/api/v1/data-quality")

    assert response.status_code == 200
    body = response.json()
    pe = next(metric for metric in body["metrics"] if metric["key"] == "pe_ratio")
    assert pe["total_companies"] == 4
    assert pe["companies_with_value"] == 3
    assert pe["coverage_pct"] == 75.0
    assert pe["stale_count"] > 0


def test_staleness_counts_companies_not_history_rows(
    client: TestClient, db_session: Session
) -> None:
    seed_metrics(db_session)
    company = Company(ticker="FRESH", name="Fresh")
    db_session.add(company)
    db_session.flush()
    old = date.today() - timedelta(days=200)
    for index in range(99):
        db_session.add(
            Quote(
                company_id=company.id,
                date=old - timedelta(days=index),
                pe_ratio=Decimal("20"),
                source="old",
            )
        )
    db_session.add(
        Quote(
            company_id=company.id,
            date=date.today(),
            pe_ratio=Decimal("15"),
            source="fresh",
        )
    )
    db_session.commit()

    body = client.get("/api/v1/data-quality").json()
    pe = next(metric for metric in body["metrics"] if metric["key"] == "pe_ratio")

    assert pe["companies_with_value"] == 1
    assert pe["stale_count"] == 0


def test_company_detail_and_sectors(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    detail = client.get("/api/v1/companies/aaa")
    assert detail.status_code == 200
    body = detail.json()
    assert body["ticker"] == "AAA"
    keys = [metric["metric_key"] for metric in body["latest_metrics"]]
    assert {"pe_ratio", "roe", "revenue_growth_yoy", "market_cap"} <= set(keys)
    assert len(keys) == len(set(keys))
    assert len(body["history"]) == 3

    assert client.get("/api/v1/companies/ZZZ").status_code == 404

    sectors = client.get("/api/v1/sectors").json()
    assert "Technology" in sectors["sectors"]
    assert "Energy" in sectors["sectors"]
