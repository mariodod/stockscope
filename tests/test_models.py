"""Data-integrity constraints on the core models."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Company, FundamentalFact
from app.seed.metrics import seed_metrics


def test_models_have_no_unused_audit_columns() -> None:
    for table in Base.metadata.sorted_tables:
        assert "created_at" not in table.columns, table.name
        assert "updated_at" not in table.columns, table.name


def test_company_ticker_is_unique(db_session: Session) -> None:
    db_session.add_all(
        [
            Company(ticker="AAPL", name="Apple Inc."),
            Company(ticker="AAPL", name="Duplicate Inc."),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_fact_is_unique_per_company_metric_period_source(db_session: Session) -> None:
    seed_metrics(db_session)
    company = Company(ticker="MSFT", name="Microsoft Corp.")
    db_session.add(company)
    db_session.flush()

    values = {
        "company_id": company.id,
        "metric_key": "pe_ratio",
        "period": "TTM",
        "unit": "ratio",
        "source": "fmp",
        "as_of_date": date(2026, 11, 18),
        "value": Decimal("35.5"),
    }
    db_session.add_all([FundamentalFact(**values), FundamentalFact(**values)])

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_orphan_fact_is_rejected(db_session: Session) -> None:
    db_session.add(
        FundamentalFact(
            company_id=999999,
            metric_key="NO_SUCH_METRIC",
            period="TTM",
            unit="ratio",
            source="fmp",
            as_of_date=date(2026, 11, 18),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_company_cascades_at_database_level(db_session: Session) -> None:
    seed_metrics(db_session)
    company = Company(ticker="TSLA", name="Tesla Inc.")
    db_session.add(company)
    db_session.flush()
    db_session.add(
        FundamentalFact(
            company_id=company.id,
            metric_key="pe_ratio",
            period="TTM",
            unit="ratio",
            source="fmp",
            as_of_date=date(2026, 11, 18),
        )
    )
    db_session.commit()

    db_session.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company.id})
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(FundamentalFact)) == 0
