"""Metric registry endpoint — drives the screener's filters and columns."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MetricDefinition
from app.schemas.metric import MetricRead

router = APIRouter(tags=["metrics"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/metrics", response_model=list[MetricRead])
def list_metrics(db: DbSession, category: str | None = None) -> list[MetricRead]:
    query = select(MetricDefinition).where(MetricDefinition.active.is_(True))
    if category is not None:
        query = query.where(MetricDefinition.category == category)
    rows = db.scalars(query.order_by(MetricDefinition.category, MetricDefinition.key)).all()
    return [MetricRead.model_validate(row) for row in rows]
