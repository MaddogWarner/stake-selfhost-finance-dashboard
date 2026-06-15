from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.api_usage import ApiUsage
from app.models.holding import Holding
from app.services import stake_client
from app.services.rate_limiter import FMP_DAILY_LIMIT
from app.services.settings_service import (
    VALID_SOURCES,
    get_data_source,
    set_data_source,
    set_stake_token,
)
from app.services.stake_service import get_cached_token, set_cached_token

router = APIRouter()


class AppSettingsRead(BaseModel):
    data_source: str


class AppSettingsUpdate(BaseModel):
    data_source: str


class StakeTokenUpdate(BaseModel):
    token: str


class StakeStatus(BaseModel):
    configured: bool
    last_sync: datetime | None


@router.get("/admin/usage")
async def get_usage(db: AsyncSession = Depends(get_db)) -> dict:
    count = (
        await db.execute(
            select(ApiUsage.call_count).where(
                ApiUsage.provider == "fmp", ApiUsage.date == date.today()
            )
        )
    ).scalar_one_or_none() or 0
    return {
        "fmp": {
            "today": count,
            "limit": FMP_DAILY_LIMIT,
            "remaining": max(FMP_DAILY_LIMIT - count, 0),
        }
    }


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
        raise HTTPException(
            status_code=422, detail="data_source must be one of: both, fmp, yfinance"
        )
    return {"data_source": await set_data_source(redis, db, data_source)}


@router.get("/admin/stake-status", response_model=StakeStatus)
async def stake_status(db: AsyncSession = Depends(get_db)) -> StakeStatus:
    last_sync = (
        await db.execute(select(func.max(Holding.last_synced_at)))
    ).scalar_one_or_none()
    return StakeStatus(configured=get_cached_token() is not None, last_sync=last_sync)


@router.post("/admin/stake-token", response_model=StakeStatus)
async def set_stake_token_endpoint(
    payload: StakeTokenUpdate, db: AsyncSession = Depends(get_db)
) -> StakeStatus:
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token must not be empty.")
    try:
        await stake_client.validate_token(token)
    except Exception as exc:  # noqa: BLE001 - surface any auth/library failure to the user
        raise HTTPException(
            status_code=400, detail=f"Stake rejected this token: {exc}"
        ) from exc

    await set_stake_token(db, token)
    set_cached_token(token)
    last_sync = (
        await db.execute(select(func.max(Holding.last_synced_at)))
    ).scalar_one_or_none()
    return StakeStatus(configured=True, last_sync=last_sync)
