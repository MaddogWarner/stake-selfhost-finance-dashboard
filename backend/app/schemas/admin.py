from pydantic import BaseModel


class ProviderUsage(BaseModel):
    today: int
    limit: int
    remaining: int


class ApiUsageRead(BaseModel):
    fmp: ProviderUsage
