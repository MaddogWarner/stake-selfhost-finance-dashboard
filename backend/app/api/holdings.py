from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.holding import Holding
from app.models.watchlist import Watchlist
from app.schemas.holding import (
    HoldingCreate,
    HoldingRead,
    HoldingUpdate,
    WatchlistCreate,
    WatchlistRead,
)
from app.services import stake_client
from app.utils.tickers import normalise_ticker

router = APIRouter()


def _exchange_filter(exchange: str | None) -> str | None:
    return exchange.upper() if exchange else None


async def sync_stake_data(db: AsyncSession) -> None:
    holdings = await stake_client.get_holdings()
    watchlist = await stake_client.get_watchlist()

    for item in holdings:
        stmt = insert(Holding).values(**item, source="stake")
        stmt = stmt.on_conflict_do_update(
            index_elements=[Holding.ticker, Holding.exchange],
            set_={
                "quantity": stmt.excluded.quantity,
                "avg_cost": stmt.excluded.avg_cost,
                "source": "stake",
                "last_synced_at": func.now(),
            },
        )
        await db.execute(stmt)

    for item in watchlist:
        stmt = insert(Watchlist).values(**item, source="stake")
        stmt = stmt.on_conflict_do_nothing(index_elements=[Watchlist.ticker, Watchlist.exchange])
        await db.execute(stmt)

    await db.commit()


@router.post("/sync")
async def sync_now(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    try:
        await sync_stake_data(db)
    except RuntimeError as exc:
        # Stake not configured / token invalid. Manual data is untouched.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@router.post("/holdings", response_model=HoldingRead, status_code=201)
async def create_holding(payload: HoldingCreate, db: AsyncSession = Depends(get_db)) -> Holding:
    ticker = normalise_ticker(payload.ticker, payload.exchange)
    stmt = insert(Holding).values(
        ticker=ticker,
        exchange=payload.exchange,
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
        source="manual",
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Holding.ticker, Holding.exchange],
        set_={
            "quantity": stmt.excluded.quantity,
            "avg_cost": stmt.excluded.avg_cost,
            "source": "manual",
            "last_synced_at": func.now(),
        },
    )
    await db.execute(stmt)
    await db.commit()
    row = (
        await db.execute(
            select(Holding).where(Holding.ticker == ticker, Holding.exchange == payload.exchange)
        )
    ).scalar_one()
    return row


@router.patch("/holdings/{holding_id}", response_model=HoldingRead)
async def update_holding(
    holding_id: int, payload: HoldingUpdate, db: AsyncSession = Depends(get_db)
) -> Holding:
    holding = await db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    if payload.quantity is not None:
        holding.quantity = payload.quantity
    if payload.avg_cost is not None:
        holding.avg_cost = payload.avg_cost
    await db.commit()
    await db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}")
async def delete_holding(holding_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    result = await db.execute(delete(Holding).where(Holding.id == holding_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"deleted": True}


@router.get("/watchlist", response_model=list[WatchlistRead])
async def list_watchlist(
    exchange: str | None = Query(default=None, pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
) -> list[Watchlist]:
    stmt = select(Watchlist).order_by(Watchlist.ticker)
    if filtered := _exchange_filter(exchange):
        stmt = stmt.where(Watchlist.exchange == filtered)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/watchlist", response_model=WatchlistRead, status_code=201)
async def create_watchlist(payload: WatchlistCreate, db: AsyncSession = Depends(get_db)) -> Watchlist:
    ticker = normalise_ticker(payload.ticker, payload.exchange)
    stmt = insert(Watchlist).values(ticker=ticker, exchange=payload.exchange, source="manual")
    stmt = stmt.on_conflict_do_nothing(index_elements=[Watchlist.ticker, Watchlist.exchange])
    await db.execute(stmt)
    await db.commit()
    row = (
        await db.execute(
            select(Watchlist).where(
                Watchlist.ticker == ticker, Watchlist.exchange == payload.exchange
            )
        )
    ).scalar_one()
    return row


@router.delete("/watchlist/{watchlist_id}")
async def delete_watchlist(watchlist_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    result = await db.execute(delete(Watchlist).where(Watchlist.id == watchlist_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return {"deleted": True}
