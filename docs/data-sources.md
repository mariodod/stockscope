# Data sources & provider strategy

## Principle

No provider is a hard dependency of the API or UI. All external data enters through a small `Provider` protocol; adapters own rate limiting, retries, field mapping, and provenance. Adding or replacing a source should not touch the screening logic.

## Candidates

| Source | Auth | Cost | Coverage | Good for | Watch out for |
| --- | --- | --- | --- | --- | --- |
| **Financial Modeling Prep** | API key (free tier) | Free tier | US-focused | Company profiles, sectors, quotes, market cap, selected ratios | Low daily request cap on free tier; some endpoints paid-only |
| **yfinance** | None | Free | Global | Rich TTM ratios, margins, growth, financial statements | Unofficial API, rate limits, can break; best-effort only |
| **SEC EDGAR companyfacts** | User-Agent header | Free | US filers | Authoritative, full-history XBRL fundamentals (revenue, income, assets, etc.) | US-only, slower refresh, XBRL tag mapping effort |
| **NASDAQ screener** | None | Free | US listings | Full ticker universe + basic descriptive fields | Undocumented, fragile; validate during M1 |

## Chosen approach for v1

1. **Universe** — SEC EDGAR `company_tickers.json` (free, no key); FMP stock list is available as an adapter but is not used by the universe job.
2. **Quotes & market cap** — FMP quote endpoints (daily refresh).
3. **Ratios & fundamentals** — yfinance `.info` / financials for breadth, with SEC EDGAR as the authoritative fallback for US filers and for history.
4. **Paid upgrade path** — if free coverage proves insufficient, swap in Polygon / FMP paid / Tiingo behind the same adapter interface. This is configuration + one adapter, not a rewrite.

## Adapter contract

```python
class Provider(Protocol):
    name: str

    def list_companies(self) -> Iterator[CompanySeed]: ...
    def get_quote(self, ticker: str) -> Quote: ...
    def get_fundamentals(self, ticker: str) -> list[FundamentalFact]: ...
```

Rules every adapter must follow:

- **Rate limiting & retries** — respect provider limits; exponential backoff on 429/5xx; never hammer on failure.
- **Canonical mapping** — translate provider field names into the `metric_key` vocabulary in [metrics_catalog.md](../app/seed/metrics_catalog.md).
- **Provenance** — stamp every fact with `source`, `as_of_date`, and (where relevant) `filed_at`.
- **Nulls** — preserve missing values as `None`; do not substitute zero.
- **Units & currency** — normalize to the metric's declared unit and record the reporting currency.

## Refresh cadence

| Job | Frequency | Notes |
| --- | --- | --- |
| Universe sync | Weekly | Detect new listings, delistings, ticker changes |
| Quote refresh | Daily (after close) | Cache for the day; idempotent upsert by (company, date) |
| Fundamentals refresh | Weekly | Only upsert changed facts; record `RefreshRun` with row counts |

## Attribution & compliance

- Free providers may require attribution or restrict commercial use. Record each provider's terms in this document before enabling it in production.
- API keys are stored only in environment variables / `.env`, never in source control.
- This project is research/educational and displays a "not financial advice" disclaimer.
