from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.api_usage import ApiUsage
from app.services.rate_limiter import FMP_DAILY_LIMIT
from app.services.settings_service import VALID_SOURCES, get_data_source, set_data_source

router = APIRouter()


class AppSettingsRead(BaseModel):
    data_source: str


class AppSettingsUpdate(BaseModel):
    data_source: str


@router.get("/admin/usage")
async def get_usage(db: AsyncSession = Depends(get_db)) -> dict:
    count = (
        await db.execute(
            select(ApiUsage.call_count).where(ApiUsage.provider == "fmp", ApiUsage.date == date.today())
        )
    ).scalar_one_or_none() or 0
    return {"fmp": {"today": count, "limit": FMP_DAILY_LIMIT, "remaining": max(FMP_DAILY_LIMIT - count, 0)}}


@router.get("/admin/settings", response_model=AppSettingsRead)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    return {"data_source": await get_data_source(redis, db)}


@router.post("/admin/settings", response_model=AppSettingsRead)
async def update_settings(
    settings: AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    data_source = settings.data_source.lower()
    if data_source not in VALID_SOURCES:
        raise HTTPException(status_code=422, detail="data_source must be one of: both, fmp, yfinance")
    return {"data_source": await set_data_source(redis, db, data_source)}
