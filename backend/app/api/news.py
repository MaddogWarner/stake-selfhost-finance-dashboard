from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.news import News
from app.services import fmp_service

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

    rows = (
        await db.execute(
            select(News).where(News.ticker == ticker).order_by(News.published_at.desc().nullslast()).limit(5)
        )
    ).scalars().all()
    if rows:
        payload = [
            {
                "ticker": row.ticker,
                "headline": row.headline,
                "source": row.source,
                "url": row.url,
                "published_at": row.published_at.isoformat() if row.published_at else None,
            }
            for row in rows
        ]
        await redis.setex(cache_key, 3600, json.dumps(payload, default=str))
        return payload

    items = await fmp_service.get_news(db, ticker, limit=5)
    payload: list[dict] = []
    for item in items:
        headline = item.get("title") or item.get("headline") or ""
        published_at = _parse_datetime(item.get("publishedDate"))
        if headline:
            stmt = insert(News).values(
                ticker=ticker,
                headline=headline,
                source=item.get("site") or item.get("source"),
                url=item.get("url"),
                published_at=published_at,
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=[News.ticker, News.url])
            await db.execute(stmt)
            payload.append(
                {
                    "ticker": ticker,
                    "headline": headline,
                    "source": item.get("site") or item.get("source"),
                    "url": item.get("url"),
                    "published_at": published_at.isoformat() if published_at else None,
                }
            )
    await db.commit()
    await redis.setex(cache_key, 3600, json.dumps(payload, default=str))
    return payload
