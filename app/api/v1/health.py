"""Service health endpoint."""

from fastapi import APIRouter

from app import __version__
from app.schemas.health import HealthRead

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthRead)
def health() -> HealthRead:
    return HealthRead(status="ok", version=__version__)
