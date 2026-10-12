# Phase A: owner access

Implemented 2026-10-13. All verification used the terminal; no browser was launched.

## Local setup

The development database has been upgraded to `6a1e9b32c704` and the API restarted on port 8000. Existing business tables were preserved. No development owner or default password was created.

From an interactive PowerShell terminal, choose your own username and password:

```powershell
cd F:\AlphaZee\backend
.\.venv\Scripts\python.exe scripts/provision_owner.py YOUR_USERNAME
```

The command displays the database target and prompts twice with hidden input. Passwords must contain 12–128 characters. Usernames contain 3–100 letters, numbers, underscores, periods, @ or hyphens and are normalized to lowercase. Open the Owner Console from the storefront footer and sign in. The console restores a valid session when reopened or after reloading the page.

For a fresh installation, configure `.env` and run `.\.venv\Scripts\python.exe -m alembic upgrade head` before provisioning. Start the local API with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers`, and run `npm.cmd run dev` from `frontend`.

To reset credentials and revoke all of that owner's sessions:

```powershell
.\.venv\Scripts\python.exe scripts/provision_owner.py YOUR_USERNAME --reset-password
```

There is no public registration endpoint. `ADMIN_API_KEY` is accepted as deprecated configuration input only and grants no access. Remove old environment entries `OWNER_USERNAME`, `OWNER_PASSWORD` and `SESSION_SECRET_KEY` if present; they do not provision credentials. The frontend removes the old `alphazee_admin_key` entry from both browser storage locations.

## Session behavior and deployment

- Passwords use salted PBKDF2-SHA256 with 600,000 iterations. Only hashes of opaque session tokens are stored in PostgreSQL. Sessions survive API restarts and are revoked on logout; signing in rotates the current browser session.
- Cookies are HttpOnly, SameSite=Strict, path `/`. Production additionally uses Secure and the `__Host-` prefix. Session lifetime defaults to eight hours, configurable with `SESSION_MAX_AGE_SECONDS` between 300 and 28800; it is a fixed expiry, not sliding activity renewal.
- Use a same-origin `/api` reverse proxy. Set `APP_ENV=production`, `DEBUG=false`, and replace `ALLOWED_ORIGINS` with exact HTTPS storefront origins. Wildcards, paths and local production origins are rejected. Login and authenticated mutations require a trusted Origin; mutations additionally require the session's CSRF token, held only in frontend memory.
- Login allows five attempts per account and twenty per client IP in a 15-minute window. Successful attempts count too. Counters are database-backed and atomic across workers. A 429 response includes `Retry-After: 900`. Wait for the window to expire before retrying.
- The local API ignores forwarded client addresses. In production configure proxy trust only for the actual reverse proxy; do not trust arbitrary client-provided forwarded headers. This determines which client IP the limiter sees.
- All `/api/v1/admin/*` routes require an active owner session. Auth/admin responses are marked no-store. A 401 returns the console to login. A failed logout stays visible and does not falsely claim server revocation.

## Verification and scope

Backend: 182 tests passed. Frontend: 76 tests passed; production build passed. Migration upgrade/downgrade/re-upgrade and real HTTP login, CSRF rejection, API-restart persistence and logout revocation passed on a dedicated disposable database. Evidence: `phase_a_auth_verification.json`; development before/after counts: `phase_a_development_before.json` and `phase_a_development_after.json`.

Run backend suites sequentially: the disposable-test fixture uses an advisory lock to reject overlapping suite processes before schema cleanup. The migration verifier `backend/scripts/verify_owner_auth.py` creates and retains a unique test database and never downgrades development.

DOM tests cover login errors, password clearing, restoration, expiry and failed/successful logout. Browser rendering and native browser cookie behavior were not exercised. Public checkout stays disabled; Phase B and subsequent commerce work remain pending.
