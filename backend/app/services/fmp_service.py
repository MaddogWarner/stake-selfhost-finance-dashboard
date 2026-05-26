from __future__ import annotations

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services import rate_limiter

BASE_URL = "https://financialmodelingprep.com/api/v3"


async def _get(db: AsyncSession, path: str, params: dict | None = None) -> object:
    if not settings.fmp_api_key:
        raise HTTPException(status_code=503, detail="FMP API key is not configured")
    if not await rate_limiter.can_call_fmp(db):
        raise HTTPException(status_code=429, detail="FMP daily limit reached")

    query = {**(params or {}), "apikey": settings.fmp_api_key}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20) as client:
        response = await client.get(path, params=query)
        response.raise_for_status()
    await rate_limiter.record_fmp_call(db)
    return response.json()


async def get_company_profile(db: AsyncSession, ticker: str) -> dict:
    data = await _get(db, f"/profile/{ticker.upper()}")
    return data[0] if isinstance(data, list) and data else {}


async def get_financial_ratios(db: AsyncSession, ticker: str) -> dict:
    data = await _get(db, f"/ratios-ttm/{ticker.upper()}")
    return data[0] if isinstance(data, list) and data else {}


async def get_income_statement(db: AsyncSession, ticker: str) -> list[dict]:
    data = await _get(db, f"/income-statement/{ticker.upper()}", {"limit": 5})
    return data if isinstance(data, list) else []


async def get_news(db: AsyncSession, ticker: str, limit: int = 5) -> list[dict]:
    data = await _get(db, "/stock_news", {"tickers": ticker.upper(), "limit": limit})
    return data if isinstance(data, list) else []
