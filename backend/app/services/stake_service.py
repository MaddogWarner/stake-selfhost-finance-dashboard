from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.settings_service import get_stake_token, set_stake_token

logger = logging.getLogger(__name__)

_cached_token: str | None = None


def get_cached_token() -> str | None:
    return _cached_token


async def bootstrap_stake_token(db: AsyncSession) -> None:
    global _cached_token

    # Priority 1: env var (explicit user override)
    if settings.stake_session_token:
        _cached_token = settings.stake_session_token
        return

    # Priority 2: previously persisted token in DB
    stored = await get_stake_token(db)
    if stored:
        _cached_token = stored
        logger.info("Stake session token loaded from database.")
        return

    # Priority 3: exchange username/password for a token (bootstrap path)
    if not (settings.stake_username and settings.stake_password):
        logger.warning("No Stake credentials configured. Sync will fail until credentials are provided.")
        return

    logger.info("No session token found; authenticating with STAKE_USERNAME/STAKE_PASSWORD.")
    try:
        token = await asyncio.to_thread(_authenticate, settings.stake_username, settings.stake_password)
    except Exception as exc:
        logger.error("Stake authentication failed: %s", exc)
        return

    if not token:
        logger.error("Stake authentication succeeded but returned no session token.")
        return

    _cached_token = token
    await set_stake_token(db, token)

    # Best-effort: zero credentials from in-memory settings so they are not held longer than needed.
    # Pydantic v2 BaseSettings is frozen by default; bypass with object.__setattr__.
    try:
        object.__setattr__(settings, "stake_password", None)
        object.__setattr__(settings, "stake_username", None)
    except Exception:
        pass

    logger.warning(
        "Stake session token obtained and saved to database. "
        "Update your .env: set STAKE_SESSION_TOKEN=%s "
        "then remove STAKE_USERNAME and STAKE_PASSWORD.",
        token,
    )


def _authenticate(username: str, password: str) -> str | None:
    try:
        import stake  # type: ignore
    except ImportError as exc:
        raise RuntimeError("stake-python is not installed") from exc

    cls: Any = getattr(stake, "Stake", None) or getattr(stake, "StakeClient", None)
    if cls is None:
        raise RuntimeError("stake-python: could not find Stake or StakeClient class")

    client = cls(username=username, password=password)
    headers = getattr(client, "headers", None)
    token = getattr(headers, "stake_session_token", None) if headers else None
    return str(token) if token else None
