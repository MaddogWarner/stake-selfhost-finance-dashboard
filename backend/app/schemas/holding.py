from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.utils.tickers import normalise_exchange

_ACCEPTED_EXCHANGES = {"ASX", "NYSE", "AU", "AUS"}


def _validate_exchange(value: str) -> str:
    if value.upper().strip() not in _ACCEPTED_EXCHANGES:
        raise ValueError("exchange must be one of: ASX, NYSE")
    return normalise_exchange(value)


ExchangeField = Annotated[str, AfterValidator(_validate_exchange)]


class HoldingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    exchange: str
    quantity: Decimal
    avg_cost: Decimal | None
    source: str
    last_synced_at: datetime


class HoldingCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: ExchangeField
    quantity: Decimal = Field(gt=0)
    avg_cost: Decimal | None = Field(default=None, ge=0)


class HoldingUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    avg_cost: Decimal | None = Field(default=None, ge=0)


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    exchange: str
    source: str
    added_at: datetime


class WatchlistCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: ExchangeField
