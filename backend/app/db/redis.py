from collections.abc import AsyncGenerator

from redis.asyncio import Redis, from_url

from app.config import settings

redis_client: Redis = from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client


async def close_redis() -> None:
    await redis_client.aclose()
