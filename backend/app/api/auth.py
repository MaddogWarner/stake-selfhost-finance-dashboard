from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, SecretStr
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.services.auth_service import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    check_session,
    create_session,
    destroy_session,
    get_password_hash,
    set_password,
    validate_password,
    verify_password,
)
from app.services.rate_limit_service import rate_limit

router = APIRouter()
AuthStatus = Literal["setup_required", "unauthenticated", "authenticated"]


class PasswordRequest(BaseModel):
    password: SecretStr


def _set_cookie(response: Response, token: str) -> None:
    # SameSite=Lax is the CSRF control for this single-origin, non-cross-site app.
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


@router.get("/auth/status")
async def status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _limit: None = Depends(rate_limit("global", 240, 60)),
) -> dict[str, AuthStatus]:
    if await get_password_hash(db) is None:
        return {"status": "setup_required"}
    if await check_session(redis, request.cookies.get(SESSION_COOKIE)):
        return {"status": "authenticated"}
    return {"status": "unauthenticated"}


@router.post("/auth/setup", dependencies=[Depends(rate_limit("auth_setup", 5, 60))])
async def setup(
    payload: PasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, AuthStatus]:
    password = payload.password.get_secret_value()
    try:
        validate_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not await set_password(db, password):
        raise HTTPException(status_code=409, detail="Setup has already been completed.")
    token = await create_session(redis)
    _set_cookie(response, token)
    return {"status": "authenticated"}


@router.post("/auth/login", dependencies=[Depends(rate_limit("auth_login", 5, 60))])
async def login(
    payload: PasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, AuthStatus]:
    password_hash = await get_password_hash(db)
    if password_hash is None:
        raise HTTPException(status_code=409, detail="Complete setup before logging in.")
    if not verify_password(payload.password.get_secret_value(), password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    token = await create_session(redis)
    _set_cookie(response, token)
    return {"status": "authenticated"}


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, redis: Redis = Depends(get_redis)
) -> dict[str, AuthStatus]:
    await destroy_session(redis, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax"
    )
    return {"status": "unauthenticated"}
