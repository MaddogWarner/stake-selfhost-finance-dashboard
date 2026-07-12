# Changelog

## 2026-07-12 — v0.5.1

### Admin password policy

- Admin passwords now require a minimum of 12 characters with at least one number and one special character, enforced server-side and mirrored in the setup wizard with matching messages. Existing passwords are unaffected until reset.
- App version → `0.5.1`.

## 2026-07-11 — v0.5.0

### Security hardening

- Added HTTPS-by-default nginx termination on `https://localhost:3443`, persistent first-run self-signed certificates, and an HTTP 301 redirect on port 3000.
- Added a one-time admin setup wizard, bcrypt password storage, Redis-backed seven-day sessions, protected API routers, login/logout UI, and host-only password reset.
- Added versioned Fernet encryption for persisted Stake tokens, first-run key generation in a persistent backend volume, legacy plaintext migration, and safe key-loss handling.
- Added Redis fixed-window limits for login, setup, Stake credential/token submission, and a global API backstop. Rate limiting fails open if Redis is unavailable while authentication remains fail closed.
- Updated deployment and security guidance, including the setup race, trusted-certificate replacement, and the limits of same-host key custody.
- App version → `0.5.0`.

## 2026-07-10 — v0.4.1

### Footer version display

- Added a single source of truth for the app version: `backend/app/version.py` (`__version__`). FastAPI now reads its version from there instead of a hardcoded string.
- Added `GET /api/version` (under `/api` so the production nginx proxy forwards it).
- Added a dashboard footer that fetches and displays the running version (e.g. "Stake Dashboard v0.4.1"); degrades to plain "Stake Dashboard" if the backend is unreachable.
- Documented the bump procedure in `CLAUDE.md` — edit `version.py` only, plus CHANGELOG and git tag.
- App version → `0.4.1`.

## 2026-07-08 — v0.4.0

### Stake auth lifecycle

- Added request-time Stake credential login via `POST /api/admin/stake-login`. Username, password, and OTP are used only for the login call; only the returned session token is persisted.
- Changed token bootstrap priority so a DB-persisted token wins over a stale `STAKE_SESSION_TOKEN` env value on restart, with an info log when the env value is ignored.
- Added token health metadata in `app_settings` (`stake_token_saved_at`, `stake_token_invalid`) and surfaced `token_state` through `/api/admin/stake-status`.
- Marked tokens invalid when Stake sync fails across all exchanges, without clearing the cached token.
- Updated the Connect Stake modal to make credential login primary, keep the DevTools token paste flow as a fallback, and show expiring/expired states plus a dashboard warning banner.
- App version → `0.4.0`.

## 2026-06-04 — v0.3.0

### Dashboard refresh controls + P/E formatting

- **Configurable auto-refresh.** The price refetch interval is no longer hardcoded at 5 minutes. New header control (`components/RefreshControls.tsx`) lets you pick **Off / 1 min / 2 min / 5 min**; the choice is held in a small React context (`hooks/useRefresh.tsx`) that `usePrices` reads for its `refetchInterval`. Defaults to 5 minutes to match the backend price cache TTL. Auto-refresh drives **prices only** — fundamentals are left alone to protect the FMP daily quota.
- **Manual refresh button.** Invalidates the price and news queries on demand, shows a "Refreshing" state while in flight, and surfaces a transient **"Refresh successful"** tile (auto-dismisses after 3s) once the refetch resolves. The confirmation appears only on a manual click, not on the auto-refresh interval.
- **P/E ratio formatting fix.** Card P/E was rendering the raw value (e.g. `32.67539924692…`) and overflowing its tile. Now formatted to 2 decimals via a `formatPe` helper that parses the `number | string` value and guards against null/NaN (`components/FeedCard.tsx`).
- App version → `0.3.0`.

## 2026-06-04 — v0.2.1

### FMP migrated to the new "stable" API

- FMP retired its legacy `/api/v3` endpoints (now `403 Legacy Endpoint`). Rewrote `services/fmp_service.py` to FMP's current **`stable`** API (`/stable/profile`, `/stable/ratios-ttm`, symbol passed as a query param) with the new field names (`marketCap`, `priceToEarningsRatioTTM`).
- Fundamentals now **fall back to Yahoo Finance automatically** when FMP is unavailable (no key, daily quota reached, or plan restriction), so cards always render.
- **News always uses Yahoo Finance.** FMP news is a paid add-on (`402 Restricted` on standard plans), so the data-source toggle now controls **fundamentals only**; removed the FMP news path from the API (`api/news.py`) and scheduler (`scheduler/jobs.py`).
- Dropped the unused FMP income-statement call from the financials job (saves one FMP call per ticker per refresh).
- App version → `0.2.1`.

## 2026-06-03 — v0.2.0

Adds manual stock tracking as the reliable core, fixes the Stake integration, and
restores live market telemetry (yfinance) that had broken against upstream API changes.

### Manual stock tracking (new core)

- Users can now add/edit/delete holdings (ticker, exchange, quantity, average cost) and watchlist tickers directly from the dashboard — no broker login required. This is the reliable default; Stake sync is now optional and layered on top.
- New CRUD endpoints in `backend/app/api/holdings.py`: `POST/PATCH/DELETE /api/holdings`, `POST/DELETE /api/watchlist`. Added `HoldingCreate`/`HoldingUpdate`/`WatchlistCreate` schemas.
- Added a `source` column (`manual`/`stake`) to the `holdings` and `watchlist` tables (migration `0004_manual_source`) so manual entries are visually distinguished and never wiped by a Stake sync.
- Extracted ticker/exchange normalisation into `backend/app/utils/tickers.py`, shared by the Stake sync and manual paths.
- Frontend: new **Manage** modal (`ManageAssets`) for CRUD, new **Connect Stake** modal (`StakeConnect`) for pasting a session token, plus a shared `Modal` and `errorMessage` helper. CORS now allows `PATCH`/`DELETE`.

### Stake integration fix

- Root cause: the integration called the `stake==0.13.0` library with an API shape that does not exist (`stake.Stake(session_token=...)`, `cls(username=..., password=...)`, `get_holdings()`/`portfolio()`), so both session-token and credential login always failed. The library was also installed `--no-deps` without its runtime deps, so `import stake` failed outright — now `aiohttp`, `inflection` and `single-version` are pinned in `requirements.txt`.
- Rewrote `services/stake_client.py` to the real async API: `async with StakeClient(SessionTokenLoginRequest(token=...), exchange=stake.NYSE|stake.ASX)`, reading `session.equities.list()` and `session.watchlist.list_watchlists()`. One session per exchange; per-exchange failures tolerated, raising only if every exchange fails (how an invalid token surfaces).
- Rewrote credential bootstrap in `services/stake_service.py` to `CredentialsLoginRequest(username, password, otp=...)` (2FA accounts need a live OTP — new `STAKE_OTP` setting). Stopped logging the raw token.
- Added in-dashboard token onboarding: `POST /api/admin/stake-token` (validates against Stake before persisting) and `GET /api/admin/stake-status`.
- `POST /api/sync` now returns a clear `400` when Stake isn't configured/valid instead of a `500`; manual data is untouched.
- Corrected docs: the `Stake-Session-Token` is a **request header** on `api2.prd.hellostake.com` (not a cookie).

### Market data / telemetry fixes

- Upgraded `yfinance` `0.2.50` → `1.4.1`. The pinned `0.2.50` no longer worked against Yahoo's current API and returned empty responses for every ticker (no prices, fundamentals or news).
- Fixed the live quote: yfinance 1.x exposes camelCase `fast_info` keys (`lastPrice`/`previousClose`); the code read snake_case and returned `None`.
- Fixed a price-endpoint hang under load: switched `get_price_history` from `yf.download()` (which spawns an internal thread pool that wedged the device when many cards fetched at once) to single-fetch `Ticker.history()`; the scheduler's batch download now runs with `threads=False`.
- Removed the global `requests_cache` install — yfinance 1.x uses `curl_cffi`, which it does not affect; app-level caching remains in Redis.
- **FMP**: Financial Modeling Prep retired its legacy v3 endpoints (now returns `403 Legacy Endpoint`). Yahoo Finance is now the recommended data source for fundamentals and news; the runtime data-source toggle still exists for users with a current FMP plan.

### Deployment

- Added `docker/docker-compose.ghcr.yml` to run prebuilt GHCR images without building locally; documented deployment in `README.md`.
- Fixed the frontend `VITE_API_URL` build arg: it now defaults to empty so the app uses relative `/api` via the bundled nginx proxy (the previous `http://localhost:8000` was baked into the bundle and broke remote/LAN access). Applied to `docker-compose.yml` and the publish workflow.
- `publish.yml`: the frontend image now also gets the full `{{version}}` tag (e.g. `0.2.0`), matching the backend.
- Added `version="0.2.0"` to the FastAPI app (shown at `/docs`).

## 2026-05-27 — v0.1.0

### Release

- Tagged and published `v0.1.0` as the first public release.
- Created GitHub release with multi-platform Docker images (`linux/amd64`, `linux/arm64`) published to GHCR:
  - `ghcr.io/maddogwarner/stake-selfhost-finance-dashboard/backend:0.1.0`
  - `ghcr.io/maddogwarner/stake-selfhost-finance-dashboard/frontend:0.1.0`

### Build Fix — pip Dependency Conflict

- `stake==0.13.0` requires `python-dotenv<0.14.0`; `pydantic-settings==2.6.1` requires `python-dotenv>=0.21.0` — these are irreconcilable when pip resolves both together.
- Fix: removed `stake==0.13.0` from `requirements.txt` and added a separate `pip install --no-deps stake==0.13.0` step in `backend/Dockerfile`. `--no-deps` bypasses stake's python-dotenv pin; env loading is handled entirely by pydantic-settings so stake's dotenv dependency is unused at runtime.

## 2026-05-27

### GitHub Actions — GHCR Publish Workflow

- Added `.github/workflows/publish.yml`: builds and publishes backend and frontend Docker images to GitHub Container Registry (`ghcr.io/maddogwarner/stake-selfhost-finance-dashboard/backend` and `.../frontend`).
- Two parallel jobs run on push to `main`, push of `v*.*.*` tags, and manual `workflow_dispatch`.
- Multi-platform builds: `linux/amd64` and `linux/arm64`.
- Tags: `latest` (main branch), semver (`1.2`, `1`) on version tags, short SHA on every push.
- Frontend `VITE_API_URL` defaults to `http://localhost:8000`; overridable via `workflow_dispatch` input for deployments to remote hosts.
- GHA layer caching scoped per image to maximise cache hit rate.
- Uses `GITHUB_TOKEN` for registry auth — no additional secrets required.

### Credential Security — Session Token Bootstrap

- Added `backend/app/services/stake_service.py` with a startup bootstrap flow: if no session token is configured, the app authenticates with `STAKE_USERNAME`/`STAKE_PASSWORD`, extracts the session token from `client.headers.stake_session_token`, persists it to the `app_settings` DB table, caches it in a module-level variable, and zeros the credentials from memory.
- Updated `backend/app/main.py` lifespan to call `bootstrap_stake_token(db)` after migrations, before the scheduler starts.
- Updated `stake_client._build_client()` to use the bootstrapped cached token; the username/password auth branch is removed — credentials are no longer passed to the Stake library directly.
- Added `get_stake_token()` and `set_stake_token()` to `settings_service.py` using the existing `app_settings` table.
- Updated `.env.example`: `STAKE_USERNAME`/`STAKE_PASSWORD` are now commented out as bootstrap-only fields with explanatory comments.
- Updated `README.md` credentials section to document the two auth options (browser cookie copy vs. username/password bootstrap) and the session token rotation process.
- Added `scripts/rotate-token.sh`: updates `STAKE_SESSION_TOKEN` in `.env` and comments out `STAKE_USERNAME`/`STAKE_PASSWORD` in one step.

## 2026-05-26

### Data Source Selector

- Added yfinance-backed fundamentals and news fetchers while keeping `yfinance==0.2.50` as the pinned PyPI dependency.
- Added the `app_settings` model and migration `0003_app_settings`, seeding `data_source = 'both'`.
- Added Redis-cached settings helpers for reading and updating the active data source.
- Added `GET /api/admin/settings` and `POST /api/admin/settings` endpoints with validation for `both`, `fmp`, and `yfinance`.
- Flushes `fundamentals:*` and `news:*` Redis cache entries when the data source changes so cards refetch against the selected source.
- Updated fundamentals and news API routes to use the active source setting after Redis cache misses.
- Updated scheduled fundamentals and news refresh jobs to respect the active source setting.
- Updated the weekly financial refresh job to skip FMP-only calls when the active data source is `yfinance`.
- Added frontend settings API calls, React Query hooks, `DataSource` and `AppSettings` types, and an inline Dashboard settings dropdown.

### Data Source Selector Validation

- Passed Python syntax compilation for `backend/app` and `backend/alembic` using a writable pycache prefix.
- Passed `npm run build` for the React frontend.
- Confirmed `npm audit --omit=dev` reports zero production vulnerabilities.
- Confirmed `requirements.txt` still pins `yfinance==0.2.50`; no yfinance source repo was cloned or vendored.

### Data Source Selector Known Follow-Ups

- Full Docker Compose validation was not run because Docker is not installed in this environment.
- Live verification of FMP quota behaviour, yfinance fundamentals/news results, and scheduler behaviour requires running Postgres/Redis/FastAPI with valid local `.env` values.

### Claude Review Fixes

- Added migration `0002_news_unique_ticker_url` and model constraint to prevent duplicate news rows for the same ticker and URL.
- Changed scheduled and on-demand news inserts to PostgreSQL upserts using `ON CONFLICT DO NOTHING`.
- Added FMP rate-limit handling in scheduled fundamentals, news, and financial refresh jobs so HTTP 429 stops further quota use while preserving work already staged.
- Added automatic Alembic `upgrade head` execution during FastAPI startup before scheduler registration.
- Replaced fixed UTC market-status windows with timezone-aware `Intl.DateTimeFormat` checks for Sydney and New York daylight saving changes.
- Added `week52_high`, `week52_low`, and backend-computed `moving_average_50` fields to price responses.
- Updated FeedCard 52-week signals to use full-year backend range fields and 50MA signals to render only when a real 50-day average is available.
- Bound backend and frontend Docker ports to `127.0.0.1` only.
- Updated the backend Docker image to run the app as a non-root user.
- Removed the hardcoded database URL from `alembic.ini`; Alembic now relies on `env.py` and runtime settings.
- Tightened CORS to `GET`/`POST` and `Content-Type`.
- Moved yfinance `requests-cache` installation out of module import time and into FastAPI lifespan startup.
- Replaced ad hoc awaitable detection in the Stake client with `inspect.isawaitable()`.
- Made the news endpoint `exchange` query parameter optional because it is not used in lookup logic.

### Review Fix Validation

- Passed Python syntax compilation for `backend/app` and `backend/alembic` using a writable pycache prefix.
- Passed `npm run build` for the React frontend.
- Confirmed `npm audit --omit=dev` reports zero production vulnerabilities.

### Review Fix Known Follow-Ups

- Full Docker Compose validation was not run because Docker is not installed in this environment.
- If a populated database already contains duplicate `news` rows for the same `(ticker, url)`, clean those duplicates before applying migration `0002_news_unique_ticker_url`.
- Live Stake sync, Redis TTL verification, yfinance quote retrieval, and FMP scheduler behaviour still require valid local `.env` credentials and running services.

### Initial Build

- Created the initial Docker Compose scaffold for PostgreSQL, Redis, FastAPI backend, and nginx-served React frontend.
- Added backend configuration, async SQLAlchemy session handling, Redis client setup, Alembic configuration, and the initial database migration.
- Implemented SQLAlchemy models for holdings, watchlist items, company profiles, price history, news, and API usage.
- Added read-only Stake sync plumbing, yfinance price/history enrichment, FMP profile/financial/news enrichment, and a hard 200-call daily FMP gate.
- Added API routers for health, holdings, watchlist, sync, prices, fundamentals, news, and admin usage.
- Added APScheduler jobs for Stake sync, market-hours-aware price refresh, fundamentals refresh, news refresh, weekly financial refresh, and price-history pruning.
- Built the React dashboard with ASX, S&P / US, and All market tabs, holdings/watchlist filters, market status badges, feed cards, sparklines, signals, news, and API usage display.
- Added frontend API modules, React Query hooks, shared TypeScript types, Tailwind configuration, Vite configuration, and nginx SPA proxy configuration.
- Added `.env.example` and `.gitignore` entries to keep runtime credentials, local dependencies, build artefacts, SQLite cache files, and Python cache files out of source control.

### Validation

- Passed Python syntax compilation for `backend/app` and `backend/alembic` using a writable pycache prefix.
- Installed frontend dependencies and generated `frontend/package-lock.json`.
- Passed `npm run build` for the React frontend.
- Confirmed `npm audit --omit=dev` reports zero production vulnerabilities.

### Known Follow-Ups

- Full Docker Compose validation was not run because Docker is not installed in this environment.
- Live Stake sync, yfinance quote retrieval, Redis cache TTL verification, and FMP-backed endpoints require a populated local `.env` with valid credentials and running services.
- Full `npm audit` reports two moderate dev-server vulnerabilities via Vite/esbuild; the available automated fix requires a breaking Vite major-version upgrade, so it was not applied during this pinned-version build.
