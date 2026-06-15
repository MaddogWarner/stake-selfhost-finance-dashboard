from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

import yfinance as yf


def normalise_ticker(ticker: str, exchange: str) -> str:
    bare = ticker.upper().strip().removesuffix(".AX")
    return f"{bare}.AX" if exchange.upper() == "ASX" else bare


def _clean_float(value: Any) -> float | None:
    try:
        if value is None or value != value:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested_url(value: Any) -> str | None:
    if isinstance(value, dict):
        url = value.get("url")
        return str(url) if url else None
    return str(value) if value else None


async def get_price_history(ticker: str, exchange: str) -> list[dict[str, Any]]:
    symbol = normalise_ticker(ticker, exchange)

    def _download() -> list[dict[str, Any]]:
        # Use Ticker.history (single HTTP fetch) rather than yf.download, whose internal
        # thread pool deadlocks the device when many cards request prices concurrently.
        frame = yf.Ticker(symbol).history(period="1y", auto_adjust=True)
        if frame.empty:
            return []
        rows: list[dict[str, Any]] = []
        for index, row in frame.reset_index().iterrows():
            row_date = row.get("Date")
            if hasattr(row_date, "date"):
                row_date = row_date.date()
            rows.append(
                {
                    "date": row_date,
                    "open": _clean_float(row.get("Open")),
                    "high": _clean_float(row.get("High")),
                    "low": _clean_float(row.get("Low")),
                    "close": _clean_float(row.get("Close")),
                    "volume": int(row.get("Volume") or 0),
                }
            )
        return rows

    return await asyncio.to_thread(_download)


async def get_live_quote(ticker: str, exchange: str) -> dict[str, Any]:
    symbol = normalise_ticker(ticker, exchange)

    def _quote() -> dict[str, Any]:
        info = yf.Ticker(symbol).fast_info
        # yfinance 1.x exposes camelCase fast_info keys (lastPrice/previousClose);
        # keep snake_case fallbacks for older versions.
        price = _clean_float(info.get("lastPrice") or info.get("last_price"))
        prev_close = _clean_float(
            info.get("previousClose") or info.get("previous_close")
        )
        change = (
            price - prev_close if price is not None and prev_close is not None else None
        )
        change_pct = (
            (change / prev_close * 100) if change is not None and prev_close else None
        )
        return {
            "ticker": ticker.upper(),
            "exchange": exchange.upper(),
            "price": price,
            "prev_close": prev_close,
            "day_change": change,
            "day_change_pct": change_pct,
            "currency": info.get("currency"),
        }

    return await asyncio.to_thread(_quote)


async def get_fundamentals(ticker: str, exchange: str) -> dict[str, Any]:
    symbol = normalise_ticker(ticker, exchange)

    def _fetch() -> dict[str, Any]:
        info = yf.Ticker(symbol).info or {}
        return {
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": info.get("longBusinessSummary"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
        }

    return await asyncio.to_thread(_fetch)


async def get_news(ticker: str, exchange: str, limit: int = 5) -> list[dict[str, Any]]:
    symbol = normalise_ticker(ticker, exchange)

    def _fetch() -> list[dict[str, Any]]:
        items = yf.Ticker(symbol).news or []
        result: list[dict[str, Any]] = []
        for item in items[:limit]:
            content = (
                item.get("content") if isinstance(item.get("content"), dict) else {}
            )
            provider = (
                content.get("provider")
                if isinstance(content.get("provider"), dict)
                else {}
            )
            published = item.get("providerPublishTime") or content.get("pubDate")
            published_at = None
            if isinstance(published, (int, float)):
                published_at = datetime.fromtimestamp(published, tz=timezone.utc)
            elif isinstance(published, str):
                try:
                    published_at = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    )
                except ValueError:
                    published_at = None
            result.append(
                {
                    "headline": item.get("title") or content.get("title"),
                    "source": item.get("publisher") or provider.get("displayName"),
                    "url": item.get("link")
                    or _nested_url(content.get("clickThroughUrl"))
                    or _nested_url(content.get("canonicalUrl")),
                    "published_at": published_at,
                }
            )
        return result

    return await asyncio.to_thread(_fetch)


async def download_batch_history(
    tickers: list[tuple[str, str]], period: str = "1y"
) -> dict[str, list[dict[str, Any]]]:
    grouped = [
        (ticker, exchange, normalise_ticker(ticker, exchange))
        for ticker, exchange in tickers
    ]
    if not grouped:
        return {}

    def _download() -> dict[str, list[dict[str, Any]]]:
        symbols = [item[2] for item in grouped]
        frame = yf.download(
            symbols,
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=False,
        )
        data: dict[str, list[dict[str, Any]]] = {}
        for ticker, exchange, symbol in grouped:
            source = (
                frame[symbol]
                if len(symbols) > 1 and symbol in frame.columns.get_level_values(0)
                else frame
            )
            rows: list[dict[str, Any]] = []
            if source.empty:
                data[f"{ticker}:{exchange}"] = rows
                continue
            for _, row in source.reset_index().iterrows():
                row_date = row.get("Date")
                if hasattr(row_date, "date"):
                    row_date = row_date.date()
                if isinstance(row_date, date):
                    rows.append(
                        {
                            "date": row_date,
                            "open": _clean_float(row.get("Open")),
                            "high": _clean_float(row.get("High")),
                            "low": _clean_float(row.get("Low")),
                            "close": _clean_float(row.get("Close")),
                            "volume": int(row.get("Volume") or 0),
                        }
                    )
            data[f"{ticker}:{exchange}"] = rows
        return data

    return await asyncio.to_thread(_download)
