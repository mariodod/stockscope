"""Recent SEC filings for alerting."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Company, FilingEvent
from app.schemas.filing import FilingRead

router = APIRouter(tags=["filings"])

Days = Annotated[int, Query(ge=1, le=365)]
Tickers = Annotated[list[str] | None, Query()]


@router.get("/filings", response_model=list[FilingRead])
def list_filings(db: DbSession, days: Days = 30, tickers: Tickers = None) -> list[FilingRead]:
    start = date.today() - timedelta(days=days)
    query = (
        select(FilingEvent, Company)
        .join(Company, Company.id == FilingEvent.company_id)
        .where(FilingEvent.filing_date >= start)
        .order_by(FilingEvent.filing_date.desc(), Company.ticker)
    )
    if tickers:
        query = query.where(Company.ticker.in_([ticker.upper() for ticker in tickers]))
    return [
        FilingRead(
            ticker=company.ticker,
            company_name=company.name,
            accession_number=event.accession_number,
            form=event.form,
            filing_date=event.filing_date,
            primary_document=event.primary_document,
        )
        for event, company in db.execute(query).all()
    ]
