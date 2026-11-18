"""SEC EDGAR adapter: free company universe and authoritative XBRL facts."""

from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.providers.base import CompanySeed, FactSeed
from app.providers.http import fetch_json
from app.providers.values import dec

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

TAG_MAP = {
    "Revenues": ("revenue", "currency"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("revenue", "currency"),
    "OperatingIncomeLoss": ("operating_income", "currency"),
    "DepreciationDepletionAndAmortization": ("depreciation", "currency"),
    "EarningsPerShareDiluted": ("eps_ttm", "currency"),
    "CashAndCashEquivalentsAtCarryingValue": ("cash_and_equivalents", "currency"),
}


class SECProvider:
    name = "sec"

    def __init__(self, client: httpx.Client | None = None, user_agent: str = "") -> None:
        self.client = client or httpx.Client(timeout=20.0)
        self.user_agent = user_agent or settings.sec_user_agent

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def list_companies(self) -> Iterator[CompanySeed]:
        payload = fetch_json(self.client, TICKERS_URL, headers=self._headers())
        for row in payload.values():
            ticker = row.get("ticker")
            if not ticker:
                continue
            yield CompanySeed(
                ticker=ticker,
                name=row.get("title") or ticker,
                cik=str(row["cik_str"]),
                country="US",
                currency="USD",
            )

    def get_quote(self, ticker: str) -> None:
        return None

    def _latest_usd(self, facts: dict[str, Any], tag: str) -> tuple[float | None, date | None]:
        units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
        entries = units.get("USD", [])
        annual = [entry for entry in entries if entry.get("form") in {"10-K", "10-Q"}]
        if not annual:
            return None, None
        latest = max(annual, key=lambda entry: entry.get("end", ""))
        return latest.get("val"), date.fromisoformat(latest["end"])

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
        if not cik:
            return
        facts = fetch_json(
            self.client, FACTS_URL.format(cik=int(cik)), headers=self._headers()
        )
        values: dict[str, tuple[float | None, date | None]] = {}
        for tag, (metric_key, _unit) in TAG_MAP.items():
            latest = self._latest_usd(facts, tag)
            if latest[0] is not None:
                values[metric_key] = latest

        operating_income, income_date = values.get("operating_income", (None, None))
        depreciation, _ = values.get("depreciation", (None, None))
        if operating_income is not None and depreciation is not None:
            yield FactSeed(
                metric_key="ebitda",
                period="TTM",
                value=dec(operating_income + depreciation),
                unit="currency",
                as_of_date=income_date or date.today(),
                source=self.name,
                notes="operating income + depreciation and amortization",
            )

        for metric_key in ("revenue", "eps_ttm", "cash_and_equivalents"):
            value, as_of_date = values.get(metric_key, (None, None))
            if value is None:
                continue
            yield FactSeed(
                metric_key=metric_key,
                period="TTM",
                value=dec(value),
                unit="currency",
                as_of_date=as_of_date or date.today(),
                source=self.name,
            )
