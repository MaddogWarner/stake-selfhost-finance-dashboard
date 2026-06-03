"""Thin wrapper over the unofficial ``stake`` library (stake==0.13.0).

Verified against the 0.13.0 public API:
- ``stake.StakeClient(request, exchange=stake.NYSE | stake.ASX)`` is an async
  context manager that logs in on ``__aenter__``.
- ``stake.SessionTokenLoginRequest(token=...)`` authenticates with a session token.
- ``session.equities.list()`` -> ``EquityPositions(equity_positions=[EquityPosition(...)])``
  where each position has ``symbol``, ``open_qty`` and ``average_price``.
- ``session.watchlist.list_watchlists()`` -> ``list[Watchlist]`` each with ``instruments``.

The exchange is fixed per client (set at construction), so we open one session per
exchange and tag the rows from the session context. Per-exchange failures are tolerated
(e.g. a US-only account has no ASX data); we only raise if *every* exchange fails, which
is how an invalid/expired token surfaces.
"""

import logging
from decimal import Decimal
from typing import Any

from app.config import settings
from app.services.stake_service import get_cached_token
from app.utils.tickers import normalise_ticker

logger = logging.getLogger(__name__)


def _extract_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    return Decimal(str(value))


def _import_stake() -> Any:
    try:
        import stake  # type: ignore

        return stake
    except ImportError as exc:
        raise RuntimeError(f"stake-python is not installed: {exc}") from exc


def _require_token() -> str:
    token = get_cached_token() or settings.stake_session_token
    if not token:
        raise RuntimeError(
            "No Stake session token available. Connect Stake in the dashboard "
            "or set STAKE_SESSION_TOKEN."
        )
    return token


def _attr(obj: Any, *names: str) -> Any:
    """Read the first present attribute (or dict key) — defensive against shape drift."""
    for name in names:
        value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return None


def _exchange_targets(stake: Any) -> list[tuple[str, Any]]:
    """(label, exchange-constant) per exchange. NYSE is the library default, so we always
    attempt it (passing the constant when available); ASX is only attempted when its
    constant resolves, so we never override the default with ``exchange=None``."""
    targets: list[tuple[str, Any]] = [("NYSE", getattr(stake, "NYSE", None))]
    asx = getattr(stake, "ASX", None)
    if asx is not None:
        targets.append(("ASX", asx))
    return targets


def _client(stake: Any, request: Any, exchange: Any) -> Any:
    kwargs = {"exchange": exchange} if exchange is not None else {}
    return stake.StakeClient(request, **kwargs)


async def get_holdings() -> list[dict[str, Any]]:
    stake = _import_stake()
    request = stake.SessionTokenLoginRequest(token=_require_token())
    holdings: list[dict[str, Any]] = []
    errors: list[str] = []
    any_success = False

    for label, exchange in _exchange_targets(stake):
        try:
            async with _client(stake, request, exchange) as session:
                positions = await session.equities.list()
                any_success = True
                rows = _attr(positions, "equity_positions", "equityPositions") or []
                for row in rows:
                    symbol = _attr(row, "symbol", "ticker")
                    if not symbol:
                        continue
                    holdings.append(
                        {
                            "ticker": normalise_ticker(str(symbol), label),
                            "exchange": label,
                            "quantity": _extract_decimal(
                                _attr(row, "open_qty", "openQty", "quantity", "units")
                            ),
                            "avg_cost": _extract_decimal(
                                _attr(row, "average_price", "avgPrice", "averagePrice"), "0"
                            ),
                        }
                    )
        except Exception as exc:  # noqa: BLE001 - tolerate per-exchange failure
            errors.append(f"{label}: {exc}")
            logger.warning("Stake holdings fetch failed for %s: %s", label, exc)

    if not any_success:
        raise RuntimeError(
            "Stake sync failed — token may be invalid or expired. " + "; ".join(errors)
        )
    return holdings


async def get_watchlist() -> list[dict[str, str]]:
    stake = _import_stake()
    request = stake.SessionTokenLoginRequest(token=_require_token())
    watchlist: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    errors: list[str] = []
    any_success = False

    for label, exchange in _exchange_targets(stake):
        try:
            async with _client(stake, request, exchange) as session:
                lists = await session.watchlist.list_watchlists()
                any_success = True
                for wl in lists or []:
                    instruments = _attr(wl, "instruments") or []
                    if not instruments:
                        instruments = await _fetch_watchlist_instruments(stake, session, wl)
                    for inst in instruments:
                        symbol = _attr(inst, "symbol", "ticker")
                        if not symbol:
                            continue
                        key = (normalise_ticker(str(symbol), label), label)
                        if key in seen:
                            continue
                        seen.add(key)
                        watchlist.append({"ticker": key[0], "exchange": key[1]})
        except Exception as exc:  # noqa: BLE001 - tolerate per-exchange failure
            errors.append(f"{label}: {exc}")
            logger.warning("Stake watchlist fetch failed for %s: %s", label, exc)

    if not any_success:
        raise RuntimeError(
            "Stake sync failed — token may be invalid or expired. " + "; ".join(errors)
        )
    return watchlist


async def _fetch_watchlist_instruments(stake: Any, session: Any, wl: Any) -> list[Any]:
    """Best-effort detail fetch when ``list_watchlists`` returns no instruments."""
    request_cls = getattr(stake, "GetWatchlistRequest", None)
    wid = _attr(wl, "watchlist_id", "watchlistId", "id")
    if not (request_cls and wid):
        return []
    try:
        detail = await session.watchlist.watchlist(request_cls(watchlist_id=wid))
        return _attr(detail, "instruments") or []
    except Exception as exc:  # noqa: BLE001
        logger.debug("Stake watchlist detail fetch failed for %s: %s", wid, exc)
        return []


async def validate_token(token: str) -> bool:
    """Open a session with ``token`` and make one lightweight call. Raises on failure."""
    stake = _import_stake()
    request = stake.SessionTokenLoginRequest(token=token)
    async with _client(stake, request, getattr(stake, "NYSE", None)) as session:
        await session.equities.list()
    return True
