"""Save and share screener configurations without user accounts."""

import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import SavedScreen
from app.schemas.screen import SavedScreenRead, ScreenState

router = APIRouter(tags=["screens"])


@router.post("/screens", response_model=SavedScreenRead, status_code=201)
def save_screen(state: ScreenState, db: DbSession) -> SavedScreenRead:
    token = secrets.token_urlsafe(16)
    saved = SavedScreen(token=token, state=state.model_dump(mode="json"))
    db.add(saved)
    db.commit()
    return SavedScreenRead(token=token, **state.model_dump())


@router.get("/screens/{token}", response_model=ScreenState)
def get_screen(token: str, db: DbSession) -> ScreenState:
    saved = db.scalar(select(SavedScreen).where(SavedScreen.token == token))
    if saved is None:
        raise HTTPException(status_code=404, detail="Unknown screen token")
    return ScreenState.model_validate(saved.state)
