from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("ticker", "exchange", name="uq_watchlist_ticker_exchange"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
