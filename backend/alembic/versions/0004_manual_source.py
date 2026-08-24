"""add source column to holdings and watchlist

Revision ID: 0004_manual_source
Revises: 0003_app_settings
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_manual_source"
down_revision: str | None = "0003_app_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "holdings",
        sa.Column("source", sa.String(10), server_default="manual", nullable=False),
    )
    op.add_column(
        "watchlist",
        sa.Column("source", sa.String(10), server_default="manual", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("watchlist", "source")
    op.drop_column("holdings", "source")
