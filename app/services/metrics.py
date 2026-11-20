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
QUOTE_KEYS = tuple(QUOTE_COLUMNS)


def validate_metric_keys(session: Session, keys: set[str]) -> None:
    """Reject metric names that are not in the registry or company columns."""
    known = set(session.scalars(select(MetricDefinition.key)).all()) | set(DESCRIPTIVE_KEYS)
    unknown = keys - known
    if unknown:
        raise ValueError(f"Unknown metric keys: {', '.join(sorted(unknown))}")


def _ranked_facts() -> Any:
    """Facts ranked newest-first per company and metric."""
    return select(
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


def _latest_facts() -> Select[Any]:
    """Latest fact per company and metric, with quote precedence marker."""
    ranked = _ranked_facts()
    return select(
        ranked.c.company_id,
        ranked.c.metric_key,
        ranked.c.value,
        ranked.c.as_of_date,
        literal(1).label("precedence"),
    ).where(ranked.c.rn == 1)


def _latest_quote_selects(keys: list[str]) -> list[Select[Any]]:
    selected = [key for key in keys if key in QUOTE_COLUMNS]
    if not selected:
        return []
    ranked = select(
        Quote.company_id.label("company_id"),
        Quote.date.label("as_of_date"),
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
            ranked.c.as_of_date,
            literal(2).label("precedence"),
        ).where(ranked.c.rn == 1)
        for index, key in enumerate(selected)
    ]


def latest_metric_pivot(keys: set[str]) -> Subquery:
    """One row per company with the newest value for each requested metric.

    Quotes outrank facts on the same date. Numeric size is never used to pick a value.
    """
    metric_keys = sorted(keys - DESCRIPTIVE_KEYS)
    values = union_all(_latest_facts(), *_latest_quote_selects(metric_keys)).subquery(
        "metric_values"
    )
    ranked = select(
        values.c.company_id,
        values.c.metric_key,
        values.c.value,
        func.row_number()
        .over(
            partition_by=[values.c.company_id, values.c.metric_key],
            order_by=[values.c.as_of_date.desc(), values.c.precedence.desc()],
        )
        .label("rn"),
    ).subquery()
    latest = select(ranked).where(ranked.c.rn == 1).subquery("latest_values")
    columns = [
        func.max(case((latest.c.metric_key == key, latest.c.value))).label(key)
        for key in metric_keys
    ]
    return select(latest.c.company_id.label("company_id"), *columns).group_by(
        latest.c.company_id
    ).subquery("pivot")


def latest_fact_rows(session: Session, company_id: int) -> list[dict[str, Any]]:
    """Latest fact per metric for a company, with provenance."""
    ranked = _ranked_facts()
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
    values = {key: getattr(row, QUOTE_COLUMNS[key].key) for key in QUOTE_KEYS}
    values["source"] = row.source
    values["as_of_date"] = row.date
    return values


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
