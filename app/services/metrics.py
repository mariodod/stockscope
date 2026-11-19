"""Derived views over the latest value of each metric."""

from typing import Any

from sqlalchemy import Select, case, func, literal, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from app.models import FundamentalFact, MetricDefinition, Quote

DESCRIPTIVE_KEYS = frozenset(
    {"ticker", "name", "exchange", "sector", "industry", "country", "currency"}
)

QUOTE_COLUMNS = {
    "market_cap": Quote.market_cap,
    "pe_ratio": Quote.pe_ratio,
    "price": Quote.price,
    "fifty_two_week_high": Quote.fifty_two_week_high,
    "fifty_two_week_low": Quote.fifty_two_week_low,
    "avg_volume": Quote.volume,
}


def validate_metric_keys(session: Session, keys: set[str]) -> set[str]:
    """Reject metric names that are not in the registry or company columns."""
    known = set(session.scalars(select(MetricDefinition.key)).all()) | set(DESCRIPTIVE_KEYS)
    unknown = keys - known
    if unknown:
        raise ValueError(f"Unknown metric keys: {', '.join(sorted(unknown))}")
    return known


def _latest_facts() -> Select[Any]:
    ranked = select(
        FundamentalFact.company_id.label("company_id"),
        FundamentalFact.metric_key.label("metric_key"),
        FundamentalFact.value.label("value"),
        func.row_number()
        .over(
            partition_by=[FundamentalFact.company_id, FundamentalFact.metric_key],
            order_by=[
                FundamentalFact.as_of_date.desc(),
                FundamentalFact.filed_at.desc(),
                FundamentalFact.id.desc(),
            ],
        )
        .label("rn"),
    ).subquery()
    return select(ranked.c.company_id, ranked.c.metric_key, ranked.c.value).where(
        ranked.c.rn == 1
    )


def _latest_quote_selects(keys: list[str]) -> list[Select[Any]]:
    selected = [key for key in keys if key in QUOTE_COLUMNS]
    if not selected:
        return []
    ranked = select(
        Quote.company_id.label("company_id"),
        *[QUOTE_COLUMNS[key].label(f"q{index}") for index, key in enumerate(selected)],
        func.row_number()
        .over(partition_by=Quote.company_id, order_by=Quote.date.desc())
        .label("rn"),
    ).subquery()
    return [
        select(
            ranked.c.company_id,
            literal(key).label("metric_key"),
            ranked.c[f"q{index}"].label("value"),
        ).where(ranked.c.rn == 1)
        for index, key in enumerate(selected)
    ]


def latest_metric_pivot(keys: set[str]) -> Subquery:
    """One row per company with a column for each requested non-descriptive metric."""
    metric_keys = sorted(keys - DESCRIPTIVE_KEYS)
    facts = _latest_facts()
    values = union_all(facts, *_latest_quote_selects(metric_keys)).subquery("metric_values")
    columns = [
        func.max(case((values.c.metric_key == key, values.c.value))).label(key)
        for key in metric_keys
    ]
    return select(values.c.company_id.label("company_id"), *columns).group_by(
        values.c.company_id
    ).subquery("pivot")


def latest_fact_rows(session: Session, company_id: int) -> list[dict[str, Any]]:
    """Latest fact per metric for a company, with provenance."""
    ranked = select(
        FundamentalFact.company_id.label("company_id"),
        FundamentalFact.metric_key.label("metric_key"),
        FundamentalFact.period.label("period"),
        FundamentalFact.value.label("value"),
        FundamentalFact.unit.label("unit"),
        FundamentalFact.source.label("source"),
        FundamentalFact.as_of_date.label("as_of_date"),
        func.row_number()
        .over(
            partition_by=[FundamentalFact.company_id, FundamentalFact.metric_key],
            order_by=[
                FundamentalFact.as_of_date.desc(),
                FundamentalFact.filed_at.desc(),
                FundamentalFact.id.desc(),
            ],
        )
        .label("rn"),
    ).subquery()
    rows = session.execute(
        select(ranked).where(ranked.c.rn == 1, ranked.c.company_id == company_id)
    ).mappings()
    return [dict(row) for row in rows]


def latest_quote_row(session: Session, company_id: int) -> dict[str, Any] | None:
    row = session.execute(
        select(Quote)
        .where(Quote.company_id == company_id)
        .order_by(Quote.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "market_cap": row.market_cap,
        "pe_ratio": row.pe_ratio,
        "price": row.price,
        "fifty_two_week_high": row.fifty_two_week_high,
        "fifty_two_week_low": row.fifty_two_week_low,
        "avg_volume": row.volume,
        "source": row.source,
        "as_of_date": row.date,
    }


def fact_history(session: Session, company_id: int) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            FundamentalFact.metric_key.label("metric_key"),
            FundamentalFact.period.label("period"),
            FundamentalFact.value.label("value"),
            FundamentalFact.as_of_date.label("as_of_date"),
            FundamentalFact.source.label("source"),
        )
        .where(FundamentalFact.company_id == company_id)
        .order_by(FundamentalFact.as_of_date, FundamentalFact.metric_key)
    ).mappings()
    return [dict(row) for row in rows]


def metric_labels(session: Session) -> dict[str, tuple[str, str, Any]]:
    rows = session.execute(
        select(
            MetricDefinition.key,
            MetricDefinition.label,
            MetricDefinition.unit,
            MetricDefinition.direction,
        )
    ).all()
    return {row[0]: (row[1], row[2], row[3]) for row in rows}
