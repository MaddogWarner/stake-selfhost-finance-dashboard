"""add news ticker url unique constraint

Revision ID: 0002_news_unique_ticker_url
Revises: 0001_initial
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_news_unique_ticker_url"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_news_ticker_url", "news", ["ticker", "url"])


def downgrade() -> None:
    op.drop_constraint("uq_news_ticker_url", "news", type_="unique")
