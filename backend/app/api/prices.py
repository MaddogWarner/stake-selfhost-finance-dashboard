from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.price_history import PriceHistory
from app.services import yfinance_service

router = APIRouter()


def _close_values(history: list[dict]) -> list[float]:
    values: list[float] = []
    for point in history:
        close = point.get("close")
        if close is not None:
            values.append(float(close))
    return values


@router.get("/prices/{ticker}")
async def get_price(
    ticker: str,
    exchange: str = Query(pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    ticker = ticker.upper()
    exchange = exchange.upper()
    cache_key = f"price:{ticker}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    quote = await yfinance_service.get_live_quote(ticker, exchange)
    history = await yfinance_service.get_price_history(ticker, exchange)
    if history:
        for point in history:
            stmt = insert(PriceHistory).values(ticker=ticker, **point)
            stmt = stmt.on_conflict_do_update(
                index_elements=[PriceHistory.ticker, PriceHistory.date],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            await db.execute(stmt)
        await db.commit()
    else:
        rows = (
            await db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == ticker)
                .order_by(PriceHistory.date.desc())
                .limit(365)
            )
        ).scalars().all()
        history = [
            {
                "date": row.date.isoformat() if isinstance(row.date, date) else row.date,
                "open": float(row.open) if row.open is not None else None,
                "high": float(row.high) if row.high is not None else None,
                "low": float(row.low) if row.low is not None else None,
                "close": float(row.close) if row.close is not None else None,
                "volume": row.volume,
            }
            for row in reversed(rows)
        ]

    closes = _close_values(history)
    moving_average_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    payload = {
        **quote,
        "history": history[-30:],
        "week52_high": max(closes, default=None),
        "week52_low": min(closes, default=None),
        "moving_average_50": moving_average_50,
    }
    await redis.setex(cache_key, 300, json.dumps(payload, default=str))
    return payload
