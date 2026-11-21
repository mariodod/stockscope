"""Sector performance response."""

from pydantic import BaseModel


class SectorPerformance(BaseModel):
    sector: str
    companies: int
    return_pct: float
    avg_pe: float | None = None
    total_market_cap: float | None = None
