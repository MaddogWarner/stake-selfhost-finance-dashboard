from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FundamentalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    exchange: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    market_cap: int | None = None
    pe_ratio: Decimal | None = None
    fetched_at: datetime | None = None
