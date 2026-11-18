"""Data-integrity constraints on the core models."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Company, FundamentalFact
from app.seed.metrics import seed_metrics


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
