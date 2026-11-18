# Stockscope

A stock screening and analysis platform for publicly listed companies. It pulls fundamentals and quotes from free data providers, stores them in a local database, and exposes them through a fast, filterable web dashboard.

> **Status: planning.** The roadmap lives in [PLAN.md](PLAN.md). Design decisions and reference material live in [docs/](docs/). Tracked work is in the [GitHub milestones and issues](../../issues) once the remote is created.

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

## Planned first version (v1) scope

- ~5,000–8,000 US-listed companies.
- Daily refresh of quotes; fundamentals refreshed on provider cadence (quarterly/annual filings).
- Market cap, valuation, profitability, growth, leverage, and liquidity metrics (see [metrics catalog](docs/metrics.md)).
- Screener with multi-filter, multi-sort, and a weighted composite rank.
- Company detail page with a fundamentals timeline.
- Local Docker Compose setup for the database.

## Quick start (available after milestone M1)

```bash
cp .env.example .env
# add your data-provider API keys to .env
docker compose up -d          # database
uvicorn app.main:app --reload # API at http://localhost:8000/docs
npm install --prefix frontend
npm run dev --prefix frontend # dashboard at http://localhost:5173
```

## Disclaimer

This project is for research and educational purposes. It is **not financial advice**. Data from free providers can be delayed, incomplete, or inaccurate — always verify against primary sources before making decisions.
