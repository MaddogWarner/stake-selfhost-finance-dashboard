from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HoldingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    exchange: str
    quantity: Decimal
    avg_cost: Decimal | None
    last_synced_at: datetime


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    exchange: str
    added_at: datetime
