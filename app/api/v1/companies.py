"""Company list, detail and sector endpoints."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession
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
    fact_history,
    latest_fact_rows,
    latest_quote_row,
    metric_labels,
)
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
    try:
        return screen(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{ticker}", response_model=CompanyDetail)
def get_company(ticker: str, db: DbSession) -> CompanyDetail:
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")

    labels = metric_labels(db)
    latest: list[LatestMetric] = []
    for row in latest_fact_rows(db, company.id):
        key = row["metric_key"]
        label, unit, direction = labels.get(key, (key, row["unit"], None))
        latest.append(
            LatestMetric(
                metric_key=key,
                label=label,
                value=row["value"],
                unit=unit,
                direction=direction,
                period=row["period"],
                source=row["source"],
                as_of_date=row["as_of_date"],
            )
        )

    quote = latest_quote_row(db, company.id)
    if quote is not None:
        for key in ("market_cap", "pe_ratio", "price", "fifty_two_week_high", "fifty_two_week_low"):
            if quote.get(key) is None:
                continue
            label, unit, direction = labels.get(key, (key, "currency", None))
            item = LatestMetric(
                metric_key=key,
                label=label,
                value=quote[key],
                unit=unit,
                direction=direction,
                period="Latest",
                source=quote["source"],
                as_of_date=quote["as_of_date"],
            )
            existing_index = next(
                (index for index, metric in enumerate(latest) if metric.metric_key == key),
                None,
            )
            if existing_index is None:
                latest.append(item)
            else:
                latest[existing_index] = item

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
        latest_metrics=latest,
        history=history,
    )


@router.get("/sectors", response_model=SectorCounts)
def list_sectors(db: DbSession) -> SectorCounts:
    sectors = db.scalars(
        select(Company.sector).where(Company.sector.is_not(None)).distinct().order_by(Company.sector)
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
