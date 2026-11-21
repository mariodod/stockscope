"""SEC EDGAR adapter: free company universe and authoritative XBRL facts."""

from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.providers.base import CompanySeed, FactSeed, FilingSeed
from app.providers.http import RateLimiter, fetch_json
from app.providers.values import dec

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

TAG_MAP = {
    "Revenues": ("revenue", "currency"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("revenue", "currency"),
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

    def get_recent_filings(
        self, cik: str | None, limit: int = 20
    ) -> Iterator[FilingSeed]:
        if not cik:
            return
        payload = fetch_json(
            self.client,
            SUBMISSIONS_URL.format(cik=int(cik)),
            headers=self._headers(),
            limiter=self.limiter,
        )
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        documents = recent.get("primaryDocument", [])
        for index, accession in enumerate(recent.get("accessionNumber", [])[:limit]):
            if index >= len(forms) or index >= len(dates):
                break
            form = forms[index]
            filing_date = dates[index]
            try:
                day = date.fromisoformat(filing_date)
            except (TypeError, ValueError):
                continue
            yield FilingSeed(
                accession_number=str(accession),
                form=str(form),
                filing_date=day,
                primary_document=documents[index] if index < len(documents) else None,
                source=self.name,
            )

    def _entries(
        self, facts: dict[str, Any], tag: str, unit: str = "USD"
    ) -> list[tuple[date | None, date, date | None, float]]:
        units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
        entries: list[tuple[date | None, date, date | None, float]] = []
        for entry in units.get(unit, []):
            if entry.get("form") not in {"10-K", "10-Q"} or entry.get("val") is None:
                continue
            try:
                end = date.fromisoformat(entry["end"])
            except (KeyError, ValueError, TypeError):
                continue
            start = None
            if entry.get("start"):
                try:
                    start = date.fromisoformat(entry["start"])
                except ValueError:
                    start = None
            filed = None
            if entry.get("filed"):
                try:
                    filed = date.fromisoformat(entry["filed"])
                except ValueError:
                    filed = None
            entries.append((start, end, filed, entry["val"]))
        return entries

    def _select(
        self, entries: list[tuple[date | None, date, date | None, float]]
    ) -> tuple[date | None, date, date | None, float]:
        return max(
            entries,
            key=lambda entry: (
                entry[1],
                (entry[1] - entry[0]).days if entry[0] else 0,
                entry[2] or date.min,
            ),
        )

    @staticmethod
    def _period(start: date | None, end: date) -> str:
        return "FY" if start is not None and (end - start).days >= 300 else "Q"

    def _latest(
        self, facts: dict[str, Any], tag: str, unit: str = "USD"
    ) -> tuple[float | None, date | None, str | None]:
        entries = self._entries(facts, tag, unit)
        if not entries:
            return None, None, None
        start, end, _, value = self._select(entries)
        return value, end, self._period(start, end)

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
        if not cik:
            return
        facts = fetch_json(
            self.client,
            FACTS_URL.format(cik=int(cik)),
            headers=self._headers(),
            limiter=self.limiter,
        )
        values: dict[str, tuple[float | None, date | None, str | None]] = {}
        for tag, (metric_key, _unit) in TAG_MAP.items():
            unit = "USD/shares" if metric_key == "eps_ttm" else "USD"
            latest = self._latest(facts, tag, unit)
            if latest[0] is not None:
                values[metric_key] = latest

        operating_entries = self._entries(facts, "OperatingIncomeLoss")
        if operating_entries:
            start, end, _, operating_income = self._select(operating_entries)
            depreciation_entries = [
                entry
                for entry in self._entries(facts, "DepreciationDepletionAndAmortization")
                if entry[0] == start and entry[1] == end
            ]
            if depreciation_entries:
                depreciation = self._select(depreciation_entries)[3]
                yield FactSeed(
                    metric_key="ebitda",
                    period=self._period(start, end),
                    value=dec(operating_income + depreciation),
                    unit="currency",
                    as_of_date=end,
                    source=self.name,
                )

        for metric_key in ("revenue", "eps_ttm", "cash_and_equivalents"):
            value, as_of_date, period = values.get(metric_key, (None, None, None))
            if value is None:
                continue
            yield FactSeed(
                metric_key=metric_key,
                period=period or "FY",
                value=dec(value),
                unit="currency",
                as_of_date=as_of_date or date.today(),
                source=self.name,
            )
