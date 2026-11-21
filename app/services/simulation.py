"""Deterministic portfolio return simulation over stored daily prices."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Quote
from app.schemas.simulation import (
    Performance,
    SimulationPoint,
    SimulationRequest,
    SimulationResult,
    Strategy,
)


def _price_series(
    db: Session, ticker: str, request: SimulationRequest
) -> list[tuple[date, float]]:
    rows = db.execute(
        select(
            Quote.date,
            func.coalesce(Quote.adjusted_close, Quote.price)
            if request.dividend_reinvestment
            else Quote.price,
        )
        .join(Company, Company.id == Quote.company_id)
        .where(
            Company.ticker == ticker.upper(),
            Quote.date >= request.start,
            Quote.date <= request.end,
        )
        .order_by(Quote.date)
    ).all()
    return [(day, float(value)) for day, value in rows if value is not None]


def _first_of_month(series: list[tuple[date, float]]) -> set[date]:
    seen: set[tuple[int, int]] = set()
    days: set[date] = set()
    for day, _ in series:
        key = (day.year, day.month)
        if key not in seen:
            seen.add(key)
            days.add(day)
    return days


def _performance(series: list[tuple[date, float]], contributed: float) -> Performance:
    final = series[-1][1] if series else 0.0
    total_return = (final / contributed - 1) * 100 if contributed > 0 else 0.0
    days = (series[-1][0] - series[0][0]).days if len(series) > 1 else 0
    annualised = (
        ((final / contributed) ** (365 / days) - 1) * 100 if days > 0 and contributed > 0 else 0.0
    )
    peak = 0.0
    max_drawdown = 0.0
    for _, value in series:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, (value / peak - 1) * 100)
    return Performance(
        final_value=round(final, 2),
        total_contributed=round(contributed, 2),
        total_return_pct=round(total_return, 2),
        annualised_return_pct=round(annualised, 2),
        max_drawdown_pct=round(max_drawdown, 2),
    )


def _simulate_one(
    series: list[tuple[date, float]],
    strategy: Strategy,
    investment: float,
    per_purchase: float,
) -> list[tuple[date, float]]:
    purchase_days = _first_of_month(series) if strategy is Strategy.DCA else {series[0][0]}
    amount = per_purchase if strategy is Strategy.DCA else investment
    shares = 0.0
    result: list[tuple[date, float]] = []
    for day, price in series:
        if day in purchase_days and price > 0:
            shares += amount / price
        result.append((day, shares * price))
    return result


def simulate(db: Session, request: SimulationRequest) -> SimulationResult:
    series_by_ticker = {ticker: _price_series(db, ticker, request) for ticker in request.tickers}
    missing = [ticker for ticker, series in series_by_ticker.items() if not series]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"No price history in range for: {', '.join(sorted(missing))}",
        )

    combined: dict[date, float] = {}
    for series in series_by_ticker.values():
        unit = _simulate_one(
            series,
            request.strategy,
            request.initial / len(series_by_ticker),
            request.contribution / len(series_by_ticker),
        )
        for day, value in unit:
            combined[day] = combined.get(day, 0.0) + value

    ordered = sorted(combined.items())
    months = len(_first_of_month(ordered))
    contributed = (
        request.contribution * months if request.strategy is Strategy.DCA else request.initial
    )

    benchmark_curve: dict[date, float] = {}
    benchmark_performance = None
    if request.benchmark and request.benchmark.upper() not in {t.upper() for t in request.tickers}:
        bench = _price_series(db, request.benchmark, request)
        if bench:
            benchmark_curve = dict(
                _simulate_one(bench, request.strategy, request.initial, request.contribution)
            )
            bench_contributed = (
                request.contribution * len(_first_of_month(bench))
                if request.strategy is Strategy.DCA
                else request.initial
            )
            benchmark_performance = _performance(sorted(benchmark_curve.items()), bench_contributed)

    points = [
        SimulationPoint(
            date=day,
            value=round(value, 2),
            benchmark_value=round(benchmark_curve[day], 2) if day in benchmark_curve else None,
        )
        for day, value in ordered
    ]
    return SimulationResult(
        performance=_performance(ordered, contributed),
        benchmark=benchmark_performance,
        series=points,
    )
