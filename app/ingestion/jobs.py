"""Idempotent ingestion jobs that write normalized provider data to the database."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.models import (
    Company,
    DividendEvent,
    FilingEvent,
    FundamentalFact,
    MetricDefinition,
    Quote,
    RefreshRun,
)
from app.providers.base import (
    CompanySeed,
    DividendProvider,
    FilingProvider,
    PriceHistoryProvider,
    Provider,
)


@contextmanager
def track_refresh(session: Session, job: str, provider: str) -> Iterator[RefreshRun]:
    """Record one ingestion run, including failures, as a RefreshRun row."""
    run = RefreshRun(job=job, provider=provider, status="running")
    session.add(run)
    session.commit()
    run_id = run.id
    try:
        yield run
    except Exception as exc:
        session.rollback()
        failed_run = session.get(RefreshRun, run_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.finished_at = datetime.now(UTC)
            failed_run.error = str(exc)[:2000]
            session.commit()
        raise
    else:
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        session.commit()


def _companies(session: Session) -> dict[str, Company]:
    return {company.ticker: company for company in session.scalars(select(Company)).all()}


def sync_universe(session: Session, provider: Provider, limit: int | None = None) -> int:
    """Insert or update companies from the provider's listed universe."""
    existing = _companies(session)
    seeds: list[CompanySeed] = []
    for seed in provider.list_companies():
        if limit is not None and len(seeds) >= limit:
            break
        seeds.append(seed)

    # SEC lists share classes (GOOG/GOOGL) under one CIK. Assign each CIK to one ticker,
    # then clear stale holders before writing so a delisted class cannot block the new one.
    assignments: dict[str, str | None] = {}
    claimed: dict[str, str] = {}
    seeded_tickers = {seed.ticker for seed in seeds}
    reserved = (
        {
            company.cik: ticker
            for ticker, company in existing.items()
            if company.cik is not None and ticker not in seeded_tickers
        }
        if limit is not None
        else {}
    )
    for seed in seeds:
        cik = seed.cik
        if cik is not None and cik in reserved and reserved[cik] != seed.ticker:
            cik = None
        if cik is not None:
            if cik in claimed and claimed[cik] != seed.ticker:
                cik = None
            else:
                claimed[cik] = seed.ticker
        assignments[seed.ticker] = cik

    for ticker, stale_company in existing.items():
        cik = stale_company.cik
        if cik is None or claimed.get(cik) == ticker:
            continue
        if assignments.get(ticker) != cik and cik in claimed:
            stale_company.cik = None
    session.flush()

    for seed in seeds:
        company = existing.get(seed.ticker)
        if company is None:
            company = Company(ticker=seed.ticker, name=seed.name)
            session.add(company)
            existing[seed.ticker] = company
        else:
            company.name = seed.name
        company.cik = assignments[seed.ticker]
        company.exchange = seed.exchange
        company.sector = seed.sector
        company.industry = seed.industry
        company.country = seed.country
        company.currency = seed.currency
    session.commit()
    return len(seeds)


def refresh_quotes(
    session: Session, provider: Provider, tickers: list[str], as_of: date | None = None
) -> int:
    """Upsert one quote per company and date."""
    quote_date = as_of or date.today()
    companies = _companies(session)
    existing = {
        (quote.company_id, quote.date): quote for quote in session.scalars(select(Quote)).all()
    }
    written = 0
    for ticker in tickers:
        company = companies.get(ticker)
        if company is None:
            continue
        seed = provider.get_quote(ticker)
        if seed is None:
            continue
        day = seed.date or quote_date
        key = (company.id, day)
        quote = existing.get(key)
        if quote is None:
            quote = Quote(company_id=company.id, date=day, source=seed.source or provider.name)
            session.add(quote)
            existing[key] = quote
        for field, value in (
            ("price", seed.price),
            ("market_cap", seed.market_cap),
            ("pe_ratio", seed.pe_ratio),
            ("volume", seed.volume),
            ("fifty_two_week_high", seed.fifty_two_week_high),
            ("fifty_two_week_low", seed.fifty_two_week_low),
        ):
            if value is not None:
                setattr(quote, field, value)
        quote.source = seed.source or provider.name
        written += 1
    session.commit()
    return written


def refresh_filings(session: Session, provider: FilingProvider, tickers: list[str]) -> int:
    """Upsert SEC filings by company and accession number."""
    companies = _companies(session)
    existing = {
        (event.company_id, event.accession_number): event
        for event in session.scalars(select(FilingEvent)).all()
    }
    written = 0
    for ticker in tickers:
        company = companies.get(ticker)
        if company is None:
            continue
        for seed in provider.get_recent_filings(company.cik):
            key = (company.id, seed.accession_number)
            event = existing.get(key)
            if event is None:
                event = FilingEvent(
                    company_id=company.id,
                    accession_number=seed.accession_number,
                    source=seed.source or provider.name,
                )
                session.add(event)
                existing[key] = event
            event.form = seed.form
            event.filing_date = seed.filing_date
            event.primary_document = seed.primary_document
            written += 1
    session.commit()
    return written


def refresh_dividends(
    session: Session, provider: DividendProvider, tickers: list[str]
) -> int:
    """Upsert expected dividend events by company, ex-date and source."""
    companies = _companies(session)
    existing = {
        (event.company_id, event.ex_date, event.source): event
        for event in session.scalars(select(DividendEvent)).all()
    }
    written = 0
    for ticker in tickers:
        company = companies.get(ticker)
        if company is None:
            continue
        for seed in provider.get_dividends(ticker):
            source = seed.source or provider.name
            key = (company.id, seed.ex_date, source)
            event = existing.get(key)
            if event is None:
                event = DividendEvent(
                    company_id=company.id, ex_date=seed.ex_date, source=source
                )
                session.add(event)
                existing[key] = event
            event.pay_date = seed.pay_date
            event.amount_per_share = seed.amount_per_share
            written += 1
    session.commit()
    return written


def backfill_history(
    session: Session, provider: PriceHistoryProvider, tickers: list[str], years: int = 5
) -> int:
    """Upsert daily close and adjusted-close history without losing quote metrics."""
    companies = _companies(session)
    existing = {
        (quote.company_id, quote.date): quote for quote in session.scalars(select(Quote)).all()
    }
    written = 0
    for ticker in tickers:
        company = companies.get(ticker)
        if company is None:
            continue
        for seed in provider.get_price_history(ticker, years):
            key = (company.id, seed.date)
            quote = existing.get(key)
            if quote is None:
                quote = Quote(
                    company_id=company.id,
                    date=seed.date,
                    source=seed.source or provider.name,
                )
                session.add(quote)
                existing[key] = quote
            if seed.close is not None:
                quote.price = seed.close
            if seed.adjusted_close is not None:
                quote.adjusted_close = seed.adjusted_close
            if seed.volume is not None:
                quote.volume = seed.volume
            written += 1
    session.commit()
    return written


def prune_quotes(session: Session, older_than_days: int) -> int:
    """Delete quotes older than the retention window. Returns rows removed."""
    cutoff = date.today() - timedelta(days=older_than_days)
    result = session.execute(delete(Quote).where(Quote.date < cutoff))
    deleted = result.rowcount if isinstance(result, CursorResult) else 0
    session.commit()
    return deleted


def refresh_fundamentals(session: Session, provider: Provider, tickers: list[str]) -> int:
    """Upsert facts on (company, metric, period, source); skip unknown metric keys."""
    valid_keys = set(session.scalars(select(MetricDefinition.key)).all())
    companies = _companies(session)
    existing = {
        (fact.company_id, fact.metric_key, fact.period, fact.source): fact
        for fact in session.scalars(select(FundamentalFact)).all()
    }
    written = 0
    for ticker in tickers:
        company = companies.get(ticker)
        if company is None:
            continue
        for seed in provider.get_fundamentals(ticker, company.cik):
            if seed.metric_key not in valid_keys:
                continue
            source = seed.source or provider.name
            key = (company.id, seed.metric_key, seed.period, source)
            fact = existing.get(key)
            if fact is None:
                fact = FundamentalFact(
                    company_id=company.id,
                    metric_key=seed.metric_key,
                    period=seed.period,
                    source=source,
                )
                session.add(fact)
                existing[key] = fact
            fact.value = seed.value
            fact.unit = seed.unit
            fact.as_of_date = seed.as_of_date
            fact.filed_at = seed.filed_at
            written += 1
    session.commit()
    return written
