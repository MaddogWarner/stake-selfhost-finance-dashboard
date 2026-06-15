from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.news import News
from app.services import yfinance_service

router = APIRouter()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/news/{ticker}")
async def get_news(
    ticker: str,
    exchange: str | None = Query(default=None, pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> list[dict]:
    ticker = ticker.upper()
    cache_key = f"news:{ticker}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    selected_exchange = exchange.upper() if exchange else "NYSE"
    # News always comes from Yahoo Finance: FMP news is a paid add-on not available on
    # standard plans, whereas yfinance news is free and reliable.
    items = await yfinance_service.get_news(ticker, selected_exchange, limit=5)

    payload: list[dict] = []
    for item in items:
        headline = item.get("headline") or item.get("title") or ""
        published_at = item.get("published_at") or _parse_datetime(
            item.get("publishedDate")
        )
        if headline:
            stmt = insert(News).values(
                ticker=ticker,
                headline=headline,
                source=item.get("source") or item.get("site"),
                url=item.get("url"),
                published_at=published_at,
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=[News.ticker, News.url])
            await db.execute(stmt)
            payload.append(
                {
                    "ticker": ticker,
                    "headline": headline,
                    "source": item.get("source") or item.get("site"),
                    "url": item.get("url"),
                    "published_at": published_at.isoformat() if published_at else None,
                }
            )
    await db.commit()
    await redis.setex(cache_key, 3600, json.dumps(payload, default=str))
    return payload
