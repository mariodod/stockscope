"""rename avg_volume to last_daily_volume

Revision ID: 9b2e3c4d5f60
Revises: 7c1d9e2f4a6b
Create Date: 2026-11-21

"""

from collections.abc import Sequence

from alembic import op

revision: str = "9b2e3c4d5f60"
down_revision: str | None = "7c1d9e2f4a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM fundamental_facts WHERE metric_key = 'avg_volume'")
    op.execute(
        "UPDATE metric_definitions SET key = 'last_daily_volume' WHERE key = 'avg_volume'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE metric_definitions SET key = 'avg_volume' WHERE key = 'last_daily_volume'"
    )
