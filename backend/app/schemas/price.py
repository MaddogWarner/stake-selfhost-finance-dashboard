from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PricePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None


class QuoteRead(BaseModel):
    ticker: str
    exchange: str
    price: float | None = None
    prev_close: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    currency: str | None = None
    history: list[PricePoint] = []
