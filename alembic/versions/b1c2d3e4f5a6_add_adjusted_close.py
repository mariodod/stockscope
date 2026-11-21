"""add adjusted close to quotes

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-11-21

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("quotes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("adjusted_close", sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("quotes", schema=None) as batch_op:
        batch_op.drop_column("adjusted_close")
