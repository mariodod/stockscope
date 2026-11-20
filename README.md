# Stockscope

A stock screening and analysis platform for publicly listed companies. It pulls fundamentals and quotes from free data providers, stores them in a local database, and exposes them through a fast, filterable web dashboard.

> **Status: M1–M5 complete.** The roadmap lives in [PLAN.md](PLAN.md). Design decisions and reference material live in [docs/](docs/). Tracked work is in the [GitHub milestones and issues](https://github.com/mariodod/stockscope/issues).

## What it will do

- Track the **US-listed company universe** (NYSE / NASDAQ / AMEX), with a schema designed to add global exchanges later.
- Refresh market data on a schedule: price, market cap, P/E, EBITDA, EV/EBITDA, margins, growth, and more.
- **Filter and rank** companies by any metric, and combine metrics into a configurable composite score.
- Drill into a single company to see its fundamental history and charts.
- Keep data-source specifics behind adapters so providers can be swapped or added without touching the API or UI.

## Architecture at a glance

```
Provider adapters  ->  Ingestion jobs  ->  PostgreSQL / SQLite  ->  FastAPI  ->  React dashboard
 (FMP, yfinance,       (sync universe,     (normalized, indexed)    (screen,      (table, filters,
  SEC EDGAR)            refresh facts)                              rank, detail)   charts)
```

| Layer | Choice | Why |
| --- | --- | --- |
| Data ingestion / analysis | Python 3.12+, pandas | Best ecosystem for financial data wrangling |
| API | FastAPI, Pydantic | Fast to build, auto-generated OpenAPI docs, strong typing |
| Storage | SQLAlchemy + Alembic; PostgreSQL prod / SQLite dev | Indexed filtering and migrations; zero-friction local dev |
| Background jobs | APScheduler (later: Celery + Redis) | Simple scheduled refresh to start |
| Frontend | React + TypeScript + Vite | Mature, fast tooling |
| Table / data grid | TanStack Table | Headless sorting, filtering, pagination, column control |
| Charts | Recharts | Declarative React charts for fundamentals history |
| Styling | Tailwind CSS | Fast, consistent UI |

## Quick start

Requires Python 3.12+ and (for PostgreSQL) Docker.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"

cp .env.example .env                 # set POSTGRES_PASSWORD, then set DATABASE_URL to:
# DATABASE_URL=postgresql+psycopg://stockscope:<your-password>@localhost:5432/stockscope
docker compose up -d db              # PostgreSQL on 127.0.0.1:5432

alembic upgrade head                 # create schema
python -m app.seed.metrics           # load 38 metrics from the packaged catalog
uvicorn app.main:app --reload        # API: http://localhost:8000/docs
```

For a zero-dependency local run, skip Docker and the `.env` edit: the default `DATABASE_URL` is SQLite and creates `./stockscope.db`.

### Full stack in containers

Set `POSTGRES_PASSWORD` in `.env` first. `FMP_API_KEY` is optional; without it only the quote job cannot run.

```bash
docker compose up --build -d
```

This starts PostgreSQL (bound to localhost only), the API (which runs migrations and seeds metrics on boot), the React dashboard behind nginx at **http://localhost:8080**, and the APScheduler worker. The API is also exposed directly on port 8000. Stop everything with `docker compose down`.

## Web dashboard (M4)

The dashboard lives in `frontend/` and uses React, TypeScript, TanStack Table/Query, Tailwind CSS and Recharts. All API responses are validated with Zod at the boundary.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to localhost:8000)
```

`npm run test`, `npm run lint` and `npm run build` are the frontend quality gates; CI runs all three.

- **Screener** — filter by any metric, sort by one metric, toggle columns, add weighted composite ranking, and paginate.
- **Company detail** — fundamentals timeline (revenue, EBITDA, EPS) and latest metrics with source and as-of date.
- **Shareable state** — filters, sort, weights and pagination are encoded in the URL, so a screen can be bookmarked or sent to someone else.

## Data ingestion (M2)

Providers sit behind a common interface (`app/providers/base.py`) so a source can be swapped without touching the API or UI.

| Job | Provider | Command | Notes |
| --- | --- | --- | --- |
| `universe` | SEC EDGAR | `python -m app.ingestion.runner --job universe` | Free, no key; ~10,400 US listings |
| `quotes` | FMP | `python -m app.ingestion.runner --job quotes` | Needs `FMP_API_KEY` in `.env` |
| `fundamentals` | yfinance | `python -m app.ingestion.runner --job fundamentals --limit 100` | Free, no key; start with a limit to respect rate limits |

Use `--job all` to run every job. Each run writes a `RefreshRun` row with its status and row count. Jobs upsert on natural keys, so rerunning them does not create duplicates.

To run the refresh jobs on a schedule, start the APScheduler worker as a long-lived process (cron expressions come from `.env`):

```bash
python -m app.worker
```

Adapter tests use recorded-style payloads and run in CI without live API calls.

## Available endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Service status and version |
| `GET` | `/api/v1/metrics` | Metric registry; optional `?category=valuation` filter |
| `GET` | `/api/v1/companies` | Filterable, sortable, paginated company list |
| `POST` | `/api/v1/screen` | Structured filters, sorting, and composite ranking |
| `GET` | `/api/v1/companies/{ticker}` | Company detail with latest metrics and history |
| `GET` | `/api/v1/sectors` | Distinct sectors and industries for filter dropdowns |
| `GET` | `/api/v1/data-quality` | Metric coverage, staleness and latest refresh runs |
| `GET` | `/docs` | Interactive OpenAPI documentation |

Example screen request:

```json
{
  "filters": [
    {"metric": "market_cap", "op": "gte", "value": 1000000000},
    {"metric": "pe_ratio", "op": "between", "value": [0, 25]},
    {"metric": "sector", "op": "eq", "value": "Technology"}
  ],
  "sort": [{"metric": "revenue_growth_yoy", "dir": "desc"}],
  "ranking": {"weights": {"pe_ratio": 0.3, "roe": 0.7}},
  "limit": 50,
  "offset": 0
}
```

Filters are whitelisted against the metric registry and compiled into parameterized SQL. Composite scores are weighted sums of percentile ranks, oriented by each metric's direction; missing values score neutrally and are listed in `missing_metrics`. Results are tie-broken by ticker so repeated screens return the same order.

Run the reproducible benchmark with `python scripts/benchmark_screen.py`. A screen with three filters, three sort keys and composite ranking over 10,400 seeded companies (41,600 facts) completed in **0.848s** locally.

## Quality gates

```bash
ruff check .       # lint
mypy app           # strict type checking
pytest             # tests
```

For the frontend, run `npm --prefix frontend test`, `npm --prefix frontend lint` and `npm --prefix frontend build`. CI runs both backend and frontend jobs on every push and pull request.

## Known limitations

- Coverage is **US-listed companies only**. The schema supports a `country`/`exchange` field for future global expansion, but no non-US provider is wired in.
- The FMP quote adapter is covered by fixture tests; a live quote sync needs an `FMP_API_KEY` and was not verified in CI.
- `avg_volume` currently stores a single quote's daily volume, not a multi-day average.
- Free providers can be delayed, rate-limited or incomplete. The `/data-quality` endpoint and dashboard badges expose coverage and staleness, but data accuracy still needs verification against primary sources.
- Caching is in-memory and per process; a multi-process deployment would need a shared cache.
- No user accounts or write endpoints; the API is read-only apart from CLI-driven ingestion.

## Disclaimer

This project is for research and educational purposes. It is **not financial advice**. Data from free providers can be delayed, incomplete, or inaccurate — always verify against primary sources before making decisions.
