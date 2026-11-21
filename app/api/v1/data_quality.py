"""Data coverage and staleness report."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.cache import api_cache
from app.config import settings
from app.models import Company, FundamentalFact, MetricDefinition, Quote, RefreshRun
from app.schemas.screen import DataQualityReport, MetricCoverage, RefreshSummary
from app.services.metrics import QUOTE_COLUMNS

router = APIRouter(tags=["data-quality"])


@router.get("/data-quality", response_model=DataQualityReport)
def data_quality(db: DbSession) -> DataQualityReport:
    key = f"data-quality:{settings.stale_after_days}"
    return api_cache.get_or_set(key, lambda: _build_report(db))


def _build_report(db: DbSession) -> DataQualityReport:
    total = db.scalar(select(func.count()).select_from(Company)) or 0
    cutoff = datetime.now(UTC).date() - timedelta(days=settings.stale_after_days)

    coverage: list[MetricCoverage] = []
    definitions = db.scalars(
        select(MetricDefinition).order_by(MetricDefinition.key)
    ).all()
    for definition in definitions:
        fact_rows = db.execute(
            select(FundamentalFact.company_id, FundamentalFact.as_of_date).where(
                FundamentalFact.metric_key == definition.key
            )
        ).all()
        latest_dates: dict[int, date] = {}
        for company_id, as_of in fact_rows:
            latest_dates[company_id] = max(latest_dates.get(company_id, as_of), as_of)

        quote_column = QUOTE_COLUMNS.get(definition.key)
        if quote_column is not None:
            quote_rows = db.execute(
                select(Quote.company_id, Quote.date).where(quote_column.is_not(None))
            ).all()
            for company_id, day in quote_rows:
                latest_dates[company_id] = max(latest_dates.get(company_id, day), day)

        stale = sum(1 for day in latest_dates.values() if day < cutoff)
        coverage.append(
            MetricCoverage(
                key=definition.key,
                label=definition.label,
                total_companies=total,
                companies_with_value=len(latest_dates),
                coverage_pct=round(100 * len(latest_dates) / total, 1) if total else 0.0,
                stale_count=stale,
                latest_as_of=max(latest_dates.values()) if latest_dates else None,
            )
        )

    runs = db.execute(
        select(RefreshRun)
        .order_by(RefreshRun.id.desc())
        .limit(10)
    ).scalars().all()
    refreshes = [
        RefreshSummary(
            job=run.job,
            provider=run.provider,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            rows_written=run.rows_written,
            error=run.error,
        )
        for run in runs
    ]
    return DataQualityReport(
        generated_at=datetime.now(UTC),
        stale_after_days=settings.stale_after_days,
        metrics=coverage,
        last_refreshes=refreshes,
    )
