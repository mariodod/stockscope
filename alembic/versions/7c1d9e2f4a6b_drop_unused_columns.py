"""drop unused columns

Revision ID: 7c1d9e2f4a6b
Revises: 87e0cf895737
Create Date: 2026-11-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c1d9e2f4a6b"
down_revision: str | None = "87e0cf895737"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.drop_column("listed_at")
    with op.batch_alter_table("fundamental_facts", schema=None) as batch_op:
        batch_op.drop_column("fiscal_year")
        batch_op.drop_column("notes")


def downgrade() -> None:
    with op.batch_alter_table("fundamental_facts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("fiscal_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("listed_at", sa.Date(), nullable=True))
