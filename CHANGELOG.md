# Changelog

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
