from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ApiUsage(Base):
    __tablename__ = "api_usage"
    __table_args__ = (
        UniqueConstraint("provider", "date", name="uq_api_usage_provider_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(
        Date, server_default=func.current_date(), nullable=False
    )
    call_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
