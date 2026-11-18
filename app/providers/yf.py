"""Yahoo Finance adapter, used for breadth of TTM ratios."""

from collections.abc import Callable
from datetime import date
from typing import Any

from app.providers.base import FactSeed, QuoteSeed
from app.providers.values import dec, whole

INFO_FIELDS = {
    "trailingPE": ("pe_ratio", "ratio"),
    "forwardPE": ("forward_pe", "ratio"),
    "pegRatio": ("peg_ratio", "ratio"),
    "priceToSalesTrailing12Months": ("price_to_sales", "ratio"),
    "priceToBook": ("price_to_book", "ratio"),
    "returnOnEquity": ("roe", "percent"),
    "returnOnAssets": ("roa", "percent"),
    "grossMargins": ("gross_margin", "percent"),
    "profitMargins": ("net_margin", "percent"),
    "ebitdaMargins": ("ebitda_margin", "percent"),
    "debtToEquity": ("debt_to_equity", "ratio"),
    "currentRatio": ("current_ratio", "ratio"),
    "dividendYield": ("dividend_yield", "percent"),
    "payoutRatio": ("payout_ratio", "percent"),
    "beta": ("beta", "ratio"),
}


class YFinanceProvider:
    name = "yfinance"

    def __init__(self, ticker_factory: Callable[[str], Any] | None = None) -> None:
        self._ticker_factory = ticker_factory

    def _ticker(self, ticker: str) -> Any:
        if self._ticker_factory is not None:
            return self._ticker_factory(ticker)
        import yfinance as yf

        return yf.Ticker(ticker)

    def list_companies(self) -> Any:
        return iter(())

    def get_quote(self, ticker: str) -> QuoteSeed | None:
        info = self._ticker(ticker).info
        if not info:
            return None
        return QuoteSeed(
            date=date.today(),
            price=dec(info.get("currentPrice") or info.get("regularMarketPrice")),
            market_cap=dec(info.get("marketCap")),
            pe_ratio=dec(info.get("trailingPE")),
            volume=whole(info.get("volume")),
            fifty_two_week_high=dec(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=dec(info.get("fiftyTwoWeekLow")),
            source=self.name,
        )

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Any:
        info = self._ticker(ticker).info
        if not info:
            return
        today = date.today()
        for field, (metric_key, unit) in INFO_FIELDS.items():
            value = dec(info.get(field))
            if value is None:
                continue
            yield FactSeed(
                metric_key=metric_key,
                period="TTM",
                value=value,
                unit=unit,
                as_of_date=today,
                source=self.name,
            )
        for field, metric_key in (("ebitda", "ebitda"), ("freeCashflow", "free_cash_flow")):
            value = dec(info.get(field))
            if value is not None:
                yield FactSeed(
                    metric_key=metric_key,
                    period="TTM",
                    value=value,
                    unit="currency",
                    as_of_date=today,
                    source=self.name,
                )
