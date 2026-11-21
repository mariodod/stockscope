"""Registry of canonical metric keys used across ingestion, API, and UI."""

from enum import StrEnum

from sqlalchemy import Boolean, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetricDirection(StrEnum):
    HIGH = "high"
    LOW = "low"
    NEUTRAL = "neutral"
    NONE = "none"


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[MetricDirection] = mapped_column(
        SAEnum(MetricDirection, name="metric_direction", native_enum=False),
        nullable=False,
        default=MetricDirection.NONE,
    )
    formula: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
