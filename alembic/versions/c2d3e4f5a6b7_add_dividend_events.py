"""add dividend events

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dividend_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=True),
        sa.Column("amount_per_share", sa.Numeric(20, 6), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_dividend_events_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dividend_events")),
        sa.UniqueConstraint("company_id", "ex_date", "source", name="uq_dividend"),
    )
    op.create_index("ix_dividend_events_company_id", "dividend_events", ["company_id"])
    op.create_index("ix_dividend_events_ex_date", "dividend_events", ["ex_date"])


def downgrade() -> None:
    op.drop_index("ix_dividend_events_ex_date", table_name="dividend_events")
    op.drop_index("ix_dividend_events_company_id", table_name="dividend_events")
    op.drop_table("dividend_events")
