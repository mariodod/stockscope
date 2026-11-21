"""Company list, detail and sector endpoints."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.cache import api_cache
from app.models import Company
from app.schemas.screen import (
    CompanyDetail,
    FactPoint,
    FilterCondition,
    FilterOp,
    LatestMetric,
    PagedCompanies,
    ScreenRequest,
    SectorCounts,
    SortDirection,
    SortSpec,
)
from app.services.metrics import (
    QUOTE_KEYS,
    fact_history,
    latest_fact_rows,
    latest_quote_row,
    metric_labels,
)
from app.services.peers import find_peers
from app.services.screening import screen

router = APIRouter(tags=["companies"])


@router.get("/companies", response_model=PagedCompanies)
def list_companies(
    db: DbSession,
    sector: str | None = None,
    exchange: str | None = None,
    sort: str = "market_cap",
    dir: SortDirection = SortDirection.DESC,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PagedCompanies:
    filters: list[FilterCondition] = []
    if sector is not None:
        filters.append(FilterCondition(metric="sector", op=FilterOp.EQ, value=sector))
    if exchange is not None:
        filters.append(FilterCondition(metric="exchange", op=FilterOp.EQ, value=exchange))
    request = ScreenRequest(
        filters=filters,
        sort=[SortSpec(metric=sort, dir=dir)],
        limit=limit,
        offset=offset,
    )
    return screen(db, request)


@router.get("/companies/{ticker}", response_model=CompanyDetail)
def get_company(ticker: str, db: DbSession) -> CompanyDetail:
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    labels = metric_labels(db)
    latest: dict[str, LatestMetric] = {}
    for row in latest_fact_rows(db, company.id):
        key = row["metric_key"]
        label, unit, direction = labels.get(key, (key, row["unit"], None))
        latest[key] = LatestMetric(
            metric_key=key,
            label=label,
            value=row["value"],
            unit=unit,
            direction=direction,
            period=row["period"],
            source=row["source"],
            as_of_date=row["as_of_date"],
        )

    quote = latest_quote_row(db, company.id)
    if quote is not None:
        for key in QUOTE_KEYS:
            if quote.get(key) is None:
                continue
            label, unit, direction = labels.get(key, (key, "currency", None))
            latest[key] = LatestMetric(
                metric_key=key,
                label=label,
                value=quote[key],
                unit=unit,
                direction=direction,
                period="Latest",
                source=quote["source"],
                as_of_date=quote["as_of_date"],
            )

    history = [FactPoint(**row) for row in fact_history(db, company.id)]
    return CompanyDetail(
        ticker=company.ticker,
        name=company.name,
        cik=company.cik,
        exchange=company.exchange,
        sector=company.sector,
        industry=company.industry,
        country=company.country,
        currency=company.currency,
        latest_metrics=list(latest.values()),
        history=history,
    )


@router.get("/companies/{ticker}/peers", response_model=PagedCompanies)
def get_peers(
    ticker: str,
    db: DbSession,
    limit: int = Query(default=5, ge=1, le=20),
) -> PagedCompanies:
    return find_peers(db, ticker, limit)


@router.get("/sectors", response_model=SectorCounts)
def list_sectors(db: DbSession) -> SectorCounts:
    def load() -> SectorCounts:
        sectors = db.scalars(
            select(Company.sector)
            .where(Company.sector.is_not(None))
            .distinct()
            .order_by(Company.sector)
        ).all()
        industries = db.scalars(
            select(Company.industry)
            .where(Company.industry.is_not(None))
            .distinct()
            .order_by(Company.industry)
        ).all()
        return SectorCounts(
            sectors=[value for value in sectors if value],
            industries=[value for value in industries if value],
        )

    return api_cache.get_or_set("sectors", load)
