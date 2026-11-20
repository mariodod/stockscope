"""Financial Modeling Prep adapter (free tier)."""

from collections.abc import Iterator
from datetime import date

import httpx

from app.config import settings
from app.providers.base import CompanySeed, FactSeed, QuoteSeed
from app.providers.http import RateLimiter, fetch_json
from app.providers.values import as_of, dec, whole

RATIO_FIELDS = {
    "priceEarningsRatio": ("pe_ratio", "ratio"),
    "priceToBookRatio": ("price_to_book", "ratio"),
    "priceToSalesRatio": ("price_to_sales", "ratio"),
    "forwardPE": ("forward_pe", "ratio"),
    "pegRatio": ("peg_ratio", "ratio"),
    "returnOnEquity": ("roe", "percent"),
    "returnOnAssets": ("roa", "percent"),
    "currentRatio": ("current_ratio", "ratio"),
    "debtToEquity": ("debt_to_equity", "ratio"),
    "dividendYield": ("dividend_yield", "percent"),
    "payoutRatio": ("payout_ratio", "percent"),
    "grossProfitMargin": ("gross_margin", "percent"),
    "netProfitMargin": ("net_margin", "percent"),
}


class FMPProvider:
    name = "fmp"

    def __init__(
        self,
        client: httpx.Client | None = None,
        api_key: str = "",
        limiter: RateLimiter | None = None,
    ) -> None:
        self.client = client or httpx.Client(
            base_url="https://financialmodelingprep.com", timeout=15.0
        )
        self.api_key = api_key or settings.fmp_api_key
        self.limiter = limiter

    def _params(self, **extra: str) -> dict[str, str]:
        return {"apikey": self.api_key, **extra}

    def list_companies(self) -> Iterator[CompanySeed]:
        rows = fetch_json(
            self.client, "/api/v3/stock/list", params=self._params(), limiter=self.limiter
        )
        for row in rows:
            ticker = row.get("symbol")
            if not ticker:
                continue
            yield CompanySeed(
                ticker=ticker,
                name=row.get("companyName") or ticker,
                cik=str(row["cik"]) if row.get("cik") else None,
                exchange=row.get("exchange"),
            )

    def get_quote(self, ticker: str) -> QuoteSeed | None:
        rows = fetch_json(
            self.client, f"/api/v3/quote/{ticker}", params=self._params(), limiter=self.limiter
        )
        if not rows:
            return None
        row = rows[0]
        return QuoteSeed(
            date=as_of(row.get("timestamp"), date.today()),
            price=dec(row.get("price")),
            market_cap=dec(row.get("marketCap")),
            pe_ratio=dec(row.get("pe")),
            volume=whole(row.get("volume")),
            fifty_two_week_high=dec(row.get("range52WeekHigh") or row.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=dec(row.get("range52WeekLow") or row.get("fiftyTwoWeekLow")),
            source=self.name,
        )

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
        rows = fetch_json(
            self.client, f"/api/v3/ratios/{ticker}", params=self._params(), limiter=self.limiter
        )
        if not rows:
            return
        row = rows[0]
        today = date.today()
        as_of_date = as_of(row.get("date"), today)
        period = f"FY{row.get('calendarYear') or today.year}"
        for field, (metric_key, unit) in RATIO_FIELDS.items():
            value = dec(row.get(field))
            if value is None:
                continue
            yield FactSeed(
                metric_key=metric_key,
                period=period,
                value=value,
                unit=unit,
                as_of_date=as_of_date,
                source=self.name,
            )
