"""drop unused audit columns

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c8
Create Date: 2026-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "companies",
    "fundamental_facts",
    "metric_definitions",
    "quotes",
    "saved_screens",
    "dividend_events",
    "filing_events",
)


def upgrade() -> None:
    for table in TABLES:
        columns = ["created_at"]
        if table == "companies":
            columns.append("updated_at")
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.drop_column(column)


def downgrade() -> None:
    for table in reversed(TABLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("(CURRENT_TIMESTAMP)"),
                    nullable=False,
                )
            )
            if table == "companies":
                batch_op.add_column(
                    sa.Column(
                        "updated_at",
                        sa.DateTime(timezone=True),
                        server_default=sa.text("(CURRENT_TIMESTAMP)"),
                        nullable=False,
                    )
                )
