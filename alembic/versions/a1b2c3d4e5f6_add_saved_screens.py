"""add saved screens

Revision ID: a1b2c3d4e5f6
Revises: 9b2e3c4d5f60
Create Date: 2026-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9b2e3c4d5f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_screens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_screens")),
    )
    op.create_index(
        op.f("ix_saved_screens_token"), "saved_screens", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_screens_token"), table_name="saved_screens")
    op.drop_table("saved_screens")
