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


def test_fetch_json_retries_transport_errors(monkeypatch: Any) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("flaky connection")
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr("app.providers.http.time.sleep", lambda seconds: None)

    assert fetch_json(_client(handler), "/flaky") == {"ok": True}
    assert calls["n"] == 3


def test_fetch_json_raises_provider_error_on_transport_failure(monkeypatch: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr("app.providers.http.time.sleep", lambda seconds: None)

    try:
        fetch_json(_client(handler), "/down")
    except ProviderHttpError:
        assert True
    else:
        raise AssertionError("expected ProviderHttpError")


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


def test_sec_ebitda_requires_matching_periods() -> None:
    def payload(depreciation_end: str) -> dict[str, Any]:
        return {
            "facts": {
                "us-gaap": {
                    "OperatingIncomeLoss": {
                        "units": {
                            "USD": [{"form": "10-K", "end": "2025-12-31", "val": 100}]
                        }
                    },
                    "DepreciationDepletionAndAmortization": {
                        "units": {
                            "USD": [{"form": "10-K", "end": depreciation_end, "val": 20}]
                        }
                    },
                }
            }
        }

    mismatched = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload("2024-12-31")))
    )
    assert "ebitda" not in {
        fact.metric_key for fact in SECProvider(client=mismatched).get_fundamentals("X", "1")
    }

    matched = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload("2025-12-31")))
    )
    facts = {
        fact.metric_key: fact
        for fact in SECProvider(client=matched).get_fundamentals("X", "1")
    }
    assert facts["ebitda"].value == Decimal("120")


def test_sec_reads_per_share_eps() -> None:
    payload = {
        "facts": {
            "us-gaap": {
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {
                                "form": "10-K",
                                "start": "2025-01-01",
                                "end": "2025-12-31",
                                "val": 6.5,
                                "filed": "2026-02-01",
                            }
                        ]
                    }
                }
            }
        }
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )

    facts = {
        fact.metric_key: fact
        for fact in SECProvider(client=client).get_fundamentals("X", "1")
    }

    assert facts["eps_ttm"].value == Decimal("6.5")
    assert facts["eps_ttm"].period == "FY"


def test_sec_keeps_newest_revenue_from_duplicate_tags() -> None:
    def entry(value: int, end: str) -> dict[str, Any]:
        return {"form": "10-K", "start": "2025-01-01", "end": end, "val": value, "filed": end}

    payload = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [entry(100, "2025-12-31")]}},
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [entry(80, "2024-12-31")]}
                },
            }
        }
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )

    facts = {
        fact.metric_key: fact
        for fact in SECProvider(client=client).get_fundamentals("X", "1")
    }

    assert facts["revenue"].value == Decimal("100")
    assert facts["revenue"].as_of_date == date(2025, 12, 31)


def test_fmp_numeric_timestamps_are_parsed() -> None:
    from app.providers.values import as_of

    assert as_of(1767225600, date(2026, 11, 21)) == date(2026, 1, 1)
    assert as_of(1767225600000, date(2026, 11, 21)) == date(2026, 1, 1)


def test_sec_ebitda_matches_reporting_duration() -> None:
    def entry(start: str, val: int, filed: str) -> dict[str, Any]:
        return {"form": "10-K", "start": start, "end": "2025-03-31", "val": val, "filed": filed}

    payload = {
        "facts": {
            "us-gaap": {
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            entry("2025-01-01", 30, "2025-05-02"),
                            entry("2024-04-01", 120, "2025-05-01"),
                        ]
                    }
                },
                "DepreciationDepletionAndAmortization": {
                    "units": {
                        "USD": [
                            entry("2024-04-01", 25, "2025-05-01"),
                            entry("2025-01-01", 5, "2025-05-02"),
                        ]
                    }
                },
            }
        }
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )

    facts = {
        fact.metric_key: fact
        for fact in SECProvider(client=client).get_fundamentals("X", "1")
    }

    assert facts["ebitda"].value == Decimal("145")
    assert facts["ebitda"].period == "FY"


def test_yfinance_price_history_maps_close_and_adjusted_close() -> None:
    import pandas as pd

    frame = pd.DataFrame(
        {
            "Close": [10.0, 11.0],
            "Adj Close": [9.8, 10.7],
            "Volume": [100, 200],
        },
        index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
    )

    class FakeTicker:
        def history(self, period: str, auto_adjust: bool) -> Any:
            assert period == "5y"
            assert auto_adjust is False
            return frame

    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker())
    rows = list(provider.get_price_history("AAPL", 5))

    assert len(rows) == 2
    assert rows[0].close == Decimal("10")
    assert rows[0].adjusted_close == Decimal("9.8")
    assert rows[1].volume == 200


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
