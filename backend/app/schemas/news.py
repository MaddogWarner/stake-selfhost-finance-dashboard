from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    headline: str
    source: str | None = None
    url: str | None = None
    published_at: datetime | None = None
