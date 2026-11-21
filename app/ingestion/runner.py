"""Command-line entry point for ingestion jobs."""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.ingestion.jobs import (
    prune_quotes,
    refresh_fundamentals,
    refresh_quotes,
    sync_universe,
    track_refresh,
)
from app.models import Company
from app.providers import Provider, build_providers

JOBS = ("universe", "quotes", "fundamentals", "prune", "all")


def _active_tickers(session: Session, limit: int | None) -> list[str]:
    query = select(Company.ticker).where(Company.is_active.is_(True))
    if limit is not None:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def run_job(job: str, limit: int | None = None) -> None:
    """Run one ingestion job and record its outcome in RefreshRun."""
    providers = build_providers()
    if job == "prune":
        with SessionLocal() as session, track_refresh(
            session, "prune", "database"
        ) as run:
            run.rows_written = prune_quotes(session, settings.quote_retention_days)
        return
    with SessionLocal() as session:
        if job in {"universe", "all"}:
            provider: Provider = providers["sec"]
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
    args = parser.parse_args()
    run_job(args.job, args.limit)


if __name__ == "__main__":
    main()
