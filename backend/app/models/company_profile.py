from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
