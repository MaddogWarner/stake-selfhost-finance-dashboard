# Stake Investment Dashboard

A self-hosted investment dashboard. Track stocks two ways: add holdings and watchlist tickers yourself, or optionally sync them live from [Stake AU](https://hellostake.com/au). Either way they're enriched with price history, fundamentals, and news from Yahoo Finance and Financial Modeling Prep (FMP), and displayed as a card-based feed with ASX, S&P/US, and All market tabs.

Read-only — no trade placement.

---

## Features

- Manual holdings and watchlist tracking — add/edit/delete tickers from the dashboard (no broker login needed)
- Optional live holdings and watchlist sync from Stake AU (dashboard credential login, or fallback session-token paste)
- 30-day price sparkline per card with daily change
- 52-week high/low signals (computed from full 1-year history)
- 50-day moving average signals (computed server-side)
- Company fundamentals: P/E ratio, market cap, sector
- Latest news headlines per ticker (cached 1 hour)
- Runtime data source selector — switch between FMP, Yahoo Finance, or both from the dashboard header without restarting Docker
- Configurable auto-refresh (off / 1 / 2 / 5 min) plus a manual refresh button with success confirmation
- Market open/closed badge per exchange (DST-aware)
- FMP daily call gate (hard limit: 200 calls/day); use Yahoo Finance mode to run with zero FMP quota
- Redis caching throughout; PostgreSQL persistence

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose **v2.24 or later** (the compose files use the optional-`.env` syntax added in 2.24 — check with `docker compose version`)
- A [Stake AU](https://hellostake.com/au) account
- A free [Financial Modeling Prep](https://financialmodelingprep.com) API key (250 calls/day on the free tier) — optional if you run in Yahoo Finance mode

---

## Credentials

### Stake sync is optional

You don't need a Stake account to use the dashboard. Click **Manage** in the header to add holdings (ticker, exchange, quantity, average cost) and watchlist tickers by hand. This is the reliable default and never depends on Stake.

If you do want to auto-sync from Stake AU, the dashboard uses the unofficial `stake-python` library. The dashboard can exchange your username, password, and current 2FA code for a session token at request time. Credentials are never stored; only the resulting session token is persisted.

**Recommended — log in from the dashboard:**

1. Click **Connect Stake** in the dashboard header.
2. Enter your Stake username and password.
3. Enter the current 2FA code if your account has 2FA enabled.
4. Click **Connect**. The app stores only the returned session token.
5. Click **Sync** to pull holdings and watchlist.

**Fallback — paste a token manually:** open **Connect Stake** and expand **Or paste a session token manually**.

1. Log in to [trading.hellostake.com](https://trading.hellostake.com) in your browser.
2. Open DevTools (F12) → **Network** tab, then click around the app (e.g. open your portfolio/watchlist) so requests appear.
3. Click any request to `api2.prd.hellostake.com` and find the **`Stake-Session-Token`** entry under **Request Headers** (it's a request header, not a cookie).
4. Copy its value, paste it into the fallback form, and click **Connect**. The token is validated against Stake and persisted to the database.
5. Click **Sync** to pull holdings and watchlist.

**Alternative — set it in `.env`:** put the token in `STAKE_SESSION_TOKEN` for first-run convenience. Once a token is saved in the database, the database token takes priority and a stale `.env` value is ignored on restart.

**Bootstrap with username/password (one-time, advanced):** set `STAKE_USERNAME`, `STAKE_PASSWORD`, and — if your account has 2FA — a *current* `STAKE_OTP` code, leaving `STAKE_SESSION_TOKEN` blank. On startup the app exchanges these for a session token and persists it. Because the OTP is short-lived this only works at the moment a fresh code is supplied; the dashboard login flow above is simpler.

**Session token expiry:** Stake tokens are valid for ~30 days. The dashboard warns when a saved token is approaching expiry or has failed sync. When that happens, repeat the dashboard login flow or paste a fresh token manually. Your manually added holdings/watchlist are never affected by Stake sync.

### FMP API key (optional)

FMP is only used for **fundamentals** (company profile + TTM P/E), and only when the data source is set to an FMP mode. The app uses FMP's current **`stable`** API (the legacy `/api/v3` endpoints were retired in 2026). If FMP is unavailable — no key, daily quota reached, or your plan doesn't include an endpoint — it **falls back to Yahoo Finance automatically**, so fundamentals always render.

Sign up at [financialmodelingprep.com](https://financialmodelingprep.com) and copy your key; the app gates itself at 200 calls/day. **News and prices never use FMP** (FMP news is a paid add-on) — they always come from Yahoo Finance. Leave the key unset to run entirely on Yahoo Finance.

---

## Setup

```bash
# Clone or download the project
cd "Stake dashboard"

# Optional: copy the environment template if you want to configure FMP or Stake
cp .env.example .env
```

Edit `.env`:

```env
# Optional — only needed for Stake auto-sync. The dashboard's "Connect Stake"
# login flow is preferred. Leave blank to use manual tracking only.
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
- HTTP and HTTPS are published on `127.0.0.1:3000` and `127.0.0.1:3443`; HTTP redirects to HTTPS. For LAN use, set `FRONTEND_HTTP_BIND` and `FRONTEND_HTTPS_BIND`. If the HTTPS host port changes, set `HTTPS_PORT` to the same port so redirects remain correct.
- Images are published publicly by CI; if you make the packages private, run `docker login ghcr.io` first.
- Update to a new release: `TAG=<version> docker compose -f docker-compose.ghcr.yml pull && ... up -d`.

### Option B — Build from source

```bash
cd docker
docker compose up --build
```

Open <https://localhost:3443>. The first visit displays the one-time password setup wizard. The certificate is self-signed, so accept the warning: Chrome **Advanced → Proceed**, Firefox **Advanced → Accept the Risk and Continue**, or Safari **Show Details → visit this website**. <http://localhost:3000> redirects to HTTPS. The development API remains at <http://localhost:8000> and its `/docs` schema is public.

## Security

**Do not expose this dashboard directly to the internet.** It is designed for localhost, a trusted LAN, or a private VPN such as Tailscale. The Stake session token grants access to a live brokerage account.

- Complete the setup wizard immediately after first start. Until setup is complete, the first person who can reach the published port can choose the admin password. The default loopback binds mean only the local host can do so.
- Sessions are revocable, Redis-backed cookies with a fixed seven-day lifetime. Login and sensitive Stake connection endpoints are rate limited; repeated login attempts can lock that source address out for up to one minute.
- The generated TLS certificate persists in the `certs` volume. To use a trusted certificate, replace `server.crt` and `server.key` in that volume with your own files and restart the frontend.
- Stake tokens are encrypted in PostgreSQL. The Fernet key is supplied through `TOKEN_ENCRYPTION_KEY` or generated into the backend `/data` volume. Because that key is on the same host as the database, this protects database dumps, backups, and direct database access—not a fully compromised host.
- To reset the password from the host, run `docker compose exec backend python -m app.reset_admin_password` from `docker/`. This invalidates all sessions and reopens the setup wizard; there is intentionally no HTTP reset endpoint.

### Initial data load

Add tickers via the **Manage** button in the header (no Stake needed), or — if you've connected Stake — trigger a sync to pull holdings and watchlist:

```bash
    curl -k -b cookies.txt -X POST https://localhost:3443/api/sync
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

The dashboard header contains a **Data source** dropdown that controls where **fundamentals** are fetched from. **News and price history always come from Yahoo Finance** regardless of this setting. The change takes effect immediately — no restart required — and switching flushes the fundamentals cache.

| Mode | Fundamentals | News & prices | FMP calls/day |
| ---- | ------------ | ------------- | ------------- |
| **Yahoo Finance Only** | Yahoo Finance | Yahoo Finance | 0 |
| **FMP + Yahoo Finance** (seeded default) | FMP, falls back to Yahoo | Yahoo Finance | Up to 200 |
| **FMP Only** | FMP, falls back to Yahoo | Yahoo Finance | Up to 200 |

FMP uses the current **`stable`** API and, with a valid key, returns the company profile and TTM P/E. If FMP can't be reached (no key, quota, or plan restriction) the dashboard falls back to Yahoo Finance automatically. **Yahoo Finance Only** needs no API key.

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
React/nginx (HTTPS 3443; HTTP 3000 redirects) → FastAPI (port 8000) → Redis → PostgreSQL → external APIs
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
Stake tokens expire (~30 days). Refresh via **Connect Stake** in the dashboard with your current credentials and 2FA code, or use the manual token fallback with the `Stake-Session-Token` request header (DevTools → Network → an `api2.prd.hellostake.com` request), not a cookie. `POST /api/sync` returns a clear error if the token is missing or invalid; your manually added tickers are unaffected. If you don't use Stake, add tickers via **Manage**.

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
