"""Ingestion jobs are idempotent and record their outcomes."""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.jobs import (
    prune_quotes,
    refresh_fundamentals,
    refresh_quotes,
    sync_universe,
    track_refresh,
)
from app.models import Company, FundamentalFact, Quote, RefreshRun
from app.providers.base import CompanySeed, FactSeed, QuoteSeed
from app.seed.metrics import seed_metrics


class FakeProvider:
    name = "fake"

    def __init__(self, count: int = 5000) -> None:
        self.count = count

    def list_companies(self) -> Iterator[CompanySeed]:
        for index in range(self.count):
            yield CompanySeed(ticker=f"S{index:05d}", name=f"Company {index}", cik=str(index))

    def get_quote(self, ticker: str) -> QuoteSeed:
        return QuoteSeed(
            date=date(2026, 1, 2),
            price=Decimal("10"),
            market_cap=Decimal("1000000000"),
            pe_ratio=Decimal("15"),
            source=self.name,
        )

    def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
        yield FactSeed(
            metric_key="pe_ratio",
            period="TTM",
            value=Decimal("15"),
            unit="ratio",
            as_of_date=date(2026, 1, 2),
            source=self.name,
        )
        yield FactSeed(
            metric_key="not_in_catalog",
            period="TTM",
            value=Decimal("1"),
            unit="ratio",
            as_of_date=date(2026, 1, 2),
            source=self.name,
        )


def test_universe_sync_is_idempotent(db_session: Session) -> None:
    provider = FakeProvider(count=5000)

    assert sync_universe(db_session, provider) == 5000
    assert db_session.scalar(select(func.count()).select_from(Company)) == 5000

    assert sync_universe(db_session, provider) == 5000
    assert db_session.scalar(select(func.count()).select_from(Company)) == 5000


def test_quote_and_fact_refresh_are_idempotent(db_session: Session) -> None:
    seed_metrics(db_session)
    provider = FakeProvider()
    sync_universe(db_session, provider, limit=20)
    tickers = [f"S{index:05d}" for index in range(20)]

    for _ in range(2):
        assert refresh_quotes(db_session, provider, tickers) == 20
        assert refresh_fundamentals(db_session, provider, tickers) == 20

    assert db_session.scalar(select(func.count()).select_from(Quote)) == 20
    assert db_session.scalar(select(func.count()).select_from(FundamentalFact)) == 20
    assert db_session.scalar(select(func.count()).select_from(RefreshRun)) == 0


def test_track_refresh_records_success_and_failure(db_session: Session) -> None:
    with track_refresh(db_session, "universe", "fake") as run:
        run.rows_written = 3

    assert run.status == "succeeded"
    assert run.rows_written == 3

    with pytest.raises(ValueError, match="boom"), track_refresh(
        db_session, "quotes", "fake"
    ) as failed:
        raise ValueError("boom")

    assert failed.status == "failed"
    assert "boom" in (failed.error or "")
    assert db_session.scalar(select(func.count()).select_from(RefreshRun)) == 2


def test_shared_ciks_do_not_break_universe_sync(db_session: Session) -> None:
    class SharedCikProvider(FakeProvider):
        def list_companies(self) -> Iterator[CompanySeed]:
            yield CompanySeed(ticker="GOOGL", name="Alphabet A", cik="1652044")
            yield CompanySeed(ticker="GOOG", name="Alphabet C", cik="1652044")

    provider = SharedCikProvider()
    sync_universe(db_session, provider)
    sync_universe(db_session, provider)

    rows = dict(db_session.execute(select(Company.ticker, Company.cik)).all())
    assert rows == {"GOOGL": "1652044", "GOOG": None}


def test_cik_holder_delisting_does_not_break_sync(db_session: Session) -> None:
    class Feed(FakeProvider):
        def __init__(self, tickers: list[str]) -> None:
            self.tickers = tickers

        def list_companies(self) -> Iterator[CompanySeed]:
            for ticker in self.tickers:
                yield CompanySeed(ticker=ticker, name=ticker, cik="1652044")

    sync_universe(db_session, Feed(["GOOGL", "GOOG"]))
    sync_universe(db_session, Feed(["GOOG"]))

    rows = dict(db_session.execute(select(Company.ticker, Company.cik)).all())
    assert rows == {"GOOGL": None, "GOOG": "1652044"}


def test_track_refresh_records_database_failures(db_session: Session) -> None:
    with pytest.raises(IntegrityError), track_refresh(db_session, "universe", "fake"):
        db_session.add(Company(ticker="DUP", name="First"))
        db_session.commit()
        db_session.add(Company(ticker="DUP", name="Second"))
        db_session.commit()

    failed = db_session.scalars(select(RefreshRun)).one()
    assert failed.status == "failed"
    assert "UNIQUE" in (failed.error or "").upper()


def test_history_backfill_is_idempotent_and_preserves_metrics(db_session: Session) -> None:
    from app.ingestion.jobs import backfill_history
    from app.providers.base import HistoricalPriceSeed

    sync_universe(db_session, FakeProvider(), limit=1)

    class HistoryProvider(FakeProvider):
        def get_price_history(self, ticker: str, years: int = 5) -> Iterator[HistoricalPriceSeed]:
            yield HistoricalPriceSeed(
                date=date(2025, 1, 2),
                close=Decimal("100"),
                adjusted_close=Decimal("98"),
                volume=500,
            )

    db_session.add(
        Quote(
            company_id=db_session.scalar(select(Company.id)),
            date=date(2025, 1, 2),
            market_cap=Decimal("1000000"),
            source="fmp",
        )
    )
    db_session.commit()

    provider = HistoryProvider()
    assert backfill_history(db_session, provider, ["S00000"], 5) == 1
    assert backfill_history(db_session, provider, ["S00000"], 5) == 1

    quote = db_session.scalar(select(Quote))
    assert quote.adjusted_close == Decimal("98")
    assert quote.market_cap == Decimal("1000000")
    assert db_session.scalar(select(func.count()).select_from(Quote)) == 1


def test_prune_quotes_removes_only_old_rows(db_session: Session) -> None:
    seed_metrics(db_session)
    company = Company(ticker="PRUNE", name="Prune")
    db_session.add(company)
    db_session.flush()
    db_session.add(
        Quote(
            company_id=company.id,
            date=date.today() - timedelta(days=1000),
            source="old",
        )
    )
    db_session.add(Quote(company_id=company.id, date=date.today(), source="new"))
    db_session.commit()

    assert prune_quotes(db_session, 500) == 1
    assert [row[0] for row in db_session.execute(select(Quote.source)).all()] == ["new"]


def test_facts_without_source_upsert_idempotently(db_session: Session) -> None:
    seed_metrics(db_session)
    sync_universe(db_session, FakeProvider(), limit=1)

    class NoSourceProvider(FakeProvider):
        def get_fundamentals(self, ticker: str, cik: str | None = None) -> Iterator[FactSeed]:
            yield FactSeed(
                metric_key="pe_ratio",
                period="TTM",
                value=Decimal("15"),
                unit="ratio",
                as_of_date=date(2026, 1, 2),
            )

    provider = NoSourceProvider()
    assert refresh_fundamentals(db_session, provider, ["S00000"]) == 1
    assert refresh_fundamentals(db_session, provider, ["S00000"]) == 1
    assert db_session.scalar(select(func.count()).select_from(FundamentalFact)) == 1


def test_unknown_metric_keys_are_skipped(db_session: Session) -> None:
    seed_metrics(db_session)
    provider = FakeProvider()
    sync_universe(db_session, provider, limit=1)

    assert refresh_fundamentals(db_session, provider, ["S00000"]) == 1
    keys = set(db_session.scalars(select(FundamentalFact.metric_key)).all())
    assert keys == {"pe_ratio"}
