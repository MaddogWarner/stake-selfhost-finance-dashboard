import asyncio

from app.db.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.services.auth_service import reset_password


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await reset_password(db, redis_client)
    await redis_client.aclose()
    print("Admin password reset. The setup wizard will appear on the next visit.")


if __name__ == "__main__":
    asyncio.run(main())
