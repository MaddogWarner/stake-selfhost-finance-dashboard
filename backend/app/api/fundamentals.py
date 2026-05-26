from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.company_profile import CompanyProfile
from app.services import fmp_service

router = APIRouter()


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(
    ticker: str,
    exchange: str = Query(pattern="^(ASX|NYSE)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    ticker = ticker.upper()
    exchange = exchange.upper()
    cache_key = f"fundamentals:{ticker}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    row = (await db.execute(select(CompanyProfile).where(CompanyProfile.ticker == ticker))).scalar_one_or_none()
    if row:
        payload = {
            "ticker": row.ticker,
            "exchange": row.exchange,
            "name": row.name,
            "sector": row.sector,
            "industry": row.industry,
            "description": row.description,
            "market_cap": row.market_cap,
            "pe_ratio": float(row.pe_ratio) if row.pe_ratio is not None else None,
            "fetched_at": row.fetched_at.isoformat(),
        }
        await redis.setex(cache_key, 86400, json.dumps(payload, default=str))
        return payload

    profile = await fmp_service.get_company_profile(db, ticker)
    ratios = await fmp_service.get_financial_ratios(db, ticker)
    payload = {
        "ticker": ticker,
        "exchange": exchange,
        "name": profile.get("companyName") or profile.get("companyName", ticker),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "description": profile.get("description"),
        "market_cap": profile.get("mktCap"),
        "pe_ratio": ratios.get("peRatioTTM") or profile.get("pe"),
    }
    stmt = insert(CompanyProfile).values(**payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=[CompanyProfile.ticker],
        set_={
            "exchange": stmt.excluded.exchange,
            "name": stmt.excluded.name,
            "sector": stmt.excluded.sector,
            "industry": stmt.excluded.industry,
            "description": stmt.excluded.description,
            "market_cap": stmt.excluded.market_cap,
            "pe_ratio": stmt.excluded.pe_ratio,
            "fetched_at": stmt.excluded.fetched_at,
        },
    )
    await db.execute(stmt)
    await db.commit()
    await redis.setex(cache_key, 86400, json.dumps(payload, default=str))
    return payload
