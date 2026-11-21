"""Command-line entry point for ingestion jobs."""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.ingestion.jobs import (
    backfill_history,
    prune_quotes,
    refresh_dividends,
    refresh_fundamentals,
    refresh_quotes,
    sync_universe,
    track_refresh,
)
from app.models import Company
from app.providers import Provider, YFinanceProvider, build_providers

JOBS = ("universe", "quotes", "fundamentals", "history", "dividends", "prune", "all")


def _active_tickers(session: Session, limit: int | None) -> list[str]:
    query = select(Company.ticker).where(Company.is_active.is_(True))
    if limit is not None:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def run_job(
    job: str, limit: int | None = None, universe_provider: str = "sec"
) -> None:
    """Run one ingestion job and record its outcome in RefreshRun."""
    providers = build_providers()
    if job == "dividends":
        dividend_provider = YFinanceProvider()
        with SessionLocal() as session, track_refresh(
            session, "dividends", dividend_provider.name
        ) as run:
            run.rows_written = refresh_dividends(
                session, dividend_provider, _active_tickers(session, limit)
            )
        return
    if job == "prune":
        with SessionLocal() as session, track_refresh(
            session, "prune", "database"
        ) as run:
            run.rows_written = prune_quotes(session, settings.quote_retention_days)
        return
    if job == "history":
        history_provider = YFinanceProvider()
        with SessionLocal() as session, track_refresh(
            session, "history", history_provider.name
        ) as run:
            run.rows_written = backfill_history(
                session, history_provider, _active_tickers(session, limit), settings.history_years
            )
        return
    with SessionLocal() as session:
        if job in {"universe", "all"}:
            provider: Provider = providers[universe_provider]
            with track_refresh(session, "universe", provider.name) as run:
                run.rows_written = sync_universe(session, provider, limit)
        if job in {"quotes", "all"}:
            provider = providers["fmp"]
            with track_refresh(session, "quotes", provider.name) as run:
                run.rows_written = refresh_quotes(
                    session, provider, _active_tickers(session, limit)
                )
        if job in {"fundamentals", "all"}:
            provider = providers["yfinance"]
            with track_refresh(session, "fundamentals", provider.name) as run:
                run.rows_written = refresh_fundamentals(
                    session, provider, _active_tickers(session, limit)
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", choices=JOBS, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--provider",
        choices=("sec", "fmp"),
        default="sec",
        help="Universe provider (fmp requires FMP_API_KEY)",
    )
    args = parser.parse_args()
    run_job(args.job, args.limit, args.provider)


if __name__ == "__main__":
    main()
