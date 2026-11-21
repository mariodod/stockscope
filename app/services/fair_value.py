"""Scenario valuations from analyst forward EPS estimates."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact, Quote
from app.schemas.fair_value import FairValueRead, FairValueScenario

DEFAULT_MULTIPLES = (12.0, 18.0, 25.0)


def _latest_value(db: Session, company_id: int, metric_key: str) -> float | None:
    value = db.scalar(
        select(FundamentalFact.value)
        .where(
            FundamentalFact.company_id == company_id,
            FundamentalFact.metric_key == metric_key,
        )
        .order_by(FundamentalFact.as_of_date.desc(), FundamentalFact.id.desc())
        .limit(1)
    )
    return float(value) if value is not None else None


def fair_value(
    db: Session,
    ticker: str,
    low_pe: float | None = None,
    base_pe: float | None = None,
    high_pe: float | None = None,
) -> FairValueRead:
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    forward_eps = _latest_value(db, company.id, "forward_eps")
    if forward_eps is None:
        raise HTTPException(
            status_code=400, detail="No forward EPS estimate available for this company"
        )

    current_price = db.scalar(
        select(Quote.price)
        .where(Quote.company_id == company.id)
        .order_by(Quote.date.desc())
        .limit(1)
    )
    price = float(current_price) if current_price is not None else None
    growth = _latest_value(db, company.id, "earnings_growth_estimate")
    implied_pe = _latest_value(db, company.id, "forward_pe")

    if base_pe is not None:
        low, base, high = low_pe or base_pe * 0.7, base_pe, high_pe or base_pe * 1.3
    elif implied_pe and implied_pe > 0:
        low, base, high = implied_pe * 0.8, implied_pe, implied_pe * 1.2
    else:
        low, base, high = DEFAULT_MULTIPLES

    scenarios = []
    for name, multiple in (("Bear", low), ("Base", base), ("Bull", high)):
        value = forward_eps * multiple
        upside = (value / price - 1) * 100 if price else 0.0
        scenarios.append(
            FairValueScenario(
                name=name,
                pe_multiple=round(multiple, 2),
                fair_value=round(value, 2),
                upside_pct=round(upside, 2),
            )
        )

    return FairValueRead(
        ticker=company.ticker,
        forward_eps=forward_eps,
        current_price=price,
        growth_estimate=growth,
        base_pe=round(base, 2),
        scenarios=scenarios,
    )
