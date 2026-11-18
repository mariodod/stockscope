# Stockscope — Project Plan

## 1. Vision

Make it effortless to answer questions like *"which profitable, reasonably valued US companies have the strongest growth and lowest debt?"* by turning raw market data into a searchable, rankable universe of public companies.

## 2. Goals

1. **Coverage** — ingest the full US-listed universe (NYSE, NASDAQ, AMEX) and keep it current.
2. **Breadth of metrics** — store the fundamentals that investors actually screen on (valuation, profitability, growth, leverage, liquidity, dividends).
3. **Fast screening** — filter, sort, and rank thousands of companies interactively with sub-second API responses.
4. **Composability** — providers, metrics, and scoring are pluggable; adding a data source or metric is a localized change.
5. **Trust** — every displayed value has a known source and as-of date; data quality issues are visible, not hidden.

## 3. Non-goals (v1)

- Trading, order execution, or portfolio management.
- Real-time streaming quotes (daily/EOD data is sufficient).
- Full global coverage (schema supports it; provider budget/coverage does not yet).
- Price prediction or investment recommendations.
- User accounts / multi-tenancy.

## 4. Success criteria

- [ ] Universe contains ≥ 5,000 US-listed companies with identifiers and sector/industry.
- [ ] ≥ 30 documented metrics available for the majority of covered companies.
- [ ] A screen across all companies with 5 filters + 3 sort keys completes in < 1s locally.
- [ ] Composite ranking is reproducible: same inputs always produce the same rank.
- [ ] Ingestion is idempotent: rerunning a sync does not create duplicate rows or drift values.
- [ ] Dashboard shows a sortable/filterable table and a company detail page with a fundamentals chart.
- [ ] `README.md` quick start works from a clean clone.

## 5. Users & core use cases

| Persona | Use case |
| --- | --- |
| Researcher / retail investor | Screen the market by valuation + quality metrics and save a shortlist. |
| Data-oriented user | Query the API directly for a filtered/ranked dataset to use in a notebook. |
| Developer | Add a new provider or metric without rewriting the API or UI. |

## 6. Architecture

### 6.1 Components

```
                +-------------------+
                |   Provider API    |  FMP / yfinance / SEC EDGAR
                +---------+---------+
                          |
                +---------v---------+
                |  Provider adapters|  normalize into a common schema
                +---------+---------+
                          |
                +---------v---------+
                |  Ingestion jobs   |  universe sync, fundamentals refresh, quote refresh
                +---------+---------+
                          |
                +---------v---------+
                |  Database         |  companies, facts, quotes, metric_defs, refresh_runs
                +---------+---------+
                          |
                +---------v---------+
                |  FastAPI service  |  /companies, /screen, /companies/{id}, /metrics, /refresh
                +---------+---------+
                          |
                +---------v---------+
                |  React dashboard  |  screener table, filters, detail page, charts
                +-------------------+
```

### 6.2 Repository layout

```
stockscope/
├── app/                     # FastAPI backend
│   ├── main.py              # app entrypoint, router registration
│   ├── config.py            # settings from environment
│   ├── db/                  # session, base, Alembic migrations
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response models
│   ├── api/v1/              # routers: companies, screen, metrics, admin
│   ├── providers/           # adapter protocol + FMP / yfinance / SEC implementations
│   ├── ingestion/           # sync jobs, normalization, upsert logic
│   ├── services/            # screening, ranking/scoring, company detail
│   └── worker/              # APScheduler scheduler
├── frontend/                # React + TypeScript + Vite
│   └── src/
│       ├── components/      # DataTable, FilterBar, MetricBadge, charts
│       ├── pages/           # ScreenerPage, CompanyPage
│       ├── hooks/           # TanStack Query hooks
│       ├── lib/             # API client, metric formatters, types
│       └── types/
├── docs/                    # architecture notes and data sources
├── tests/                   # backend unit + integration tests
├── alembic/                 # DB migrations
├── docker-compose.yml       # PostgreSQL for local development
├── .env.example
├── PLAN.md
└── README.md
```

### 6.3 Tech stack

| Concern | Choice | Rationale |
| --- | --- | --- |
| Language / data | Python 3.12 + pandas | Richest ecosystem for financial data and transformation |
| API framework | FastAPI + Pydantic v2 | Typed validation, auto OpenAPI, async-friendly |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Mature, flexible, safe schema evolution |
| Database | PostgreSQL (prod), SQLite (dev) | Indexed filtering; frictionless local start via `DATABASE_URL` |
| Jobs | APScheduler; later Celery + Redis | Start simple, scale out only if refresh times demand it |
| HTTP client | httpx | Async, timeouts, retries, testable |
| Frontend | React 18 + TypeScript + Vite | Standard, fast, strongly typed |
| Table | TanStack Table | Headless control over sorting/filtering/pagination |
| Server state | TanStack Query | Caching, loading/error states, refetch control |
| Charts | Recharts | Simple declarative fundamentals charts |
| Styles | Tailwind CSS | Rapid, consistent UI |
| Tooling | ruff, mypy, pytest, ESLint, Prettier | Fast, consistent quality gates |

### 6.4 Data model (initial entities)

| Entity | Key fields | Notes |
| --- | --- | --- |
| `Company` | id, ticker (unique), cik, name, exchange, sector, industry, country, currency, is_active, listed_at | The central entity; `country` enables global expansion |
| `FundamentalFact` | company_id, metric_key, period, fiscal_year, value, unit, source, as_of_date, filed_at | Long/tall table so new metrics need no schema change; unique constraint on (company, metric, period, source) |
| `Quote` | company_id, date, price, market_cap, pe_ratio, volume, fifty_two_week_high/low | Time-series of daily market data |
| `MetricDefinition` | key, label, category, unit, direction, source/formula, description | Drives UI columns, filters, and documentation from one place |
| `RefreshRun` | id, job, provider, started_at, finished_at, status, rows_written, error | Observability into ingestion; makes failures debuggable |

Design notes:
- A **tall facts table** (`FundamentalFact`) plus a **metric registry** avoids adding a column for every new metric and lets the UI generate controls dynamically.
- Latest values are materialized into a `company_latest_metrics` view (or cached table, if query speed requires it) so screening does not scan all history.
- All monetary values are stored in the company's reporting **currency** with `unit` metadata; v1 will not do FX conversion (documented limitation).
- Every fact stores `source` + `as_of_date`, so staleness is visible in the UI.

## 7. Data strategy

### 7.1 Provider comparison

| Source | Cost | Coverage | Strengths | Limitations |
| --- | --- | --- | --- | --- |
| Financial Modeling Prep (free tier) | Free key | US-focused, broad | Quote/market cap, company profile, some ratios; simple REST | Strict daily request cap; free-tier endpoints limited |
| yfinance (Yahoo) | Free, no key | Global, broad | Rich `.info` (TTM ratios, margins, growth) + financials | Unofficial, rate-limited, can break without notice; not for production SLAs |
| SEC EDGAR XBRL / companyfacts | Free, no key | US filers only | Authoritative fundamentals, full history | US-only, slower refresh, requires User-Agent, XBRL mapping effort |
| NASDAQ screener endpoint | Free, no key | US listings | Full ticker universe + basic fields | Undocumented, fragile |

**Decision:** start with a **provider adapter interface** and two sources: FMP (primary quote/profile) and yfinance (fundamental ratios), with SEC EDGAR as the authoritative fallback for US fundamentals. The interface means a later switch to a paid provider (Polygon, FMP paid, Tiingo) is a config change, not a rewrite. See [docs/data-sources.md](docs/data-sources.md).

### 7.2 Adapter interface (conceptual)

```python
class Provider(Protocol):
    name: str
    def list_companies(self) -> Iterator[CompanySeed]: ...
    def get_quote(self, ticker: str) -> Quote: ...
    def get_fundamentals(self, ticker: str) -> list[FundamentalFact]: ...
```

Each adapter is responsible for: rate limiting, retries with backoff, mapping provider fields to canonical `metric_key`s, and stamping `source` / `as_of_date`. The ingestion layer knows nothing about provider-specific payloads.

### 7.3 Refresh strategy

- **Universe sync** — weekly (new listings, delistings, ticker changes).
- **Quote refresh** — daily after market close; cached for the day.
- **Fundamentals refresh** — weekly check for new filings; only changed facts are upserted.
- Jobs are idempotent (upsert on natural keys) and record a `RefreshRun`.
- Provider keys live in `.env` and are never committed.

### 7.4 Data quality & normalization

- Canonical `metric_key` registry maps provider-specific names to one vocabulary (see [metrics catalog](../app/seed/metrics_catalog.md)).
- EBITDA is derived when absent: `operating income + depreciation & amortization`; the derivation is recorded in `MetricDefinition.formula`.
- Nulls are preserved (never silently zero-filled); UI shows "n/a" and excludes nulls from rankings.
- Outlier/winsorization rules are applied at ranking time, not at storage time, so raw data stays intact.

## 8. Screening & ranking design

### 8.1 Filter grammar

Filters are expressed as structured conditions on `metric_key`:

```json
{
  "filters": [
    {"metric": "market_cap", "op": "gte", "value": 1e9},
    {"metric": "pe_ratio", "op": "between", "value": [0, 25]},
    {"metric": "sector", "op": "eq", "value": "Technology"},
    {"metric": "debt_to_equity", "op": "lte", "value": 1.0}
  ],
  "sort": [{"metric": "revenue_growth_yoy", "dir": "desc"}],
  "ranking": {"weights": {"pe_ratio": 0.2, "roe": 0.3, "revenue_growth_yoy": 0.5}},
  "limit": 50, "offset": 0
}
```

Operators: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `between`, `in`, `is_null`. Whitelist metric keys from `MetricDefinition` to prevent arbitrary SQL. Build queries with SQLAlchemy expressions (parameterized), never string concatenation.

### 8.2 Composite ranking

1. For each weighted metric, compute a **percentile rank** across the filtered universe (0–1), oriented by the metric's `direction` (e.g. lower P/E is better).
2. Missing values are scored at the neutral point (0.5) and flagged, so companies are not unfairly penalized for sparse data.
3. Composite = weighted sum of oriented percentile ranks.
4. Deterministic tie-break by ticker. Weight normalization is enforced (weights sum to 1).

This is explainable (each component is visible per company) and robust to outliers.

### 8.3 API endpoints (v1)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/companies` | Paginated, filterable, sortable company list |
| `POST` | `/api/v1/screen` | Full screen with filters, sort, and composite ranking |
| `GET` | `/api/v1/companies/{ticker}` | Company detail + latest metrics + history |
| `GET` | `/api/v1/metrics` | Metric registry (drives UI controls) |
| `GET` | `/api/v1/sectors` | Distinct sectors/industries for filter dropdowns |
| `POST` | `/api/v1/refresh` | Trigger ingestion job (auth-protected) |
| `GET` | `/api/v1/health` | Health check |

All list endpoints return `total`, `limit`, `offset`, and `items` for pagination.

## 9. Frontend design

- **Screener page** — metric registry drives columns and filter controls; TanStack Table provides sorting, multi-column filtering, pagination, and column visibility. Users can apply a composite ranking with adjustable weights.
- **Company page** — header with key metrics, a fundamentals timeline chart (revenue, EBITDA, EPS), and a table of all latest metrics with source + as-of date.
- **Formatting** — currency/percent/ratio formatters keyed by metric `unit`; color signals for positive/negative values and staleness.
- **State** — filters and sort are reflected in the URL so screens are shareable. TanStack Query caches API responses.

## 10. Phases & milestones

Each milestone ends in a verifiable state. Acceptance criteria are checked before the next phase begins.

### M1 — Foundation & data model
- Repo scaffold, `pyproject.toml`, lint/type/test config, Docker Compose Postgres, Alembic setup.
- ORM models + first migration; metric registry seeded from `app/seed/metrics_catalog.md`.
- FastAPI skeleton with `/health` and `/metrics`; CI runs lint + tests.
- **Acceptance:** clean clone → `docker compose up -d` → API `/docs` works; migration runs; tests pass.

### M2 — Data ingestion
- Provider protocol + FMP, yfinance, and SEC adapters with retries/rate limiting.
- Universe sync, fundamentals refresh, quote refresh jobs; normalization into canonical metrics.
- Idempotent upserts and `RefreshRun` logging; scheduler wired up.
- **Acceptance:** a fresh DB syncs ≥ 5,000 companies and populates the core metrics; rerunning produces no duplicates.

### M3 — Screening & ranking API
- `/companies`, `/screen`, `/companies/{ticker}`, `/sectors` endpoints.
- Filter grammar, safe query builder, percentile composite scoring.
- Pagination, response schemas, OpenAPI docs, integration tests with seeded fixtures.
- **Acceptance:** documented query returns correct, stable results; < 1s on the seeded full universe.

### M4 — Web dashboard
- Vite/React/TS app, API client, generated types from OpenAPI.
- Screener table with filters/sorting/pagination/column control.
- Company detail page with fundamentals chart; URL-synced state.
- **Acceptance:** a user can filter, rank, and drill into a company end-to-end against the live API.

### M5 — Hardening & delivery
- Caching, rate-limit resilience, error handling, structured logging.
- Data-quality dashboard/staleness indicators, README quick start, deploy config (Dockerfile + Compose for full stack).
- Performance pass on screening queries (indexes / materialized view).
- **Acceptance:** documented local + containerized start works; quality gates green; known limitations documented.

## 11. Risks & mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Free-tier rate limits and missing fields | Incomplete coverage | Adapter abstraction; cache aggressively; batch/space requests; SEC fallback; document coverage % |
| yfinance instability | Ingestion failures | Isolate behind adapter; retries/backoff; treat as best-effort; easy swap to paid provider |
| "All public companies" is beyond free sources | Scope disappointment | v1 = US-listed; schema has `country`/`exchange` for global expansion; paid provider is a config change |
| Inconsistent metric definitions across providers | Misleading comparisons | Canonical metric registry + documented formulas; store source per fact |
| EBITDA not directly available | Missing key metric | Derive from operating income + D&A; record formula and flag derived values |
| Slow screens at scale | Poor UX | Indexed columns, materialized latest-metrics view, pagination, query tests |

## 12. Testing strategy

- **Unit:** normalization/metric mapping, score math, formatters, filter operator translation.
- **Integration:** API endpoints against a seeded test DB (SQLite in-memory or test Postgres).
- **Contract:** provider adapter tests using recorded fixture payloads (no live API calls in CI).
- **Idempotency:** run ingestion twice against a fixture DB and assert identical state.
- **Frontend:** component tests for table/filter behavior; mock API responses.

## 13. Operations & deployment

- Configuration entirely via environment variables (`.env.example` documents all keys).
- Docker Compose brings up DB + API + frontend for local and single-host deployment.
- Alembic migrations are the only way schema changes reach a database.
- Ingestion runs as a scheduled process; failures are recorded in `RefreshRun` and logged.
- No secrets in the repository; free-tier keys are user-supplied.

## 14. Decisions log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-11-19 | Web dashboard as primary interface | Visual exploration and ranking of many companies is the core need |
| 2026-11-19 | Free-tier providers first | Validate the model at zero cost; keep provider layer swappable |
| 2026-11-19 | US-listed first, global-ready schema | Focus scope; `country`/`exchange` fields allow later expansion |
| 2026-11-19 | Python (FastAPI) + React/TS | Best data tooling in Python, strong typed frontend |
| 2026-11-19 | Metric registry is parsed from `app/seed/metrics_catalog.md` | The catalog stays the single source of truth and ships inside the package |
| 2026-11-19 | Use `uvicorn` without the `standard` extra | Its PyYAML dependency has no Python 3.15 wheel and requires a C compiler locally; the extra is not needed |

## 15. Open questions (revisit before M2)

- Which free provider tier gives the best metric coverage in practice? (validate with a small sample during M1.)
- Is SEC EDGAR mapping worth the effort in v1, or only for the metrics yfinance lacks?
- Should latest metrics be a materialized view refreshed per ingestion, or computed on the fly? (Measure in M3.)
- What is the retention policy for daily quote history (1y vs 5y)?
