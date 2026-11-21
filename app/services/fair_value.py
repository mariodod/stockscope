"""Scenario valuations from analyst forward EPS estimates."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact
from app.schemas.fair_value import FairValueRead, FairValueScenario
from app.services.metrics import latest_quote_row

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

    quote = latest_quote_row(db, company.id)
    current_price = quote.get("price") if quote else None
    price = float(current_price) if current_price is not None else None
    growth = _latest_value(db, company.id, "earnings_growth_estimate")
    implied_pe = _latest_value(db, company.id, "forward_pe")

    provided = {
        name: value
        for name, value in (("low", low_pe), ("base", base_pe), ("high", high_pe))
        if value is not None
    }
    if any(value <= 0 for value in provided.values()):
        raise ValueError("P/E multiples must be positive")

    base = (
        base_pe
        if base_pe is not None
        else implied_pe
        if implied_pe is not None and implied_pe > 0
        else DEFAULT_MULTIPLES[1]
    )
    low = low_pe if low_pe is not None else base * 0.8
    high = high_pe if high_pe is not None else base * 1.2
    if low > base or high < base:
        raise ValueError("multiples must satisfy low <= base <= high")

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
