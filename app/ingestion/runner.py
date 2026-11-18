"""Command-line entry point for ingestion jobs."""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.ingestion.jobs import refresh_fundamentals, refresh_quotes, sync_universe, track_refresh
from app.models import Company
from app.providers import FMPProvider, Provider, SECProvider, YFinanceProvider

JOBS = ("universe", "quotes", "fundamentals", "all")


def _active_tickers(session: Session, limit: int | None) -> list[str]:
    query = select(Company.ticker).where(Company.is_active.is_(True))
    if limit is not None:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def run_job(job: str, limit: int | None = None) -> None:
    """Run one ingestion job and record its outcome in RefreshRun."""
    with SessionLocal() as session:
        if job in {"universe", "all"}:
            provider: Provider = SECProvider()
            with track_refresh(session, "universe", provider.name) as run:
                run.rows_written = sync_universe(session, provider, limit)
        if job in {"quotes", "all"}:
            provider = FMPProvider(api_key=settings.fmp_api_key)
            with track_refresh(session, "quotes", provider.name) as run:
                run.rows_written = refresh_quotes(
                    session, provider, _active_tickers(session, limit)
                )
        if job in {"fundamentals", "all"}:
            provider = YFinanceProvider()
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
