from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.api.holdings import sync_stake_data
from app.db.redis import redis_client
from app.db.session import AsyncSessionLocal
from app.models.company_profile import CompanyProfile
from app.models.holding import Holding
from app.models.news import News
from app.models.price_history import PriceHistory
from app.models.watchlist import Watchlist
from app.services import fmp_service, yfinance_service
from app.services.settings_service import get_data_source

SYDNEY = ZoneInfo("Australia/Sydney")
NEW_YORK = ZoneInfo("America/New_York")


async def _unique_tickers() -> list[tuple[str, str]]:
    async with AsyncSessionLocal() as db:
        holdings = (await db.execute(select(Holding.ticker, Holding.exchange))).all()
        watchlist = (
            await db.execute(select(Watchlist.ticker, Watchlist.exchange))
        ).all()
    return sorted(
        set((ticker, exchange) for ticker, exchange in [*holdings, *watchlist])
    )


def is_asx_open(now_utc: datetime | None = None) -> bool:
    now = (now_utc or datetime.now(timezone.utc)).astimezone(SYDNEY)
    return now.weekday() < 5 and time(10, 0) <= now.time() <= time(16, 0)


def is_nyse_open(now_utc: datetime | None = None) -> bool:
    now = (now_utc or datetime.now(timezone.utc)).astimezone(NEW_YORK)
    return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def sync_stake_holdings() -> None:
    async with AsyncSessionLocal() as db:
        await sync_stake_data(db)


async def refresh_prices() -> None:
    asx_open = is_asx_open()
    nyse_open = is_nyse_open()
    if not asx_open and not nyse_open:
        return

    tickers = [
        item
        for item in await _unique_tickers()
        if (item[1] == "ASX" and asx_open) or (item[1] == "NYSE" and nyse_open)
    ]
    history_by_ticker = await yfinance_service.download_batch_history(
        tickers, period="1y"
    )
    async with AsyncSessionLocal() as db:
        for ticker, exchange in tickers:
            for point in history_by_ticker.get(f"{ticker}:{exchange}", []):
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
            await redis_client.delete(f"price:{ticker}")
        await db.commit()


async def refresh_fundamentals() -> None:
    tickers = await _unique_tickers()
    async with AsyncSessionLocal() as db:
        source = await get_data_source(redis_client, db)
        existing = set(
            (await db.execute(select(CompanyProfile.ticker))).scalars().all()
        )
        for ticker, exchange in tickers:
            if ticker in existing:
                continue
            if source == "yfinance":
                profile = await yfinance_service.get_fundamentals(ticker, exchange)
                row = CompanyProfile(
                    ticker=ticker,
                    exchange=exchange,
                    name=profile.get("name"),
                    sector=profile.get("sector"),
                    industry=profile.get("industry"),
                    description=profile.get("description"),
                    market_cap=profile.get("market_cap"),
                    pe_ratio=profile.get("pe_ratio"),
                )
            else:
                try:
                    profile = await fmp_service.get_company_profile(db, ticker)
                    ratios = await fmp_service.get_financial_ratios(db, ticker)
                except HTTPException as exc:
                    if exc.status_code == 429:
                        break
                    raise
                if not profile:
                    continue
                row = CompanyProfile(
                    ticker=ticker,
                    exchange=exchange,
                    name=profile.get("companyName"),
                    sector=profile.get("sector"),
                    industry=profile.get("industry"),
                    description=profile.get("description"),
                    market_cap=profile.get("marketCap"),
                    pe_ratio=ratios.get("priceToEarningsRatioTTM"),
                )
            db.add(row)
        await db.commit()


async def refresh_news() -> None:
    tickers = await _unique_tickers()
    async with AsyncSessionLocal() as db:
        for ticker, exchange in tickers:
            # News always comes from Yahoo Finance (FMP news is a gated paid add-on).
            items = await yfinance_service.get_news(ticker, exchange, limit=3)
            for item in items:
                headline = item.get("headline") or item.get("title")
                if not headline:
                    continue
                published_at = item.get("published_at") or _parse_datetime(
                    item.get("publishedDate")
                )
                stmt = insert(News).values(
                    ticker=ticker,
                    headline=headline,
                    source=item.get("source") or item.get("site"),
                    url=item.get("url"),
                    published_at=published_at,
                )
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=[News.ticker, News.url]
                )
                await db.execute(stmt)
            await redis_client.delete(f"news:{ticker}")
        await db.commit()


async def refresh_financials() -> None:
    async with AsyncSessionLocal() as db:
        source = await get_data_source(redis_client, db)
        if source == "yfinance":
            return
        tickers = await _unique_tickers()
        for ticker, exchange in tickers:
            try:
                profile = await fmp_service.get_company_profile(db, ticker)
                ratios = await fmp_service.get_financial_ratios(db, ticker)
            except HTTPException as exc:
                if exc.status_code == 429:
                    break
                raise
            payload = {
                "ticker": ticker,
                "exchange": exchange,
                "name": profile.get("companyName"),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "description": profile.get("description"),
                "market_cap": profile.get("marketCap"),
                "pe_ratio": ratios.get("priceToEarningsRatioTTM"),
            }
            stmt = insert(CompanyProfile).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=[CompanyProfile.ticker],
                set_={
                    key: getattr(stmt.excluded, key)
                    for key in payload
                    if key != "ticker"
                },
            )
            await db.execute(stmt)
            await redis_client.delete(f"fundamentals:{ticker}", f"profile:{ticker}")
        await db.commit()


async def prune_price_history() -> None:
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=730)
    async with AsyncSessionLocal() as db:
        await db.execute(delete(PriceHistory).where(PriceHistory.date < cutoff))
        await db.commit()
