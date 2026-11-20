"""Composite screening endpoint."""

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.screen import PagedCompanies, ScreenRequest
from app.services.screening import screen

router = APIRouter(tags=["screening"])


@router.post("/screen", response_model=PagedCompanies)
def run_screen(request: ScreenRequest, db: DbSession) -> PagedCompanies:
    return screen(db, request)
