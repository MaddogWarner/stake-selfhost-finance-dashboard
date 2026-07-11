import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, fundamentals, holdings, news, prices
from app.db.redis import close_redis
from app.db.session import AsyncSessionLocal
from app.scheduler.registry import start_scheduler, stop_scheduler
from app.services.stake_service import bootstrap_stake_token
from app.services.auth_service import require_auth
from app.services.crypto_service import initialise_crypto
from app.services.rate_limit_service import rate_limit
from app.version import __version__


def _run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(_run_migrations)
    initialise_crypto()
    async with AsyncSessionLocal() as db:
        await bootstrap_stake_token(db)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()
        await close_redis()


app = FastAPI(
    title="Stake Investment Dashboard", version=__version__, lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3443",
        "https://127.0.0.1:3443",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

protected = [Depends(require_auth), Depends(rate_limit("global", 240, 60))]
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(
    holdings.router, prefix="/api", tags=["holdings"], dependencies=protected
)
app.include_router(
    prices.router, prefix="/api", tags=["prices"], dependencies=protected
)
app.include_router(
    fundamentals.router, prefix="/api", tags=["fundamentals"], dependencies=protected
)
app.include_router(news.router, prefix="/api", tags=["news"], dependencies=protected)
app.include_router(admin.router, prefix="/api", tags=["admin"], dependencies=protected)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# Under /api so the production nginx proxy reaches it (it only forwards /api).
@app.get("/api/version")
async def version() -> dict[str, str]:
    return {"version": __version__}
