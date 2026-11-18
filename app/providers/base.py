"""Canonical data shapes returned by every provider adapter."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CompanySeed:
    ticker: str
    name: str
    cik: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str = "US"
    currency: str = "USD"


@dataclass(frozen=True)
class QuoteSeed:
    date: date
    price: Decimal | None = None
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    volume: int | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None
    source: str = ""


@dataclass(frozen=True)
class FactSeed:
    metric_key: str
    period: str
    value: Decimal | None
    unit: str
    as_of_date: date
    fiscal_year: int | None = None
    filed_at: datetime | None = None
    source: str = ""
    notes: str | None = None


class Provider(Protocol):
    name: str

    def list_companies(self) -> Iterator[CompanySeed]: ...

    def get_quote(self, ticker: str) -> QuoteSeed | None: ...

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]: ...
