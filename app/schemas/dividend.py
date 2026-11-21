"""Dividend calendar response."""

from datetime import date

from pydantic import BaseModel


class DividendRead(BaseModel):
    ticker: str
    company_name: str
    ex_date: date
    pay_date: date | None = None
    amount_per_share: float | None = None
    source: str
