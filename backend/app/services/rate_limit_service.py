import logging
import time

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.db.redis import get_redis

logger = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    # Trusted only because nginx overwrites X-Forwarded-For and the backend is host-local.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
    async def dependency(request: Request, redis: Redis = Depends(get_redis)) -> None:
        window = int(time.time()) // window_seconds
        key = f"ratelimit:{scope}:{client_ip(request)}:{window}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
        except Exception as exc:  # noqa: BLE001 - rate limiting must fail open
            logger.warning("Rate limiting unavailable; allowing request: %s", exc)
            return
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Try again shortly.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
