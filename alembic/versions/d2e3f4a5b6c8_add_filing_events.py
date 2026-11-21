"""add filing events

Revision ID: d2e3f4a5b6c8
Revises: c2d3e4f5a6b7
Create Date: 2026-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "filing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("form", sa.String(length=16), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("primary_document", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_filing_events_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_filing_events")),
        sa.UniqueConstraint("company_id", "accession_number", name="uq_filing"),
    )
    op.create_index("ix_filing_events_company_id", "filing_events", ["company_id"])
    op.create_index("ix_filing_events_filing_date", "filing_events", ["filing_date"])


def downgrade() -> None:
    op.drop_index("ix_filing_events_filing_date", table_name="filing_events")
    op.drop_index("ix_filing_events_company_id", table_name="filing_events")
    op.drop_table("filing_events")
