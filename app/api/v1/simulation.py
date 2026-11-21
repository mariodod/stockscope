"""Returns simulation endpoint."""

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.simulation import SimulationRequest, SimulationResult
from app.services.simulation import simulate

router = APIRouter(tags=["simulation"])


@router.post("/simulate", response_model=SimulationResult)
def run_simulation(request: SimulationRequest, db: DbSession) -> SimulationResult:
    return simulate(db, request)
