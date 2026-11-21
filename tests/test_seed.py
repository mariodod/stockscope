"""Metric registry parsing and idempotent seeding."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MetricDefinition, MetricDirection
from app.seed.metrics import parse_metrics, seed_metrics


def test_parse_metrics_covers_catalog() -> None:
    metrics = parse_metrics()

    assert len(metrics) == 38
    assert len({metric.key for metric in metrics}) == 38
    assert {metric.category for metric in metrics} == {
        "valuation",
        "profitability",
        "growth",
        "financial_health",
        "dividends_market",
        "descriptive",
    }
    by_key = {metric.key: metric for metric in metrics}
    assert by_key["pe_ratio"].direction is MetricDirection.LOW
    assert by_key["revenue_growth_yoy"].direction is MetricDirection.HIGH
    assert by_key["ebitda"].is_derived is True
    assert by_key["sector"].direction is MetricDirection.NONE
    assert by_key["last_daily_volume"].label == "Last daily volume"


def test_seed_metrics_is_idempotent(db_session: Session) -> None:
    first = seed_metrics(db_session)
    second = seed_metrics(db_session)

    assert first == (38, 0)
    assert second == (0, 38)
    assert db_session.scalar(select(func.count()).select_from(MetricDefinition)) == 38
