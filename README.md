# Stake Investment Dashboard

A self-hosted investment dashboard. Track stocks two ways: add holdings and watchlist tickers yourself, or optionally sync them live from [Stake AU](https://hellostake.com/au). Either way they're enriched with price history, fundamentals, and news from Yahoo Finance and Financial Modeling Prep (FMP), and displayed as a card-based feed with ASX, S&P/US, and All market tabs.

Read-only — no trade placement.

---

## Features

- Manual holdings and watchlist tracking — add/edit/delete tickers from the dashboard (no broker login needed)
- Optional live holdings and watchlist sync from Stake AU (paste a session token in the dashboard)
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

### Stake sync is optional

You don't need a Stake account to use the dashboard. Click **Manage** in the header to add holdings (ticker, exchange, quantity, average cost) and watchlist tickers by hand. This is the reliable default and never depends on Stake.

If you do want to auto-sync from Stake AU, the dashboard uses the unofficial `stake-python` library, which authenticates with a **session token**.

**Recommended — paste the token in the dashboard:**

1. Log in to [trading.hellostake.com](https://trading.hellostake.com) in your browser.
2. Open DevTools (F12) → **Network** tab, then click around the app (e.g. open your portfolio/watchlist) so requests appear.
3. Click any request to `api2.prd.hellostake.com` and find the **`Stake-Session-Token`** entry under **Request Headers** (it's a request header, not a cookie).
4. Copy its value, click **Connect Stake** in the dashboard header, paste it, and click **Connect**. The token is validated against Stake and persisted to the database.
5. Click **Sync** to pull holdings and watchlist.

**Alternative — set it in `.env`:** put the token in `STAKE_SESSION_TOKEN`. It's persisted to the database on first use, so subsequent restarts work even if you later blank it.

**Bootstrap with username/password (one-time, advanced):** set `STAKE_USERNAME`, `STAKE_PASSWORD`, and — if your account has 2FA — a *current* `STAKE_OTP` code, leaving `STAKE_SESSION_TOKEN` blank. On startup the app exchanges these for a session token and persists it. Because the OTP is short-lived this only works at the moment a fresh code is supplied; the paste-token flow above is simpler.

**Session token expiry:** Stake tokens are valid for ~30 days. When one expires, repeat the paste-token flow to refresh it — the new token overwrites the old one automatically. Your manually added holdings/watchlist are never affected by Stake sync.

### FMP API key (optional)

> **Note:** FMP has retired its legacy v3 endpoints; free-tier and older keys now return `403 Legacy Endpoint`. Unless you have a current FMP plan, leave this unset and use **Yahoo Finance Only** — the recommended data source for fundamentals and news (see [Data source](#data-source)).

Sign up at [financialmodelingprep.com](https://financialmodelingprep.com) and copy your key. The free tier historically provided 250 calls/day; the app gates itself at 200 to keep a buffer. With the data source set to **Yahoo Finance Only**, FMP is never called and the key is unused.

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
# Optional — only needed for Stake auto-sync. You can also paste the token via the
# dashboard's "Connect Stake" button instead of setting it here. Leave blank to use
# manual tracking only.
STAKE_SESSION_TOKEN=
# One-time bootstrap alternative (advanced). STAKE_OTP is your current 2FA code, if enabled.
# STAKE_USERNAME=your@email.com
# STAKE_PASSWORD=yourpassword
# STAKE_OTP=

FMP_API_KEY=your_fmp_key_here

# Leave these as-is for Docker deployment
DATABASE_URL=postgresql+asyncpg://stake:stake@db:5432/stake_dashboard
REDIS_URL=redis://redis:6379/0
VITE_API_URL=http://localhost:8000
```

---

## Deploy (Docker)

Two options. Both run Postgres, Redis, the FastAPI backend, and the React frontend (which serves the UI and proxies `/api` to the backend). The backend runs database migrations automatically on first boot — allow 30–60 seconds for everything to settle. All Compose commands run from the `docker/` directory.

### Option A — Prebuilt images from GHCR (recommended)

No local build; pulls multi-arch images (`linux/amd64`, `linux/arm64`) from GitHub Container Registry.

```bash
git clone https://github.com/MaddogWarner/stake-selfhost-finance-dashboard.git
cd stake-selfhost-finance-dashboard
cp .env.example .env            # optional: add FMP/Stake creds (see Credentials)

cd docker
TAG=0.2.0 docker compose -f docker-compose.ghcr.yml up -d
```

- Pin a release with `TAG` (e.g. `0.2.0`), or omit it to use `latest`.
- Only the frontend port is published — `127.0.0.1:3000` by default. Expose it on your LAN with `FRONTEND_BIND`, e.g. `FRONTEND_BIND=192.168.1.150:3000 TAG=0.2.0 docker compose -f docker-compose.ghcr.yml up -d`. The backend is reachable only inside the Compose network, via the frontend's `/api` proxy.
- Images are published publicly by CI; if you make the packages private, run `docker login ghcr.io` first.
- Update to a new release: `TAG=<version> docker compose -f docker-compose.ghcr.yml pull && ... up -d`.

### Option B — Build from source

```bash
cd docker
docker compose up --build
```

Serves the dashboard at <http://localhost:3000>, the API at <http://localhost:8000> (and docs at `/docs`), both bound to `127.0.0.1` only.

### Initial data load

Add tickers via the **Manage** button in the header (no Stake needed), or — if you've connected Stake — trigger a sync to pull holdings and watchlist:

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

> **Recommended: Yahoo Finance Only.** FMP retired its legacy v3 endpoints, so the **FMP** and **FMP + Yahoo Finance** modes return errors unless you have a current FMP plan. New installs seed **FMP + Yahoo Finance**; switch to **Yahoo Finance Only** (one click, or via the API below) for working fundamentals and news with no API key.

| Mode | Fundamentals & news | FMP calls/day |
| ---- | ------------------- | ------------- |
| **Yahoo Finance Only** (recommended) | Yahoo Finance (yfinance) | 0 |
| **FMP + Yahoo Finance** (seeded default) | FMP (needs current plan) | Up to 200 |
| **FMP Only** | FMP (needs current plan) | Up to 200 |

Prices and price history always come from Yahoo Finance regardless of this setting.

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
Stake tokens expire (~30 days). Refresh it via **Connect Stake** in the dashboard — copy the `Stake-Session-Token` request header (DevTools → Network → an `api2.prd.hellostake.com` request), not a cookie. `POST /api/sync` returns a clear error if the token is missing or invalid; your manually added tickers are unaffected. If you don't use Stake, add tickers via **Manage**.

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
