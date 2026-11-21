"""Request and response models for the returns simulator."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Strategy(StrEnum):
    LUMP_SUM = "lump_sum"
    DCA = "dca"


class SimulationRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=20)
    start: date
    end: date
    initial: float = Field(ge=0)
    contribution: float = Field(default=0, ge=0)
    strategy: Strategy = Strategy.LUMP_SUM
    dividend_reinvestment: bool = True
    benchmark: str | None = "SPY"

    @model_validator(mode="after")
    def check_period(self) -> "SimulationRequest":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        if self.strategy is Strategy.DCA and self.contribution <= 0:
            raise ValueError("DCA requires a positive contribution")
        if self.strategy is Strategy.LUMP_SUM and self.initial <= 0:
            raise ValueError("Lump sum requires a positive initial investment")
        return self


class Performance(BaseModel):
    final_value: float
    total_contributed: float
    total_return_pct: float
    annualised_return_pct: float
    max_drawdown_pct: float


class SimulationPoint(BaseModel):
    date: date
    value: float
    benchmark_value: float | None = None


class SimulationResult(BaseModel):
    performance: Performance
    benchmark: Performance | None = None
    series: list[SimulationPoint]
