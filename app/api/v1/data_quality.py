"""Data coverage and staleness report."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import select

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
    total = len(db.scalars(select(Company.id)).all())
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
        company_ids = {row[0] for row in fact_rows}
        dates = [row[1] for row in fact_rows]
        stale = sum(1 for value in dates if value < cutoff)

        quote_column = QUOTE_COLUMNS.get(definition.key)
        if quote_column is not None:
            quote_rows = db.execute(
                select(Quote.company_id, Quote.date).where(quote_column.is_not(None))
            ).all()
            company_ids |= {row[0] for row in quote_rows}
            dates += [row[1] for row in quote_rows]
            stale += sum(1 for value in quote_rows if value[1] < cutoff)

        coverage.append(
            MetricCoverage(
                key=definition.key,
                label=definition.label,
                total_companies=total,
                companies_with_value=len(company_ids),
                coverage_pct=round(100 * len(company_ids) / total, 1) if total else 0.0,
                stale_count=stale,
                latest_as_of=max(dates) if dates else None,
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
            finished_at=run.finished_at,
            rows_written=run.rows_written,
        )
        for run in runs
    ]
    return DataQualityReport(
        generated_at=datetime.now(UTC),
        stale_after_days=settings.stale_after_days,
        metrics=coverage,
        last_refreshes=refreshes,
    )
