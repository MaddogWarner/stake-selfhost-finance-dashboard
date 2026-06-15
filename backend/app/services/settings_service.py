from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting

VALID_SOURCES = {"fmp", "yfinance", "both"}
SETTINGS_REDIS_KEY = "settings:data_source"


async def get_stake_token(db: AsyncSession) -> str | None:
    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "stake_session_token")
    )
    return result.scalar_one_or_none()


async def set_stake_token(db: AsyncSession, token: str) -> None:
    stmt = insert(AppSetting).values(key="stake_session_token", value=token)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": stmt.excluded.value, "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()


async def get_data_source(redis: Redis, db: AsyncSession) -> str:
    cached = await redis.get(SETTINGS_REDIS_KEY)
    if cached in VALID_SOURCES:
        return cached

    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "data_source")
    )
    value = result.scalar_one_or_none() or "both"
    if value not in VALID_SOURCES:
        value = "both"
    await redis.set(SETTINGS_REDIS_KEY, value)
    return value


async def set_data_source(redis: Redis, db: AsyncSession, value: str) -> str:
    stmt = insert(AppSetting).values(key="data_source", value=value)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": stmt.excluded.value, "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()
    await redis.set(SETTINGS_REDIS_KEY, value)
    await flush_data_source_caches(redis)
    return value


async def flush_data_source_caches(redis: Redis) -> None:
    keys: list[str] = []
    keys.extend(await redis.keys("fundamentals:*"))
    keys.extend(await redis.keys("news:*"))
    if keys:
        await redis.delete(*keys)
