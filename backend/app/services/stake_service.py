from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.settings_service import get_stake_token, set_stake_token

logger = logging.getLogger(__name__)

_cached_token: str | None = None


def get_cached_token() -> str | None:
    return _cached_token


def set_cached_token(token: str | None) -> None:
    global _cached_token
    _cached_token = token


async def bootstrap_stake_token(db: AsyncSession) -> None:
    global _cached_token

    # Priority 1: previously persisted token in DB
    stored = await get_stake_token(db)
    if stored:
        _cached_token = stored
        if settings.stake_session_token:
            logger.info(
                "Stake session token loaded from database; ignoring STAKE_SESSION_TOKEN."
            )
        else:
            logger.info("Stake session token loaded from database.")
        return

    # Priority 2: env var as first-run convenience only
    if settings.stake_session_token:
        _cached_token = settings.stake_session_token
        logger.info("Stake session token loaded from STAKE_SESSION_TOKEN.")
        return

    # Priority 3: exchange username/password for a token (one-time bootstrap path).
    # NOTE: a 2FA account needs a *live* OTP here; the OTP is short-lived, so this only
    # works at the instant a fresh STAKE_OTP is supplied. The dashboard "Connect Stake"
    # paste-token flow is the primary path.
    if not (settings.stake_username and settings.stake_password):
        logger.warning(
            "No Stake credentials configured. Sync will fail until a token is provided."
        )
        return

    logger.info(
        "No session token found; authenticating with STAKE_USERNAME/STAKE_PASSWORD."
    )
    try:
        token = await authenticate(
            settings.stake_username, settings.stake_password, settings.stake_otp
        )
    except Exception as exc:  # noqa: BLE001 - third-party auth failures are non-fatal
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
        object.__setattr__(settings, "stake_otp", None)
    except (AttributeError, TypeError) as exc:
        logger.warning("Unable to clear Stake credentials from memory: %s", exc)

    logger.warning(
        "Stake session token obtained and saved. It is now persisted in the database; "
        "you can leave STAKE_USERNAME/STAKE_PASSWORD/STAKE_OTP unset."
    )


async def authenticate(
    username: str, password: str, otp: str | None = None
) -> str | None:
    try:
        import stake  # type: ignore
    except ImportError as exc:
        raise RuntimeError("stake-python is not installed") from exc

    request: Any = stake.CredentialsLoginRequest(
        username=username, password=password, otp=otp
    )
    async with stake.StakeClient(request) as session:
        headers = getattr(session, "headers", None)
        token = getattr(headers, "stake_session_token", None) if headers else None
    return str(token) if token else None
