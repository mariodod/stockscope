"""Expected or historical dividend events for a company."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.company import Company


class DividendEvent(Base):
    __tablename__ = "dividend_events"
    __table_args__ = (
        UniqueConstraint("company_id", "ex_date", "source", name="uq_dividend"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_per_share: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    company: Mapped["Company"] = relationship()
