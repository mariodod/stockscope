"""Upcoming dividend events."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Company, DividendEvent
from app.schemas.dividend import DividendRead

router = APIRouter(tags=["dividends"])

Days = Annotated[int, Query(ge=1, le=365)]
Tickers = Annotated[list[str] | None, Query()]


@router.get("/dividends", response_model=list[DividendRead])
def list_dividends(db: DbSession, days: Days = 90, tickers: Tickers = None) -> list[DividendRead]:
    today = date.today()
    deadline = today + timedelta(days=days)
    query = (
        select(DividendEvent, Company)
        .join(Company, Company.id == DividendEvent.company_id)
        .where(DividendEvent.ex_date >= today, DividendEvent.ex_date <= deadline)
        .order_by(DividendEvent.ex_date, Company.ticker)
    )
    if tickers:
        query = query.where(Company.ticker.in_([ticker.upper() for ticker in tickers]))
    return [
        DividendRead(
            ticker=company.ticker,
            company_name=company.name,
            ex_date=event.ex_date,
            pay_date=event.pay_date,
            amount_per_share=float(event.amount_per_share)
            if event.amount_per_share is not None
            else None,
            source=event.source,
        )
        for event, company in db.execute(query).all()
    ]
