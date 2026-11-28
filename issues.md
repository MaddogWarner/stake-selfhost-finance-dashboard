# Known Issues / Minor Technical Debt

## Docker — source files owned by root inside container

**File:** `backend/Dockerfile`

`COPY . .` runs before the `USER appuser` switch, so all source files inside the container are root-owned. The app runs as `appuser` and only reads those files at runtime, and `/tmp` (used for the yfinance SQLite cache) is world-writable, so this causes no runtime problems today.

If the app ever needs to write inside `/app` at runtime, change the COPY instruction to:

```dockerfile
COPY --chown=appuser:appgroup . .
```

## News API — omitted exchange defaults to NYSE in yfinance mode

**File:** `backend/app/api/news.py`

When `GET /api/news/{ticker}` is called without an `exchange` query parameter and the active data source is `yfinance`, the endpoint defaults to `NYSE`. For ASX tickers, this means `normalise_ticker("CBA", "NYSE")` does not append `.AX`, so a direct request such as `GET /api/news/CBA` may query the wrong Yahoo Finance symbol.

The frontend always sends `exchange`, so normal dashboard use is unaffected.

Possible future fixes:

- require `exchange` again for the news endpoint
- infer exchange from holdings/watchlist before calling yfinance
- add an explicit fallback for known ASX tickers

## Price, profile and news tables are keyed by ticker only

**Files:** `backend/app/models/price_history.py`, `company_profile.py`, `news.py`

Redis cache keys include the exchange, but `price_history` (`ticker, date`), `company_profile` (`ticker`) and `news` (`ticker, url`) do not. A ticker held on both ASX and NYSE (e.g. `BHP`) shares one row set, so the DB fallback and stored profile can show the other market's data. Fixing it needs an `exchange` column in those unique constraints plus an Alembic migration.

## Stake sync never removes sold positions

**File:** `backend/app/api/holdings.py` (`sync_stake_data`)

Sync upserts what Stake returns but never deletes `source="stake"` rows that Stake no longer reports, so a fully sold position stays on the dashboard until deleted by hand. A fix must only prune exchanges whose fetch succeeded (`stake_client` tolerates per-exchange failures), or a transient ASX error would wipe ASX holdings.
