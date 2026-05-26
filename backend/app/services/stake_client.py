import inspect
from decimal import Decimal
from typing import Any

from app.config import settings


def _normalise_exchange(value: str | None) -> str:
    raw = (value or "").upper()
    if raw in {"ASX", "AU", "AUS"}:
        return "ASX"
    return "NYSE"


def _normalise_ticker(value: str, exchange: str) -> str:
    ticker = value.upper().strip()
    if exchange == "ASX":
        ticker = ticker.removesuffix(".AX")
    return ticker


def _extract_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value))


async def _build_client() -> Any:
    try:
        import stake  # type: ignore
    except ImportError as exc:
        raise RuntimeError("stake-python is not installed") from exc

    if settings.stake_session_token:
        if hasattr(stake, "Stake"):
            return stake.Stake(session_token=settings.stake_session_token)
        if hasattr(stake, "StakeClient"):
            return stake.StakeClient(session_token=settings.stake_session_token)

    if settings.stake_username and settings.stake_password:
        if hasattr(stake, "Stake"):
            return stake.Stake(username=settings.stake_username, password=settings.stake_password)
        if hasattr(stake, "StakeClient"):
            return stake.StakeClient(username=settings.stake_username, password=settings.stake_password)

    raise RuntimeError("Stake credentials are not configured")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _call_first(client: Any, method_names: tuple[str, ...]) -> Any:
    for name in method_names:
        method = getattr(client, name, None)
        if method:
            return await _maybe_await(method())
    raise RuntimeError(f"Stake client does not expose any of: {', '.join(method_names)}")


async def get_holdings() -> list[dict[str, Any]]:
    client = await _build_client()
    raw_holdings = await _call_first(client, ("get_holdings", "holdings", "portfolio"))
    rows = raw_holdings.get("holdings", raw_holdings) if isinstance(raw_holdings, dict) else raw_holdings
    holdings: list[dict[str, Any]] = []
    for row in rows or []:
        symbol = row.get("ticker") or row.get("symbol") or row.get("instrument", {}).get("symbol")
        if not symbol:
            continue
        exchange = _normalise_exchange(row.get("exchange") or row.get("market") or row.get("instrument", {}).get("exchange"))
        holdings.append(
            {
                "ticker": _normalise_ticker(symbol, exchange),
                "exchange": exchange,
                "quantity": _extract_decimal(row.get("quantity") or row.get("units")),
                "avg_cost": _extract_decimal(row.get("avg_cost") or row.get("averagePrice"), "0"),
            }
        )
    return holdings


async def get_watchlist() -> list[dict[str, str]]:
    client = await _build_client()
    raw_watchlist = await _call_first(client, ("get_watchlist", "watchlist"))
    rows = raw_watchlist.get("watchlist", raw_watchlist) if isinstance(raw_watchlist, dict) else raw_watchlist
    watchlist: list[dict[str, str]] = []
    for row in rows or []:
        symbol = row.get("ticker") or row.get("symbol")
        if not symbol:
            continue
        exchange = _normalise_exchange(row.get("exchange") or row.get("market"))
        watchlist.append({"ticker": _normalise_ticker(symbol, exchange), "exchange": exchange})
    return watchlist
