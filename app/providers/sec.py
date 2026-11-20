"""SEC EDGAR adapter: free company universe and authoritative XBRL facts."""

from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.providers.base import CompanySeed, FactSeed
from app.providers.http import RateLimiter, fetch_json
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

    def __init__(
        self,
        client: httpx.Client | None = None,
        user_agent: str = "",
        limiter: RateLimiter | None = None,
    ) -> None:
        self.client = client or httpx.Client(timeout=20.0)
        self.user_agent = user_agent or settings.sec_user_agent
        self.limiter = limiter

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def list_companies(self) -> Iterator[CompanySeed]:
        payload = fetch_json(
            self.client, TICKERS_URL, headers=self._headers(), limiter=self.limiter
        )
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

    def _usd_by_end(self, facts: dict[str, Any], tag: str) -> dict[date, float]:
        units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
        values: dict[date, float] = {}
        for entry in units.get("USD", []):
            if entry.get("form") not in {"10-K", "10-Q"}:
                continue
            end, value = entry.get("end"), entry.get("val")
            if not end or value is None:
                continue
            try:
                values[date.fromisoformat(end)] = value
            except ValueError:
                continue
        return values

    def _latest_usd(self, facts: dict[str, Any], tag: str) -> tuple[float | None, date | None]:
        by_end = self._usd_by_end(facts, tag)
        if not by_end:
            return None, None
        latest_end = max(by_end)
        return by_end[latest_end], latest_end

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
        if not cik:
            return
        facts = fetch_json(
            self.client,
            FACTS_URL.format(cik=int(cik)),
            headers=self._headers(),
            limiter=self.limiter,
        )
        values: dict[str, tuple[float | None, date | None]] = {}
        for tag, (metric_key, _unit) in TAG_MAP.items():
            latest = self._latest_usd(facts, tag)
            if latest[0] is not None:
                values[metric_key] = latest

        operating_income, income_date = values.get("operating_income", (None, None))
        if operating_income is not None and income_date is not None:
            depreciation = self._usd_by_end(
                facts, "DepreciationDepletionAndAmortization"
            ).get(income_date)
            if depreciation is not None:
                yield FactSeed(
                    metric_key="ebitda",
                    period="TTM",
                    value=dec(operating_income + depreciation),
                    unit="currency",
                    as_of_date=income_date,
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
