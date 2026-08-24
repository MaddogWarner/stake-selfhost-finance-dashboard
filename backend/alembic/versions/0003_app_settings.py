"""add app_settings table

Revision ID: 0003_app_settings
Revises: 0002_news_unique_ticker_url
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_app_settings"
down_revision: str | None = "0002_news_unique_ticker_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("INSERT INTO app_settings (key, value) VALUES ('data_source', 'both')")


def downgrade() -> None:
    op.drop_table("app_settings")
