import logging
from datetime import datetime, timezone

from cryptography.fernet import InvalidToken
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting
from app.services.crypto_service import decrypt, encrypt

logger = logging.getLogger(__name__)

VALID_SOURCES = {"fmp", "yfinance", "both"}
SETTINGS_REDIS_KEY = "settings:data_source"


async def get_stake_token(db: AsyncSession) -> str | None:
    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "stake_session_token")
    )
    value = result.scalar_one_or_none()
    if value is None:
        return None
    if value.startswith("enc:v1:"):
        try:
            return decrypt(value.removeprefix("enc:v1:"))
        except InvalidToken:
            logger.error(
                "Stored Stake token cannot be decrypted because the encryption key no longer matches; reconnect Stake."
            )
            await mark_stake_token_invalid(db)
            return None
    # Legacy plaintext values are upgraded on first successful read. Only the stored
    # value changes; saved_at/invalid metadata must reflect the original token, not
    # the migration, so the expiry warning fires on time.
    await _upsert_stake_token_value(db, value)
    await db.commit()
    return value


async def _upsert_stake_token_value(db: AsyncSession, token: str) -> None:
    encrypted = f"enc:v1:{encrypt(token)}"
    stmt = insert(AppSetting).values(key="stake_session_token", value=encrypted)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": stmt.excluded.value, "updated_at": func.now()},
    )
    await db.execute(stmt)


async def set_stake_token(db: AsyncSession, token: str) -> None:
    await _upsert_stake_token_value(db, token)
    await set_stake_token_meta(db)
    await db.commit()


async def set_stake_token_meta(db: AsyncSession) -> None:
    saved_at = datetime.now(timezone.utc).isoformat()
    saved_stmt = insert(AppSetting).values(key="stake_token_saved_at", value=saved_at)
    saved_stmt = saved_stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": saved_stmt.excluded.value, "updated_at": func.now()},
    )
    await db.execute(saved_stmt)
    invalid_stmt = insert(AppSetting).values(key="stake_token_invalid", value="false")
    invalid_stmt = invalid_stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": "false", "updated_at": func.now()},
    )
    await db.execute(invalid_stmt)


async def mark_stake_token_invalid(db: AsyncSession) -> None:
    stmt = insert(AppSetting).values(key="stake_token_invalid", value="true")
    stmt = stmt.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": "true", "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()


async def get_stake_token_meta(db: AsyncSession) -> tuple[datetime | None, bool]:
    result = await db.execute(
        select(AppSetting.key, AppSetting.value).where(
            AppSetting.key.in_(("stake_token_saved_at", "stake_token_invalid"))
        )
    )
    values = dict(result.all())
    saved_at = None
    raw_saved_at = values.get("stake_token_saved_at")
    if raw_saved_at:
        try:
            saved_at = datetime.fromisoformat(raw_saved_at.replace("Z", "+00:00"))
            if saved_at.tzinfo is None:
                saved_at = saved_at.replace(tzinfo=timezone.utc)
        except ValueError:
            saved_at = None
    invalid = values.get("stake_token_invalid") == "true"
    return saved_at, invalid


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
