# Phase M1 — direct owner dashboard

Implemented and verified 2026-10-14. Open **http://localhost:13000/admin**.
Storefront: **http://localhost:13000**. This phase provides the dashboard shell;
catalog creation/upload workflows are still assigned to M2–M4.

## Start and provision

From `F:\AlphaZee`, with Docker Desktop running:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
```

Provisioning prompts for your own password twice; no default account was added
to development. To reset that account and revoke its sessions:

```powershell
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME --reset-password
```

Use either the create or reset command as needed. Do not put passwords into files
or command arguments. The existing eight-hour default session and server-side
Origin/CSRF protections continue to apply.

## Behavior

- `/admin` restores a valid owner session or shows login. Private navigation is
  hidden during the check and while signed out; passwords clear after login.
- Sections have URLs: `/admin/products`, `/admin/collections`, `/admin/media`,
  `/admin/inventory`, `/admin/suppliers`, `/admin/orders`, `/admin/returns`,
  `/admin/coupons`, `/admin/reports`. Overview is `/admin` (also `/admin/overview`).
  Refresh and back/forward preserve the selected section; unknown sections
  show an explicit message. The storefront footer links directly to `/admin`.
- Existing operational renderers/services are reused. Products, Collections and
  Media explicitly explain that authoring is coming in the next phases, with
  no fake save controls. Order-specific deep links remain M7 work.
- Return to store, refresh and sign out are available. Unsaved form input guards
  section navigation/refresh/exit; rejected back-navigation restores the current
  route without asking a second time. A failed logout retains its visible error.
- Expiry/logout invalidates outstanding view requests so late private responses
  cannot replace login. Dispatch/settlement dialogs close, preserve keyboard
  handling and make the page behind them inert. The dashboard itself is not an
  overlay and does not trap keyboard focus or lock body scrolling.
- Narrow layouts use horizontally scrollable section navigation and contained
  content/table overflow. Remote Google Fonts load asynchronously; the app also
  works with remote fonts blocked.

## Actual verification

| Check | Result |
| --- | --- |
| Frontend suite | 87 passed, zero failed; includes route/login, unknown sections, stale private responses, dirty-form guards and existing operation tests |
| Frontend production build | Passed; 28 modules |
| Backend auth/session regression | 25 passed; one existing Starlette/AnyIO warning; backend business code unchanged |
| Production web image | Built; existing Caddy SPA fallback returns 200 and compiled app for `/admin`, `/admin/orders`, `/admin/products`, `/admin/reports` |
| Real headless Chrome | 13 checks passed against `alphazee_m1_browser_c0d22289e0_test`, with an isolated SAMPLE owner and API/Vite processes |
| Browser scenarios | Direct login, hidden private navigation, orders empty state, Products placeholder, fresh-document session/section restoration, inventory, back/forward, 390px mobile width, logout and server rejection, relogin and forced isolated expiry |
| Screenshots | Desktop 1440x900 and mobile 390x844 inspected; Refresh contrast repaired; final captures show settled empty inventory |
| Normal development | Row/schema/sequence and config fingerprints match M0; direct/proxied readiness, 401 owner protection and 503 public-order protection passed |

Machine-readable evidence: `m1_browser_verification.json` and
`m1_local_verification.json`. Screenshots/private Chrome profile are under
`.local/m1-browser/db397b757c/` (Git-ignored). The SAMPLE database is retained;
normal development was not used for browser fixtures. Test processes were stopped.
The temporary static-web test container/network was removed; no production DB/API
was started and no production credentials/DNS/TLS were exercised.

Commands used for regression and browser verification:

```powershell
# From frontend
npm.cmd test
npm.cmd run build
# From repository root
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_owner_sessions.py backend/tests/test_api_auth.py -q -p no:cacheprovider --tb=short
backend\.venv\Scripts\python.exe backend/scripts/verify_m1_browser.py
docker compose --env-file .env.production.example -f compose.prod.yml build web
```

Browser verification uses the installed Chrome and the existing `websockets`
package from Uvicorn's environment; it creates a fresh test DB and random ports,
not the private M0 restore. Windows may require permission to launch Chrome.
Initial harness failures (extension-target selection, empty-state wording and
reload timing) were corrected; only the completed final run is reported passed.
Runtime exceptions and same-origin transport failures were absent. Expected 401
responses and deliberately blocked optional font requests are not app failures.

This is M1 acceptance only: no new product/media schemas, catalog authoring,
checkout lab, or complete commerce browser walkthrough is delivered yet. Public
checkout remains disabled. The next phase is M2 catalog lifecycle and owner APIs.
