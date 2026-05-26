# Known Issues / Minor Technical Debt

## Docker — source files owned by root inside container

**File:** `backend/Dockerfile`

`COPY . .` runs before the `USER appuser` switch, so all source files inside the container are root-owned. The app runs as `appuser` and only reads those files at runtime, and `/tmp` (used for the yfinance SQLite cache) is world-writable, so this causes no runtime problems today.

If the app ever needs to write inside `/app` at runtime, change the COPY instruction to:

```dockerfile
COPY --chown=appuser:appgroup . .
```
