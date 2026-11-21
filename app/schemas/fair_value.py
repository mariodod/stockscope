"""Fair value scenario response."""

from pydantic import BaseModel


class FairValueScenario(BaseModel):
    name: str
    pe_multiple: float
    fair_value: float
    upside_pct: float


class FairValueRead(BaseModel):
    ticker: str
    forward_eps: float
    current_price: float | None
    growth_estimate: float | None
    base_pe: float
    scenarios: list[FairValueScenario]
