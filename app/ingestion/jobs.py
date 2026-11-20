"""Idempotent ingestion jobs that write normalized provider data to the database."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact, MetricDefinition, Quote, RefreshRun
from app.providers.base import CompanySeed, Provider


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
    for seed in seeds:
        cik = seed.cik
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
        quote.price = seed.price
        quote.market_cap = seed.market_cap
        quote.pe_ratio = seed.pe_ratio
        quote.volume = seed.volume
        quote.fifty_two_week_high = seed.fifty_two_week_high
        quote.fifty_two_week_low = seed.fifty_two_week_low
        quote.source = seed.source or provider.name
        written += 1
    session.commit()
    return written


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
