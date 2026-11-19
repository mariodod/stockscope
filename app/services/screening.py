"""Filtering, sorting and composite ranking over company metrics."""

from bisect import bisect_left, bisect_right
from functools import cmp_to_key
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Company, MetricDefinition, MetricDirection
from app.schemas.screen import (
    CompanySummary,
    FilterCondition,
    FilterOp,
    PagedCompanies,
    ScreenRequest,
    SortDirection,
    SortSpec,
)
from app.services.metrics import DESCRIPTIVE_KEYS, latest_metric_pivot, validate_metric_keys


def build_query(session: Session, keys: set[str]) -> tuple[Select[Any], Any]:
    """Build a company query with one column per requested metric."""
    validate_metric_keys(session, keys)
    pivot = latest_metric_pivot(keys)
    query = select(Company)
    for key in sorted(keys - DESCRIPTIVE_KEYS):
        query = query.add_columns(pivot.c[key])
    return query.outerjoin(pivot, pivot.c.company_id == Company.id), pivot


def apply_filters(query: Select[Any], filters: list[FilterCondition], pivot: Any) -> Select[Any]:
    """Translate structured filters into parameterized SQL expressions."""
    for condition in filters:
        column = (
            getattr(Company, condition.metric)
            if condition.metric in DESCRIPTIVE_KEYS
            else pivot.c[condition.metric]
        )
        op = condition.op
        value = condition.value
        if op is FilterOp.IS_NULL:
            clause = column.is_(None) if value is not False else column.is_not(None)
        elif op is FilterOp.EQ:
            clause = column == value
        elif op is FilterOp.NEQ:
            clause = column != value
        elif op is FilterOp.GT:
            clause = column > value
        elif op is FilterOp.GTE:
            clause = column >= value
        elif op is FilterOp.LT:
            clause = column < value
        elif op is FilterOp.LTE:
            clause = column <= value
        elif op is FilterOp.BETWEEN:
            clause = column.between(value[0], value[1])
        elif op is FilterOp.IN:
            clause = column.in_(value)
        else:
            raise ValueError(f"Unsupported operator: {op}")
        query = query.where(clause)
    return query


def _value(record: dict[str, Any], metric: str) -> Any:
    if metric == "__score__":
        return record.get("score")
    if metric in DESCRIPTIVE_KEYS:
        return getattr(record["company"], metric)
    return record["metrics"].get(metric)


def _compare(a: dict[str, Any], b: dict[str, Any], spec: SortSpec) -> int:
    left, right = _value(a, spec.metric), _value(b, spec.metric)
    if left is None and right is None:
        return 0
    if left is None:
        return 1
    if right is None:
        return -1
    if left == right:
        return 0
    order = -1 if left < right else 1
    return -order if spec.dir is SortDirection.DESC else order


def _sort_key_for(spec: SortSpec) -> Any:
    return cmp_to_key(lambda a, b: _compare(a, b, spec))


def _percentile(value: float, ordered: list[float]) -> float:
    below = bisect_left(ordered, value)
    above = bisect_right(ordered, value)
    return (below + 0.5 * (above - below)) / len(ordered)


def _apply_ranking(
    session: Session, records: list[dict[str, Any]], request: ScreenRequest
) -> None:
    if request.ranking is None:
        return
    weights = request.ranking.weights
    if any(key in DESCRIPTIVE_KEYS for key in weights):
        raise ValueError("Ranking weights must reference numeric metrics")

    rows = session.execute(
        select(MetricDefinition.key, MetricDefinition.direction).where(
            MetricDefinition.key.in_(weights)
        )
    ).all()
    directions = {row[0]: row[1] for row in rows}
    ordered_values = {
        key: sorted(
            float(_value(record, key))
            for record in records
            if _value(record, key) is not None
        )
        for key in weights
    }

    for record in records:
        components: dict[str, float] = {}
        missing: list[str] = []
        score = 0.0
        for key, weight in weights.items():
            raw = _value(record, key)
            if raw is None or not ordered_values[key]:
                oriented = 0.5
                missing.append(key)
            else:
                percentile = _percentile(float(raw), ordered_values[key])
                direction = directions.get(key)
                if direction is MetricDirection.LOW:
                    oriented = 1 - percentile
                elif direction in {MetricDirection.NEUTRAL, MetricDirection.NONE}:
                    oriented = 0.5
                else:
                    oriented = percentile
            components[key] = round(oriented, 6)
            score += weight * oriented
        record["score"] = round(score, 6)
        record["components"] = components
        record["missing"] = missing


def screen(session: Session, request: ScreenRequest) -> PagedCompanies:
    """Run one screen: filter, rank, sort deterministically, then paginate."""
    keys = {condition.metric for condition in request.filters}
    keys |= {spec.metric for spec in request.sort}
    keys |= set(request.columns)
    if request.ranking is not None:
        keys |= set(request.ranking.weights)

    query, pivot = build_query(session, keys)
    query = apply_filters(query, request.filters, pivot)

    metric_keys = sorted(keys - DESCRIPTIVE_KEYS)
    records: list[dict[str, Any]] = []
    for row in session.execute(query).all():
        company = row[0]
        records.append(
            {
                "company": company,
                "metrics": {key: row[index + 1] for index, key in enumerate(metric_keys)},
            }
        )

    _apply_ranking(session, records, request)

    records.sort(key=lambda record: record["company"].ticker)
    if request.ranking is not None and not request.sort:
        default = SortSpec(metric="__score__", dir=SortDirection.DESC)
        records.sort(key=_sort_key_for(default))
    for spec in reversed(request.sort):
        records.sort(key=_sort_key_for(spec))

    total = len(records)
    window = records[request.offset : request.offset + request.limit]
    items = [
        CompanySummary(
            ticker=record["company"].ticker,
            name=record["company"].name,
            exchange=record["company"].exchange,
            sector=record["company"].sector,
            industry=record["company"].industry,
            metrics=record["metrics"],
            score=record.get("score"),
            score_components=record.get("components", {}),
            missing_metrics=record.get("missing", []),
        )
        for record in window
    ]
    return PagedCompanies(total=total, limit=request.limit, offset=request.offset, items=items)
