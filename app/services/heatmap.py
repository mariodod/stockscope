"""Sector returns and valuation from stored daily prices."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Quote
from app.schemas.heatmap import SectorPerformance


@dataclass
class CompanyReturn:
    sector: str
    first: float
    last: float
    cap: float | None
    pe: float | None


def sector_performance(db: Session, days: int) -> list[SectorPerformance]:
    """Average price return per sector over the requested window."""
    start = date.today() - timedelta(days=days)
    rows = db.execute(
        select(
            Company.sector,
            Company.id,
            Quote.adjusted_close,
            Quote.market_cap,
            Quote.pe_ratio,
        )
        .join(Company, Company.id == Quote.company_id)
        .where(Company.sector.is_not(None), Quote.date >= start, Quote.adjusted_close.is_not(None))
        .order_by(Company.id, Quote.date)
    ).all()

    by_company: dict[int, CompanyReturn] = {}
    for sector, company_id, adjusted, market_cap, pe in rows:
        if adjusted is None:
            continue
        price = float(adjusted)
        cap = float(market_cap) if market_cap is not None else None
        ratio = float(pe) if pe is not None else None
        entry = by_company.get(company_id)
        if entry is None:
            by_company[company_id] = CompanyReturn(
                sector=str(sector), first=price, last=price, cap=cap, pe=ratio
            )
            continue
        entry.last = price
        if cap is not None:
            entry.cap = cap
        if ratio is not None:
            entry.pe = ratio

    by_sector: dict[str, list[CompanyReturn]] = {}
    for entry in by_company.values():
        by_sector.setdefault(entry.sector, []).append(entry)

    results = []
    for sector, entries in by_sector.items():
        returns = [(entry.last / entry.first - 1) * 100 for entry in entries if entry.first > 0]
        if not returns:
            continue
        caps = [entry.cap for entry in entries if entry.cap is not None]
        pes = [entry.pe for entry in entries if entry.pe is not None]
        results.append(
            SectorPerformance(
                sector=sector,
                companies=len(entries),
                return_pct=round(sum(returns) / len(returns), 2),
                avg_pe=round(sum(pes) / len(pes), 2) if pes else None,
                total_market_cap=round(sum(caps), 2) if caps else None,
            )
        )
    return sorted(results, key=lambda item: item.return_pct, reverse=True)
