"""Composite screening endpoint."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.deps import DbSession
from app.schemas.screen import PagedCompanies, ScreenRequest
from app.services.export import MAX_EXPORT_ROWS, screen_to_csv
from app.services.screening import screen

router = APIRouter(tags=["screening"])


@router.post("/screen", response_model=PagedCompanies)
def run_screen(request: ScreenRequest, db: DbSession) -> PagedCompanies:
    return screen(db, request)


@router.post("/screen/export")
def export_screen(request: ScreenRequest, db: DbSession) -> Response:
    """Export the full filtered screen as CSV, capped at MAX_EXPORT_ROWS."""
    export_request = request.model_copy(update={"limit": MAX_EXPORT_ROWS, "offset": 0})
    result = screen(db, export_request)
    return Response(
        content=screen_to_csv(result, export_request),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stockscope-screen.csv"'},
    )
