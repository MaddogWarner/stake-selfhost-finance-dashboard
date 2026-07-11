# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All Docker commands must be run from the `docker/` directory (compose files live there):

```bash
# Start full stack
cd docker && docker compose up --build

# Start with dev hot-reload (backend mounts source; start frontend separately)
cd docker && docker compose -f docker-compose.yml -f docker-compose.override.yml up backend db redis

# Frontend dev server (separate terminal, from frontend/)
cd frontend && npm run dev
```

Alembic migrations run from `backend/`:
```bash
cd backend

# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

The `alembic.ini` hardcodes the DB URL for local dev. When running inside Docker the backend applies migrations automatically on startup (verify this is wired in `main.py` lifespan).

## Versioning

The app version has one source of truth: `backend/app/version.py` (`__version__`). FastAPI reads it for `/docs`, `GET /api/version` exposes it, and the frontend footer fetches it at runtime. When bumping the version, edit only that file (plus CHANGELOG and git tag).

## Architecture

### Request flow
```
React/nginx (HTTPS 3443; HTTP 3000 redirects) → FastAPI (port 8000) → Redis (cache/sessions) → PostgreSQL (DB) → external APIs
```

All API routers follow a **cache-aside** pattern: check Redis → fall back to PostgreSQL → fall back to live API. Write-through on cache miss.

All data/admin API routers require the Redis-backed `stake_dash_session` cookie via `require_auth`. Auth status, version, health, docs, and OpenAPI remain public. Sessions have a fixed seven-day TTL.

### Backend layers
- `app/api/` — FastAPI routers; thin, delegate to services
- `app/services/` — business logic and external API clients
- `app/models/` — SQLAlchemy 2.0 ORM (`Mapped`/`mapped_column` style, `DeclarativeBase`)
- `app/schemas/` — Pydantic v2 request/response models
- `app/scheduler/` — APScheduler jobs registered in FastAPI `lifespan`
- `app/db/session.py` — `get_db()` async dependency; `app/db/redis.py` — `get_redis()` dependency

### Settings
`app/config.py` uses `pydantic-settings` `BaseSettings`. All config comes from `.env` (copy `.env.example` to `.env`). The `settings` singleton is module-level; use `get_settings()` in tests to override.

### FMP rate limiter
`services/rate_limiter.py` gates every FMP API call. The hard limit is `FMP_DAILY_LIMIT = 200` (free tier is 250; we keep a buffer). **Every FMP call must**:
1. `await can_call_fmp(db)` — raises or returns `False` if at limit
2. `await record_fmp_call(db)` — upserts today's count in `api_usage` table

Never add FMP calls that bypass this gate.

`services/rate_limit_service.py` is the inbound per-IP Redis limiter. It is distinct from `services/rate_limiter.py`, which protects the outbound FMP quota. Inbound limiting fails open if Redis is unavailable; authentication still fails closed.

### Stake token encryption

Persisted Stake tokens use the versioned `enc:v1:` Fernet format. The key comes from `TOKEN_ENCRYPTION_KEY` or `/data/fernet.key`; plaintext legacy rows are encrypted lazily on read. Initialise crypto before token bootstrap.

### Ticker normalisation (important)
Tickers are stored **without** exchange suffixes (e.g. `CBA`, not `CBA.AX`). The exchange is stored separately as `ASX` or `NYSE`. When calling yfinance, `services/yfinance_service.py` appends `.AX` for ASX tickers at call time. `services/stake_client.py` strips `.AX` on ingest.

The `stake_client._normalise_exchange()` function maps `AU`/`AUS` → `ASX`; everything else defaults to `NYSE`.

### Redis key convention
```
price:{ticker}          TTL 300s
fundamentals:{ticker}   TTL 86400s
profile:{ticker}        TTL 604800s
news:{ticker}           TTL 3600s
52w:{ticker}            TTL 3600s
```

### Stake client
`services/stake_client.py` wraps the unofficial `stake-python` library (reverse-engineered, may change). It uses the real `stake==0.13.0` async API: `async with stake.StakeClient(stake.SessionTokenLoginRequest(token=...), exchange=stake.NYSE|stake.ASX) as session`, then `await session.equities.list()` (holdings) and `await session.watchlist.list_watchlists()` (watchlist). Exchange is fixed per client, so it opens one session per exchange and tags rows from context; per-exchange failures are tolerated and it raises only if *every* exchange fails (how an invalid/expired token surfaces). Request-time dashboard login and credential bootstrap (`services/stake_service.py`) use `stake.CredentialsLoginRequest(username, password, otp=...)`; credentials/OTP are never persisted, and 2FA accounts need a live OTP. Auth priority for sync: cached DB-persisted token → `STAKE_SESSION_TOKEN` env var as first-run fallback → credential bootstrap. A pasted token via `POST /api/admin/stake-token` or credential login via `POST /api/admin/stake-login` is persisted to `app_settings` and takes priority on restart. Stake sync is optional; manual holdings/watchlist (source=`manual`) work without it and are never overwritten by sync. If the Stake API shape changes, fix the `_attr` field mappings in `get_holdings()`/`get_watchlist()`.

### Database
PostgreSQL 16. All tables are created by Alembic; do not use `Base.metadata.create_all()`. All models use `UniqueConstraint` on `(ticker, exchange)` so upserts use `ON CONFLICT DO UPDATE`. The `price_history` table stores bare tickers (no `.AX`).

## Frontend
React 18 + Vite + TailwindCSS + Recharts. API base URL comes from `VITE_API_URL` build arg (defaults to `http://localhost:8000`). The nginx container in production proxies `/api` to the backend, so the frontend uses relative `/api` paths in production builds.

## Key external dependencies
- `stake==0.13.0` — unofficial, asyncio-based; may break on Stake API changes
- `yfinance==0.2.50` — unofficial; uses `requests-cache` (SQLite at `/tmp/yfinance.sqlite`, 1h TTL) to avoid throttling
- FMP free tier: 250 calls/day; gated at 200 via `rate_limiter.py`
