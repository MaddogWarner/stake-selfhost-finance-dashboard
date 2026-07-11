import secrets

import bcrypt
from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.models.app_setting import AppSetting

PASSWORD_KEY = "admin_password_hash"
SESSION_COOKIE = "stake_dash_session"
SESSION_TTL_SECONDS = 604800


async def get_password_hash(db: AsyncSession) -> str | None:
    result = await db.execute(select(AppSetting.value).where(AppSetting.key == PASSWORD_KEY))
    return result.scalar_one_or_none()


def validate_password(password: str) -> None:
    length = len(password.encode())
    if length < 10:
        raise ValueError("Password must be at least 10 characters.")
    if length > 72:
        raise ValueError("Password must be no more than 72 bytes.")


async def set_password(db: AsyncSession, password: str) -> bool:
    validate_password(password)
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    stmt = insert(AppSetting).values(key=PASSWORD_KEY, value=password_hash)
    stmt = stmt.on_conflict_do_nothing(index_elements=[AppSetting.key]).returning(AppSetting.key)
    won = (await db.execute(stmt)).scalar_one_or_none() is not None
    await db.commit()
    return won


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


async def create_session(redis: Redis) -> str:
    token = secrets.token_urlsafe(32)
    await redis.set(f"session:{token}", "1", ex=SESSION_TTL_SECONDS)
    return token


async def check_session(redis: Redis, token: str | None) -> bool:
    return bool(token and await redis.exists(f"session:{token}"))


async def destroy_session(redis: Redis, token: str | None) -> None:
    if token:
        await redis.delete(f"session:{token}")


async def require_auth(request: Request, redis: Redis = Depends(get_redis)) -> None:
    if not await check_session(redis, request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Not authenticated")


async def reset_password(db: AsyncSession, redis: Redis) -> None:
    await db.execute(delete(AppSetting).where(AppSetting.key == PASSWORD_KEY))
    await db.commit()
    keys = [key async for key in redis.scan_iter(match="session:*")]
    if keys:
        await redis.delete(*keys)
