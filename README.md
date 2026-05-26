# Stake Investment Dashboard

A self-hosted investment dashboard that pulls your live holdings and watchlist from [Stake AU](https://hellostake.com/au) and enriches them with price history, fundamentals, and news from Yahoo Finance and Financial Modeling Prep (FMP). Displayed as a card-based feed with ASX, S&P/US, and All market tabs.

Read-only — no trade placement.

---

## Features

- Live holdings and watchlist synced from Stake AU
- 30-day price sparkline per card with daily change
- 52-week high/low signals (computed from full 1-year history)
- 50-day moving average signals (computed server-side)
- Company fundamentals: P/E ratio, market cap, sector
- Latest news headlines per ticker (cached 1 hour)
- Runtime data source selector — switch between FMP, Yahoo Finance, or both from the dashboard header without restarting Docker
- Market open/closed badge per exchange (DST-aware)
- FMP daily call gate (hard limit: 200 calls/day); use Yahoo Finance mode to run with zero FMP quota
- Redis caching throughout; PostgreSQL persistence

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- A [Stake AU](https://hellostake.com/au) account
- A free [Financial Modeling Prep](https://financialmodelingprep.com) API key (250 calls/day on the free tier) — optional if you run in Yahoo Finance mode

---

## Credentials

### Stake session token

The dashboard uses the unofficial `stake-python` library and authenticates via a session token. There are two ways to provide it:

**Option A — Copy from browser (quickest):**

1. Log in to [hellostake.com/au](https://hellostake.com/au) in your browser
2. Open DevTools → Application → Cookies
3. Copy the value of the `Stake-Session-Token` cookie
4. Paste it into `.env` as `STAKE_SESSION_TOKEN=<value>`

**Option B — Bootstrap with username/password (first run only):**

Set `STAKE_USERNAME` and `STAKE_PASSWORD` in `.env` and leave `STAKE_SESSION_TOKEN` blank. On the first startup the app authenticates, saves the token to the database, and logs it:

```text
[WARNING] Stake session token obtained and saved to database.
          Update your .env: set STAKE_SESSION_TOKEN=<token>
          then remove STAKE_USERNAME and STAKE_PASSWORD.
```

Copy the logged token to `STAKE_SESSION_TOKEN`, then comment out or remove `STAKE_USERNAME` and `STAKE_PASSWORD`. The token is also stored in the database, so future restarts work even before you update `.env`.

**Session token expiry:** Stake tokens are valid for approximately 30 days. When one expires, repeat Option A or B to refresh it. The new token overwrites the old one in the database automatically.

### FMP API key

Sign up at [financialmodelingprep.com](https://financialmodelingprep.com) and copy your key from the dashboard. The free tier provides 250 calls/day; the app gates itself at 200 to keep a buffer. If you set the data source to **Yahoo Finance Only**, FMP is never called and the key is unused.

---

## Setup

```bash
# Clone or download the project
cd "Stake dashboard"

# Copy the environment template and fill in your credentials
cp .env.example .env
```

Edit `.env`:

```env
# Use session token (preferred) or username/password
STAKE_SESSION_TOKEN=your_token_here
# STAKE_USERNAME=your@email.com
# STAKE_PASSWORD=yourpassword

FMP_API_KEY=your_fmp_key_here

# Leave these as-is for Docker deployment
DATABASE_URL=postgresql+asyncpg://stake:stake@db:5432/stake_dashboard
REDIS_URL=redis://redis:6379/0
VITE_API_URL=http://localhost:8000
```

---

## Deploy (Docker)

All Docker Compose commands run from the `docker/` directory.

```bash
cd docker

# Build and start all four services
docker compose up --build
```

On first boot the backend automatically runs database migrations before starting the scheduler. Allow 30–60 seconds for all services to become healthy.

| Service   | URL                           |
| --------- | ----------------------------- |
| Dashboard | <http://localhost:3000>       |
| API       | <http://localhost:8000>       |
| API docs  | <http://localhost:8000/docs>  |

Both ports are bound to `127.0.0.1` only and are not accessible from other devices on your network.

### Initial data load

After the stack is up, trigger a manual Stake sync to populate holdings and watchlist:

```bash
curl -X POST http://localhost:8000/api/sync
```

Price data, fundamentals, and news will begin populating on the next scheduler run (prices refresh every 5 minutes during market hours; news every 2 hours).

### Stopping

```bash
docker compose down          # stop containers, keep data volumes
docker compose down -v       # stop and delete all data (full reset)
```

---

## Data refresh schedule

| Job | Frequency | Condition |
| --- | --------- | --------- |
| Stake sync | Every 15 min | Always |
| Prices | Every 5 min | Market hours only (ASX/NYSE) |
| Fundamentals | Daily at 06:00 UTC | New tickers only |
| News | Every 2 hours | Always |
| Financials | Weekly (Sunday) | Always |
| History pruning | Weekly (Saturday) | Removes data > 2 years old |

---

## Local development

For backend hot-reload, use the override compose file and run the frontend dev server separately:

```bash
# Terminal 1 — backend + infra with source mounted
cd docker
docker compose -f docker-compose.yml -f docker-compose.override.yml up backend db redis

# Terminal 2 — frontend dev server with HMR
cd frontend
npm install
npm run dev
```

Frontend is available at `http://localhost:5173` in dev mode.

### Alembic migrations

Run from `backend/`:

```bash
cd backend

# Generate a migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

---

## Data source

The dashboard header contains a **Data source** dropdown that controls where fundamentals and news are fetched from. The change takes effect immediately — no restart required. Switching sources flushes the Redis cache for fundamentals and news so cards refetch against the new source on the next load.

| Mode | Fundamentals & news | FMP calls/day |
| ---- | ------------------- | ------------- |
| **FMP + Yahoo Finance** (default) | FMP | Up to 200 |
| **FMP Only** | FMP | Up to 200 |
| **Yahoo Finance Only** | Yahoo Finance (yfinance) | 0 |

Prices and price history always come from Yahoo Finance regardless of this setting (FMP price endpoints cost quota).

The setting is stored in the database and persists across restarts. You can also read or update it via the API:

```bash
# Read current setting
curl http://localhost:8000/api/admin/settings

# Switch to Yahoo Finance only
curl -X POST http://localhost:8000/api/admin/settings \
  -H "Content-Type: application/json" \
  -d '{"data_source": "yfinance"}'

# Valid values: "both", "fmp", "yfinance"
```

---

## Architecture

```text
React (port 3000) → FastAPI (port 8000) → Redis (cache) → PostgreSQL → external APIs
```

Four Docker services:

| Service | Image | Purpose |
| ------- | ----- | ------- |
| `db` | postgres:16-alpine | Persistent storage |
| `redis` | redis:7-alpine | Cache (prices 5min, news 1h, fundamentals 24h) |
| `backend` | python:3.12-slim | FastAPI + APScheduler |
| `frontend` | nginx:alpine | React SPA served via nginx |

External data sources:

| Source | Used for | Rate limit |
| ------ | -------- | ---------- |
| Stake AU (unofficial) | Holdings, watchlist | Session-based |
| Yahoo Finance (yfinance) | Price history, live quotes | Unofficial; cached 1h |
| FMP free tier | Fundamentals, news | 250 calls/day (gated at 200) |

---

## Monitoring API usage

```bash
curl http://localhost:8000/api/admin/usage
```

Returns today's FMP call count, limit, and remaining calls.

---

## Troubleshooting

**No holdings/watchlist after sync**
Verify your Stake credentials in `.env`. The session token expires periodically — refresh it from your browser cookies.

**FMP data not loading**
Check `GET /api/admin/usage`. If today's count is at 200, data will resume the next calendar day (UTC).

**Duplicate news rows warning on startup**
If you ran the app before the news deduplication migration was applied, clean duplicates before running `alembic upgrade head`:

```sql
DELETE FROM news
WHERE id NOT IN (
    SELECT MIN(id) FROM news GROUP BY ticker, url
);
```

**Port already in use**
Change the host-side port in `docker/docker-compose.yml` (e.g. `127.0.0.1:8001:8000`) and update `VITE_API_URL` in `.env` to match.
