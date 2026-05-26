from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.company_profile import CompanyProfile
from app.services import fmp_service, yfinance_service
from app.services.settings_service import get_data_source

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

    source = await get_data_source(redis, db)
    if source == "yfinance":
        raw = await yfinance_service.get_fundamentals(ticker, exchange)
        payload = {
            "ticker": ticker,
            "exchange": exchange,
            "name": raw.get("name"),
            "sector": raw.get("sector"),
            "industry": raw.get("industry"),
            "description": raw.get("description"),
            "market_cap": raw.get("market_cap"),
            "pe_ratio": raw.get("pe_ratio"),
            "fetched_at": datetime.now(timezone.utc),
        }
    else:
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
            "fetched_at": datetime.now(timezone.utc),
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
