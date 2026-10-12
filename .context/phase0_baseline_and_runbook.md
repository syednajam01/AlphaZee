# Phase 0: baseline and checkout containment

Recorded 2026-10-13 against local commit `2ff7ac5`.

## Baseline

- Python used: backend virtual environment, 3.13.3. System launcher also lists 3.14; do not accidentally use it for this project.
- Node: 25.2.1. Vite build reports 5.4.21.
- FastAPI: 0.115.6; SQLAlchemy: 2.0.36; pytest: 8.3.5.
- Normal frontend: port 3000; normal API: 8000; PostgreSQL: loopback 5433.
- Development PostgreSQL reports 16.15, database `alphazee_dev`.
- Read-only inspection found applied migration `e5c83f14a091`; repository head is `13b1315d1395`. No migration was applied or rewritten. The development database is behind the repository head.
- Baseline counts: orders 0, order_lines 0, stock_reservations 0, inventory_balances 0, products 0, suppliers 0. These are recorded observations, not permission to reset the database.
- Initial working tree contained the untracked repair plan. Existing commerce changes were already in the local commit; no unrelated work was reverted.
- Port-listener discovery through PowerShell did not provide usable results; existing frontend/API process status is not verified by this baseline.

## Containment contract

Public order creation is disabled server-side. `POST /api/v1/orders` returns 503 before database access, including direct requests and requests with an admin key. Catalog, cart, tracking and existing-order routes are not disabled by this gate.

`GET /api/v1/storefront/capabilities` returns only checkout availability and a test-mode flag, with `Cache-Control: no-store`. The frontend starts closed and keeps checkout disabled if this request fails or returns an invalid response. Cart contents are retained. Test checkout is visibly marked SAMPLE / TEST.

There is deliberately no public launch switch in this phase. `TEST_CHECKOUT_ENABLED=true` is accepted only when `APP_ENV=test` and the database is loopback PostgreSQL with a name ending in `_test`, without query-string connection overrides. Public launch requires the later release work.

## Separate browser test profile

Normal development settings are left in place. The separate profile uses API 8001, frontend 3001 and `alphazee_browser_test`. Vite refuses occupied ports rather than silently moving to a different port. Both profiles bind the frontend to loopback.

Preparation for the browser phase:

1. Provision and migrate only the disposable `alphazee_browser_test` database after verifying its target. This phase does not create or seed that database.
2. In `backend`, copy `.env.browser-test.example` to `.env.browser-test` and use test-only credentials. The local file is gitignored.
3. Start the separate API from `backend`:

   ```powershell
   .\.venv\Scripts\python.exe scripts/start_browser_test.py
   ```

   The launcher validates the profile against the normal application database, rejects a matching database name, and passes configuration only to its child process. It does not alter the running development server, `.env`, or database schema.

4. In a separate terminal in `frontend`:

   ```powershell
   npm.cmd run dev -- --mode test
   ```

5. Visit `http://127.0.0.1:3001`. Verify `/api/v1/ready` through that proxy and the SAMPLE / TEST label before any sample mutations. Do not substitute the normal development API.

Label all future fixtures with SAMPLE / TEST. Fixtures must be restricted to the disposable target; do not run the ordinary development seed script for browser tests.

## Repeatable checks

From `backend`:

```powershell
.\.venv\Scripts\python.exe scripts/phase0_baseline.py
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The baseline script opens a read-only transaction and prints no credentials. It does not run migrations. `alembic heads` inspects repository migration files only.

The pytest fixture validates a distinct loopback PostgreSQL `_test` target before creating or dropping fixture tables. Non-PostgreSQL, remote and query-redirected targets are rejected. Existing integration fixtures explicitly override the checkout gate only after obtaining a guarded disposable database session. Containment tests use their own client without that override.

From `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Use `npm.cmd` on this Windows installation because PowerShell blocks `npm.ps1`; no execution-policy change is needed.

Never reset, truncate, downgrade or seed development data for verification. Never remove the Docker volume. Migration lifecycle testing belongs on a separately validated disposable database and remains pending for the later repair phases.
