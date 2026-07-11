# Stake Dashboard — Security Hardening: TLS, Auth, Token Encryption, Rate Limiting
**Date:** 11/07/2026
**Author:** Claude (plan/architecture) — for Codex execution
**Context:** The dashboard currently serves plain HTTP, has no authentication on any endpoint (including `/api/admin/*`, which can overwrite the Stake token or forward credentials to Stake), stores the Stake session token in plaintext in Postgres, and has no rate limiting. The Stake session token grants access to a live brokerage account, so this matters even for a single-user LAN app.

This plan hardens the stack in four parts:
- **P1** — HTTPS by default with a self-signed cert generated on first container start; HTTP redirects to HTTPS.
- **P2** — Single-admin authentication: first-visit setup wizard sets a password; login issues a Redis-backed session cookie; all API routes require it.
- **P3** — Encrypt the Stake session token at rest (Fernet), with automatic key generation if none is configured.
- **P4** — Redis-backed rate limiting, strict on credential endpoints.

Decisions already made with David (do not re-litigate): password login page (not API key), first-visit setup wizard for the admin password with auto-generated backing keys, HTTP→HTTPS redirect kept on the old port, Codex implements / Claude reviews.

---

## Security requirements (apply throughout)

- The admin password must never be persisted in plaintext or logged — only a bcrypt hash in `app_settings`. Treat it like the Stake credentials in the existing `stake-login` flow: request body + memory only.
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`. Session identifiers are random (`secrets.token_urlsafe(32)`), stored server-side in Redis — no JWTs, no client-side signed state.
- Do not log request bodies on auth endpoints. Never echo the password, hash, encryption key, or session id in any response or log line.
- Comparisons of secrets use constant-time primitives (`bcrypt.checkpw` is inherently so; use `secrets.compare_digest` anywhere else).
- Fail closed on auth (missing/invalid session → 401). Fail **open** on rate limiting if Redis is unreachable (log a warning) — never lock the sole user out because the cache is down.
- No HSTS header. HSTS is scoped per-host (ignores port); setting it on `localhost` would force-break every other local HTTP dev server on the machine.

New dependencies (add to `backend/requirements.txt`, pinned like the existing entries): `bcrypt` (latest 4.x), `cryptography` (latest stable). Nothing else — rate limiting is hand-rolled on the existing Redis client.

---

## P1 — HTTPS by default (frontend nginx container)

The frontend nginx container becomes the TLS terminator. The backend stays plain HTTP inside the compose network (unchanged), as does `localhost:8000` for dev.

### `frontend/Dockerfile`

- `apk add --no-cache openssl` in the final (nginx) stage.
- Copy a new entrypoint script into `/docker-entrypoint.d/40-selfsigned-cert.sh` (the stock `nginx:alpine` entrypoint runs everything in that directory before starting nginx). Make it executable.
- Replace the static `nginx.conf` copy with an envsubst template (see below): copy to `/etc/nginx/templates/default.conf.template`. The stock entrypoint's `20-envsubst-on-templates.sh` renders it using environment variables. Set `ENV NGINX_ENVSUBST_FILTER='^(HTTPS_PORT)$'` (or equivalent) so only our variable is substituted and nginx's own `$` variables survive.
- `EXPOSE 80 443`.

### New: `frontend/docker-entrypoint.d/40-selfsigned-cert.sh`

```sh
#!/bin/sh
set -eu
CERT_DIR=/etc/nginx/certs
if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
    mkdir -p "$CERT_DIR"
    echo "Generating self-signed TLS certificate (first run)..."
    openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
        -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
        -subj "/CN=stake-dashboard" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    chmod 600 "$CERT_DIR/server.key"
fi
```

The cert lives in a named volume (`certs`) so it survives container recreation; users who want a trusted cert (own CA, Tailscale, etc.) just drop their own `server.crt`/`server.key` into that volume — document this in the README.

### `frontend/nginx.conf` → template

```nginx
server {
    listen 80;
    # Port 80 exists only to redirect. ${HTTPS_PORT} is the host-published HTTPS
    # port (nginx cannot know it otherwise), substituted at container start.
    return 301 https://$host:${HTTPS_PORT}$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    ssl_certificate     /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
    }
}
```

`X-Forwarded-For` is set to `$remote_addr` (overwrite, never append) so the backend can trust the first/only value for rate limiting.

### `docker/docker-compose.yml` and `docker/docker-compose.ghcr.yml`

Frontend service in both files:

```yaml
    ports:
      - "${FRONTEND_HTTP_BIND:-127.0.0.1:3000}:80"
      - "${FRONTEND_HTTPS_BIND:-127.0.0.1:3443}:443"
    environment:
      HTTPS_PORT: "${HTTPS_PORT:-3443}"
    volumes:
      - certs:/etc/nginx/certs
```

Add `certs:` to the volumes block in both files. The ghcr file's existing `FRONTEND_BIND` variable is replaced by the two new ones — update its header comment accordingly. If a user overrides the published HTTPS port, they must set `HTTPS_PORT` to match; note this next to the variables.

Backend service (both files): append `--proxy-headers --forwarded-allow-ips=*` to the uvicorn command so `request.client` and forwarded headers resolve correctly behind nginx. This is safe because the backend port is never published beyond `127.0.0.1` (dev) or at all (ghcr) — anyone who can reach the backend directly already owns the host. Note: in the ghcr compose the backend currently has no explicit `command:`; add one mirroring the dev compose (or set it via the backend image's CMD — Codex to pick whichever keeps the two files consistent).

The dashboard URL becomes **https://localhost:3443**; http://localhost:3000 redirects there. Update README quick-start accordingly.

---

## P2 — Authentication: setup wizard + password login + Redis sessions

Single admin account, no usernames. State machine exposed by `GET /api/auth/status`:

| state | meaning |
|---|---|
| `setup_required` | no `admin_password_hash` row exists yet |
| `unauthenticated` | password set, no valid session cookie |
| `authenticated` | valid session |

### Backend — new `backend/app/services/auth_service.py`

- `get_password_hash(db)` / bcrypt helpers. Hash stored in `app_settings` under key `admin_password_hash` (reuses the existing table and upsert pattern from `settings_service.py` — no migration needed).
- `set_password(db, password) -> bool`: `INSERT ... ON CONFLICT DO NOTHING` on the key; return whether the insert won. This is the setup race guard — first request wins, concurrent second gets `False`.
- Password policy: minimum 10 characters, maximum 72 bytes (bcrypt truncates beyond 72 — reject, don't truncate silently). No composition rules.
- Sessions: `create_session(redis) -> str` stores `session:{token}` with TTL 7 days (constant `SESSION_TTL_SECONDS = 604800`); `check_session(redis, token) -> bool`; `destroy_session(redis, token)`. Fixed TTL, no sliding renewal — after 7 days you log in again; keep it simple.

### Backend — new `backend/app/api/auth.py` router

- `GET /api/auth/status` → `{ "status": "setup_required" | "unauthenticated" | "authenticated" }`. Unauthenticated access allowed.
- `POST /api/auth/setup` — body `{password: SecretStr}`. 409 if a hash already exists (or if the ON CONFLICT insert lost the race). On success: create session, set cookie, return status. Rate-limited (P4).
- `POST /api/auth/login` — body `{password: SecretStr}`. 401 on mismatch with a generic message ("Incorrect password."); when no hash exists yet return 409 pointing at setup. On success: create session, set cookie. Rate-limited (P4).
- `POST /api/auth/logout` — destroy the session, clear the cookie.

Cookie: name `stake_dash_session`, `httponly=True, secure=True, samesite="lax", path="/", max_age=SESSION_TTL_SECONDS`. (`Secure` on `http://localhost:8000` in dev is fine — browsers treat localhost as a trustworthy origin.)

### Backend — enforcement

New dependency `require_auth(request, redis)` in `auth_service` (or `app/api/deps.py` if Codex prefers): read the cookie, `check_session`, raise 401 `{"detail": "Not authenticated"}` if absent/invalid.

In `main.py`, apply it at router registration: `app.include_router(<each existing router>, dependencies=[Depends(require_auth)])` for **every** existing router (holdings, watchlist, prices, news, admin, etc.). Exemptions: the new auth router, `GET /api/version`, and any health endpoint. `/docs` and `/openapi.json` stay public (schema only, no data) — acceptable for a self-hosted app.

Keep CORS for the dev servers working with cookies: add `allow_credentials=True` to the existing `CORSMiddleware` config (origins stay the explicit localhost list — never `*` with credentials).

### Backend — password reset path

New module `backend/app/reset_admin_password.py` runnable as `python -m app.reset_admin_password`: deletes the `admin_password_hash` row and all `session:*` keys in Redis, prints confirmation. The wizard then reappears on next visit. Document in README:

```bash
docker compose exec backend python -m app.reset_admin_password
```

This is intentionally host-access-only — no reset over HTTP.

### Frontend

- `frontend/src/api/auth.ts`: `fetchAuthStatus`, `setup`, `login`, `logout`. Set axios `withCredentials: true` globally in `api/client.ts` (needed in dev where origin differs; harmless in prod same-origin).
- New `AuthGate` component wrapping the app in `App.tsx`: queries `/api/auth/status`;
  - `setup_required` → **SetupWizard**: single card explaining this protects the dashboard, password + confirm fields (min 10 chars, client-side match check), submit → `setup` → app.
  - `unauthenticated` → **LoginPage**: password field, submit → `login`; show the API error message on failure (covers both bad password and 429 rate-limit responses).
  - `authenticated` → render the app.
- Axios response interceptor: any 401 flips auth state back to `unauthenticated` (except on the auth endpoints themselves).
- Add a **Log out** control wherever the settings/admin UI lives (same page as `StakeConnect` — Codex: check `Settings`/`Admin` page component and match its style).
- Styling: match the existing dark slate/sky Tailwind idiom used in `StakeConnect.tsx`.

**Setup-race note for the README (see P5):** until the wizard is completed, anyone who can reach the published port can claim the admin password. Default binds are `127.0.0.1` so this is a non-issue out of the box, but tell users to complete setup immediately after first start, especially if they changed the bind address.

---

## P3 — Encrypt the Stake token at rest (Fernet)

### Key management — `backend/app/services/crypto_service.py` (new)

Key resolution order, resolved once at startup (in `lifespan`, before `bootstrap_stake_token`):

1. `TOKEN_ENCRYPTION_KEY` env var (add `token_encryption_key: str | None = None` to `config.py`) — must be a valid Fernet key; fail startup loudly with a clear message if it isn't.
2. Key file `/data/fernet.key` inside the backend container — new named volume `backend_data` mounted at `/data` (add to both compose files).
3. Neither exists → generate `Fernet.generate_key()`, write to `/data/fernet.key` with mode `0600`, log **one** info line saying a key was generated and where it lives. Never log the key itself.

Expose `encrypt(value: str) -> str` and `decrypt(value: str) -> str` using the resolved key.

### Storage format — `backend/app/services/settings_service.py`

- `set_stake_token` stores `f"enc:v1:{encrypt(token)}"`.
- `get_stake_token`:
  - value starts with `enc:v1:` → decrypt and return. On `InvalidToken` (key changed/lost): log an error explaining the encryption key no longer matches, mark the token invalid (existing `stake_token_invalid` mechanism), and return `None` — the UI's existing "Token expired — re-connect" state then guides the user to reconnect. Never crash on this.
  - value has no prefix (legacy plaintext) → return it as-is **and** lazily migrate: re-store it encrypted. This upgrades existing installs on first read with no migration script.

The `enc:v1:` prefix is deliberate versioning — if we ever rotate schemes, `v2` can coexist.

### `.env.example`

Add, commented:

```bash
# Optional: Fernet key for encrypting the Stake session token at rest.
# If unset, a key is auto-generated on first start and stored in the backend's
# /data volume. To supply your own:
#   docker compose exec backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# or on the host: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# TOKEN_ENCRYPTION_KEY=
```

(Do not suggest `openssl rand -base64 32` — Fernet requires *urlsafe* base64; openssl's output can contain `+`/`/` and fail confusingly.)

**Honesty requirement for the docs:** this protects DB dumps/backups and direct DB access — it does not protect against full host compromise, since the key necessarily lives on the same host (volume or `.env`). Say exactly that in the README; don't oversell it.

---

## P4 — Rate limiting (Redis fixed window, no new deps)

### New `backend/app/services/rate_limit_service.py`

(Name it distinctly from the existing `rate_limiter.py`, which is the *outbound* FMP budget — do not touch that file.)

- `client_ip(request) -> str`: first entry of `X-Forwarded-For` if present, else `request.client.host`. With the P1 nginx config overwriting XFF and the backend port unpublished, this is trustworthy; add a code comment saying it relies on that.
- Dependency factory:

```python
def rate_limit(scope: str, limit: int, window_seconds: int):
    async def dependency(request: Request, redis: Redis = Depends(get_redis)) -> None:
        ...
    return dependency
```

Fixed window: key `ratelimit:{scope}:{ip}:{unix_time // window_seconds}`, `INCR`, set `EXPIRE window_seconds` when the count is 1. Over limit → `HTTPException(429, detail="Too many requests. Try again shortly.", headers={"Retry-After": str(window_seconds)})`. Any Redis error → log warning once per occurrence and allow the request (fail open, per security requirements).

### Applied limits

| Endpoint | Limit | Rationale |
|---|---|---|
| `POST /api/auth/login` | 5 / 60 s per IP | brute-force guard on the admin password |
| `POST /api/auth/setup` | 5 / 60 s per IP | setup-race hammering |
| `POST /api/admin/stake-login` | 5 / 60 s per IP | stops the endpoint being a credential-forwarding oracle against the user's Stake account |
| `POST /api/admin/stake-token` | 10 / 60 s per IP | each attempt costs a live Stake validation call |
| Everything else under `/api` | 240 / 60 s per IP | generous global backstop; the dashboard legitimately fires many parallel queries on load |

Per-endpoint limits via `dependencies=[Depends(rate_limit(...))]` on those routes; the global backstop via a dependency added alongside `require_auth` at router registration (exempt `GET /api/auth/status` from nothing — the backstop applies to it too).

Behaviour note: `stake-login`/`stake-token` sit behind auth after P2, so these limits are defence in depth, not the primary control.

### Frontend

`errorMessage()` in `utils/errors.ts` already surfaces `detail` from error responses — verify a 429 renders sensibly in the login page and `StakeConnect`; no special handling needed beyond that.

---

## P5 — Documentation

### `README.md`

- Update quick start: dashboard is now at **https://localhost:3443**; first visit shows a certificate warning (self-signed — expected; how to proceed in Chrome/Firefox/Safari in one line each) and then the one-time setup wizard to choose the admin password.
- New **Security** section covering, plainly:
  - **Do not expose this dashboard to the internet.** It is designed for localhost/LAN/VPN (e.g. Tailscale) use. The Stake session token it holds grants access to a live brokerage account.
  - TLS is self-signed by default; browsers will warn once. To use your own cert, replace `server.crt`/`server.key` in the `certs` volume.
  - Secrets custody: the token encryption key lives in `.env` or the backend `/data` volume **on the same host as the database** — this protects DB dumps and backups, not a fully compromised host. Risk is low for a home deployment but users should understand it.
  - Complete the setup wizard immediately after first start — until then, whoever reaches the port first sets the password (default binds are `127.0.0.1`, so normally only you can).
  - Password reset: the `docker compose exec backend python -m app.reset_admin_password` procedure.
  - Rate limits exist; hammering login locks you out for up to a minute.
- Update any screenshots/URLs referencing `http://localhost:3000`.

### Other docs

- `CLAUDE.md`: brief additions — auth model (Redis sessions, `require_auth`), `enc:v1:` token storage, `rate_limit_service` vs `rate_limiter` distinction, new URL/ports.
- `CHANGELOG.md`: entry under the new version.
- `backend/app/version.py`: bump minor → `0.5.0` (breaking-ish UX change: new port + login).

---

## Implementation order & verification

Order: P3 → P2 → P4 → P1 → P5. (P3/P2/P4 are backend-testable without touching Docker; P1 flips the transport last so the dev loop stays easy.)

Acceptance criteria — all must pass:

1. **Fresh install:** `cd docker && docker compose up --build` with no `.env` secrets → containers start; logs show cert generation and encryption-key generation exactly once; second `up` shows neither (both persisted in volumes).
2. `curl -sI http://localhost:3000/` → `301` with `Location: https://localhost:3443/`.
3. `curl -skI https://localhost:3443/` → `200`, TLS handshake OK (`-k` needed, self-signed).
4. Unauthenticated `curl -sk https://localhost:3443/api/holdings` → `401`. `GET /api/version` and `GET /api/auth/status` → `200` without auth.
5. First browser visit → setup wizard; setting a password lands in the dashboard; container restart keeps the session (cookie + Redis) until TTL; **Log out** returns to the login page; wrong password → generic 401 message.
6. Second concurrent/subsequent `POST /api/auth/setup` → `409`.
7. Six rapid wrong-password logins → sixth gets `429` with `Retry-After`.
8. After connecting Stake, `docker compose exec db psql -U stake -d stake_dashboard -c "select value from app_settings where key='stake_session_token'"` shows an `enc:v1:` value, not the raw token. A pre-existing plaintext row is transparently readable and becomes `enc:v1:` after first use.
9. Deleting the `/data/fernet.key` volume file (simulated key loss) and restarting → app runs, logs the decrypt error, UI shows the reconnect state; no crash loop.
10. `python -m app.reset_admin_password` → wizard reappears, old session cookie rejected.
11. Existing test suite still passes; add backend tests for: auth status transitions, setup race (two concurrent setups), login success/failure, `require_auth` 401, encrypt/decrypt round-trip + legacy plaintext migration + InvalidToken handling, rate-limit window (use fakeredis or the test Redis, whichever the suite already uses — check `backend/tests/` conventions first).
12. Frontend verified in a real browser against the compose stack (per David's global workflow, Playwright or equivalent): console clean, wizard/login/logout flows, desktop + mobile widths.

Out of scope (do not implement): HSTS, multi-user accounts, OAuth/passkeys, Let's Encrypt/ACME, encrypting other DB columns, CSRF tokens (SameSite=Lax + no cross-site deployment covers the threat model; document this choice in a code comment on the cookie).
