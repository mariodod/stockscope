"""Adapter tests using recorded-style payloads; no live provider calls in CI."""

from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from app.providers import FMPProvider, SECProvider, YFinanceProvider
from app.providers.http import ProviderHttpError, fetch_json


def _client(handler: Any, base_url: str = "https://example.test") -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url=base_url)


def test_fmp_adapter_maps_universe_quote_and_ratios() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/stock/list"):
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "AAPL",
                        "companyName": "Apple Inc.",
                        "cik": "0000320193",
                        "exchange": "NASDAQ",
                    },
                    {"symbol": "", "companyName": "No ticker"},
                ],
            )
        if path.endswith("/quote/AAPL"):
            return httpx.Response(
                200,
                json=[
                    {
                        "price": 190.5,
                        "marketCap": 3000000000000,
                        "pe": 30.2,
                        "volume": 50000000,
                        "fiftyTwoWeekHigh": 200,
                        "fiftyTwoWeekLow": 150,
                    }
                ],
            )
        if path.endswith("/ratios/AAPL"):
            return httpx.Response(
                200,
                json=[{"calendarYear": "2025", "date": "2025-12-31", "returnOnEquity": 0.45}],
            )
        return httpx.Response(404, json={})

    provider = FMPProvider(client=_client(handler), api_key="test-key")
    companies = list(provider.list_companies())
    assert [seed.ticker for seed in companies] == ["AAPL"]
    assert companies[0].cik == "0000320193"

    quote = provider.get_quote("AAPL")
    assert quote is not None
    assert quote.price == Decimal("190.5")
    assert quote.market_cap == Decimal("3000000000000")
    assert quote.source == "fmp"

    facts = list(provider.get_fundamentals("AAPL"))
    assert len(facts) == 1
    assert facts[0].metric_key == "roe"
    assert facts[0].unit == "percent"
    assert facts[0].as_of_date == date(2025, 12, 31)


def test_fetch_json_retries_server_errors(monkeypatch: Any) -> None:
    calls = {"n": 0}
    slept: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr("app.providers.http.time.sleep", slept.append)
    result = fetch_json(_client(handler), "/flaky")

    assert result == {"ok": True}
    assert calls["n"] == 2
    assert slept == [0.1]


def test_fetch_json_raises_after_retries(monkeypatch: Any) -> None:
    monkeypatch.setattr("app.providers.http.time.sleep", lambda seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    try:
        fetch_json(_client(handler), "/busy")
    except ProviderHttpError:
        assert True
    else:
        raise AssertionError("expected ProviderHttpError")


def test_sec_adapter_maps_universe_and_derives_ebitda() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "company_tickers.json" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
                },
            )
        if "companyfacts" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "facts": {
                        "us-gaap": {
                            "Revenues": {
                                "units": {
                                    "USD": [
                                        {"form": "10-K", "end": "2025-09-27", "val": 391000000000}
                                    ]
                                }
                            },
                            "OperatingIncomeLoss": {
                                "units": {
                                    "USD": [
                                        {"form": "10-K", "end": "2025-09-27", "val": 123000000000}
                                    ]
                                }
                            },
                            "DepreciationDepletionAndAmortization": {
                                "units": {
                                    "USD": [
                                        {"form": "10-K", "end": "2025-09-27", "val": 11000000000}
                                    ]
                                }
                            },
                        }
                    }
                },
            )
        return httpx.Response(404, json={})

    provider = SECProvider(client=_client(handler), user_agent="test-agent")
    companies = list(provider.list_companies())
    assert companies[0].ticker == "AAPL"
    assert companies[0].cik == "320193"
    assert provider.get_quote("AAPL") is None

    facts = {fact.metric_key: fact for fact in provider.get_fundamentals("AAPL", "320193")}
    assert facts["revenue"].value == Decimal("391000000000")
    assert facts["ebitda"].value == Decimal("134000000000")
    assert provider.name == "sec"


def test_yfinance_adapter_uses_injected_ticker() -> None:
    class FakeTicker:
        info = {
            "currentPrice": 100,
            "marketCap": 1000000000,
            "trailingPE": 25,
            "volume": 1234,
            "returnOnEquity": 0.2,
            "ebitda": 250000000,
        }

    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker())
    quote = provider.get_quote("FAKE")
    assert quote is not None
    assert quote.price == Decimal("100")
    assert quote.source == "yfinance"

    keys = {fact.metric_key for fact in provider.get_fundamentals("FAKE")}
    assert {"pe_ratio", "roe", "ebitda"} <= keys
