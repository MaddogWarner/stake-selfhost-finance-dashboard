from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.holding import Holding
from app.models.watchlist import Watchlist
from app.schemas.holding import HoldingRead, WatchlistRead
from app.services import stake_client

router = APIRouter()


def _exchange_filter(exchange: str | None) -> str | None:
    return exchange.upper() if exchange else None


async def sync_stake_data(db: AsyncSession) -> None:
    holdings = await stake_client.get_holdings()
    watchlist = await stake_client.get_watchlist()

    for item in holdings:
        stmt = insert(Holding).values(**item)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Holding.ticker, Holding.exchange],
            set_={"quantity": stmt.excluded.quantity, "avg_cost": stmt.excluded.avg_cost, "last_synced_at": stmt.excluded.last_synced_at},
        )
        await db.execute(stmt)

    for item in watchlist:
        stmt = insert(Watchlist).values(**item)
        stmt = stmt.on_conflict_do_nothing(index_elements=[Watchlist.ticker, Watchlist.exchange])
        await db.execute(stmt)

    await db.commit()


@router.post("/sync")
async def sync_now(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    await sync_stake_data(db)
    return {"synced": True}


@router.get("/holdings", response_model=list[HoldingRead])
async def list_holdings(
    exchange: str | None = Query(default=None, pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    stmt = select(Holding).order_by(Holding.ticker)
    if filtered := _exchange_filter(exchange):
        stmt = stmt.where(Holding.exchange == filtered)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/watchlist", response_model=list[WatchlistRead])
async def list_watchlist(
    exchange: str | None = Query(default=None, pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
) -> list[Watchlist]:
    stmt = select(Watchlist).order_by(Watchlist.ticker)
    if filtered := _exchange_filter(exchange):
        stmt = stmt.where(Watchlist.exchange == filtered)
    return list((await db.execute(stmt)).scalars().all())
