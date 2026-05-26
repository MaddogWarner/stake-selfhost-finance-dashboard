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

## Fundamentals API — dead fallback expression in FMP path

**File:** `backend/app/api/fundamentals.py`, line 54

```python
"name": profile.get("companyName") or profile.get("companyName", ticker),
```

Both `get()` calls use the same key `"companyName"`. The first call is redundant — when `"companyName"` is absent, `profile.get("companyName")` returns `None` (falsy), so the `or` evaluates `profile.get("companyName", ticker)`, which also looks up the same absent key and returns `ticker`. The intent is to fall back to `ticker`, but the first `get()` adds noise without effect.

Fix:

```python
"name": profile.get("companyName") or ticker,
```
