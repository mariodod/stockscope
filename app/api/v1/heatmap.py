"""Sector heatmap data."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.heatmap import SectorPerformance
from app.services.heatmap import sector_performance

router = APIRouter(tags=["heatmap"])

Days = Annotated[int, Query(ge=1, le=3650)]


@router.get("/sector-performance", response_model=list[SectorPerformance])
def get_sector_performance(db: DbSession, days: Days = 90) -> list[SectorPerformance]:
    return sector_performance(db, days)
