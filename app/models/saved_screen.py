"""A stored screener configuration, addressable by an unguessable token."""

from typing import Any

from sqlalchemy import JSON, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SavedScreen(Base):
    __tablename__ = "saved_screens"
    __table_args__ = (Index("ix_saved_screens_token", "token", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
