"""Same-sector peer discovery for a company."""

from math import log

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Quote
from app.schemas.screen import (
    FilterCondition,
    FilterOp,
    PagedCompanies,
    ScreenRequest,
    SortDirection,
    SortSpec,
)
from app.services.screening import screen

PEER_METRICS = ("market_cap", "pe_ratio", "roe", "revenue_growth_yoy", "debt_to_equity")


def _latest_market_cap(db: Session, company: Company) -> float | None:
    value = db.scalar(
        select(Quote.market_cap)
        .where(Quote.company_id == company.id)
        .order_by(Quote.date.desc())
        .limit(1)
    )
    return float(value) if value is not None else None


def find_peers(db: Session, ticker: str, limit: int) -> PagedCompanies:
    """Return companies in the same sector, closest in market cap first."""
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    if company.sector is None:
        return PagedCompanies(total=0, limit=limit, offset=0, items=[])

    request = ScreenRequest(
        filters=[FilterCondition(metric="sector", op=FilterOp.EQ, value=company.sector)],
        sort=[SortSpec(metric="market_cap", dir=SortDirection.DESC)],
        columns=list(PEER_METRICS),
        limit=500,
    )
    candidates = screen(db, request).items
    peers = [item for item in candidates if item.ticker != company.ticker]

    target_cap = _latest_market_cap(db, company)
    if target_cap is not None and target_cap > 0:
        peers.sort(
            key=lambda item: abs(
                log(max(float(item.metrics.get("market_cap") or 0), 1)) - log(target_cap)
            )
        )

    selected = peers[:limit]
    return PagedCompanies(total=len(peers), limit=limit, offset=0, items=selected)
