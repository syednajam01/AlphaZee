# Repair verification report

## Phase 0 — implemented, automated checks passed

Date: 2026-10-13. Starting commit: `2ff7ac5`.

### Changes

- Added a default-closed server dependency on public order creation. Disabled checkout fails before the database dependency executes; an admin key does not bypass it.
- Added a no-store public capability endpoint with only safe booleans.
- Added frontend capability state, disabled checkout controls, explanatory messages and SAMPLE / TEST labeling. Failed or malformed capability responses keep checkout closed without clearing the cart.
- Limited checkout enablement to explicit test mode on a loopback PostgreSQL `_test` database; rejected query-string target overrides.
- Strengthened pytest database validation, keeping guarded database fixtures separate from the dedicated containment tests.
- Added a separate browser-test environment example, validated child-process API launcher on port 8001, and Vite test mode on port 3001. Normal development configuration is not rewritten.
- Added the read-only baseline script, operational runbook, README pointer and gitignore entry for local browser-test credentials.

Primary files: `backend/app/config.py`, `backend/app/dependencies/checkout.py`, `backend/app/api/v1/orders.py`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/scripts/`, `frontend/src/utils/capabilities.js`, `frontend/src/utils/api.js`, storefront header/cart/checkout/main, and `frontend/vite.config.js`.

### Verification results

| Check | Result |
| --- | --- |
| Pre-fix reproduction | Direct checkout reached a forbidden database dependency; capabilities returned 404; configuration had no containment fields |
| Full backend regression | 159 passed using `python -m pytest -q -p no:cacheprovider --tb=short` |
| Additional launcher tests, added after full-suite collection | 2 passed; unsafe development target rejected before launch; child configuration does not mutate parent environment |
| Frontend tests | 69 passed using `npm.cmd test` |
| Production build | Passed using `npm.cmd run build` |
| Patch whitespace | `git diff --check` passed |
| Development baseline recheck | Same applied revision and same six recorded table counts as baseline |

The full backend run includes real PostgreSQL integration tests using the guarded `alphazee_test` fixture target, plus unit/mocked tests. The 11 new containment cases run without a real database. Existing integration clients explicitly override the gate after acquiring a guarded test session so order behavior remains tested; the containment cases use independent clients to test the real gate.

The enabled-mode order-service test uses a mock session/service; it verifies the gate permits the isolated configuration, not a complete browser checkout. The new launcher tests mock process creation, so they do not claim the browser test database is provisioned or migrated.

One existing Starlette/AnyIO deprecation warning remains. Initial frontend command execution required `npm.cmd` because this machine blocks PowerShell npm scripts. No execution policy was changed. Pytest cache writing was disabled after a cache-directory permission warning; tests themselves run normally.

### Data and migrations

The development baseline was inspected using an explicit read-only transaction. `alphazee_dev` remains at `e5c83f14a091`, while repository head is `13b1315d1395`. No migrations, seeds, resets or application writes were executed against development. The observed orders, order_lines, stock_reservations, inventory_balances, products and suppliers counts remain zero. This comparison covers those counts and revision, not a full database checksum.

No new schema migration was needed. Migration lifecycle verification and the development schema mismatch are outstanding for subsequent phases. Browser-test sample data has not been created.

### Browser verification — not performed in Phase 0

No live browser interaction or localhost button fix is claimed. Frontend tests and a successful build do not prove the page initializes correctly in the user's browser. The original non-working controls must be reproduced and diagnosed in Phase L1, including Console/Network evidence, API readiness, overlays and persisted browser actions.

Public checkout remains disabled. Owner-session authentication and the other corrected commerce rules remain scheduled in their respective phases. Phase 0 does not establish launch readiness.

Runbook: `phase0_baseline_and_runbook.md` in this directory.

## Phase L1 — implemented with terminal-only verification

Date: 2026-10-13. The owner explicitly requested that work proceed without a browser. No browser was launched. The interrupted attempt to install Playwright left no package.json/package-lock change; no new dependencies were installed.

### Diagnosis

- Port 3000 belonged to Node PID 4844 running `F:\AlphaZee\frontend\node_modules\vite\bin\vite.js`, confirmed by process-command inspection. Vite served the expected HTML, main module and stylesheet with 200 responses. This rules out a different project on that port at inspection time; it does not inspect the user's browser cache.
- No API listened on 8000. Direct health requests failed to connect; Vite health/readiness requests returned 500 because its upstream was unavailable.
- Source inspection found all four live modal templates gave their embedded backdrop `is-open` even when the modal root was closed. `.drawer-backdrop.is-open` explicitly set `visibility:visible`, overriding inherited hidden visibility; the closed parent also had opacity zero. Such a descendant can remain an invisible pointer interceptor. This is a concrete source defect consistent with the reported dead buttons, but the exact pointer behavior was not measured in a browser.
- A regression test constructed the actual app with a failing API and demonstrated that closed overlay roots were neither hidden nor inert. It failed before the overlay repair and passes after it. This test verifies DOM state, not computed browser CSS/hit testing.
- Footer/mobile tracking did not share the header handler. All Products pointed to missing `#shop`; policy links pointed to nonexistent sections; two support links used a placeholder WhatsApp destination. The search icon only scrolled to the catalog.

### Repairs

- Added a shared overlay controller for product, cart, menu, checkout, tracking and owner console. Closed roots are explicitly `hidden` and `inert`, with a CSS `display:none !important` rule. Embedded backdrops become visible only when their containing modal opens.
- Added Escape dismissal, Tab/Shift-Tab focus containment, focus return, previous scroll-state restoration, and a single active overlay. Product close continues invalidating outstanding detail requests. Mobile expanded state now follows open/close.
- Separated app construction into `src/app.js`. The entrypoint handles both loading and already-ready documents, catches module/construction failures, and provides a working reload action with an explanatory error screen.
- Wired header/mobile/footer tracking to the same modal, repaired the shop anchor, and accurately named the catalog-scroll button. Placeholder support/policy destinations are explicitly unavailable instead of broken links. Collection failures offer a customer-facing retry message.
- Made unfinished dispatch/remittance forms dismissible and prevented native submit reloads. Their submit buttons are explicitly unavailable until the planned fulfillment/settlement phases; no unsupported operation reports success.
- Started the existing backend on loopback port 8000 using its development configuration, leaving the existing Vite process in place. This restored live API reads. No schema or sample data changes were made.
- Added `backend/scripts/check_local_integration.py` for repeatable terminal-only HTTP checks, and completed the control register in `frontend_control_inventory.md`.

### Verification

| Check | Actual result |
| --- | --- |
| Frontend test suite | 75 passed (`npm.cmd test`), including 6 new shell/startup/overlay tests |
| Final production build | Passed (`npm.cmd run build`), 27 modules transformed |
| Patch whitespace | `git diff --check` passed |
| Shell DOM regression | Offline mount; hidden/inert roots; cart/menu/tracking/admin open/close; Escape; focus return; FAQ; all tracking links; browse action; retry/recovery; collection filter; sample variant selection; add/quantity/remove cart controls; public checkout disabled; nested form cancel/disabled state |
| Overlay DOM tests | Tab and Shift-Tab wrap, Escape, scroll/focus restoration, listener cleanup, switching dialogs |
| Startup tests | DOMContentLoaded path, already-ready path, module failure and construction failure with reload action |
| Live HTTP checks | 22 passed through direct API and Vite; evidence in `phase_l1_http_checks.json` |
| Data/API reads | Health and readiness 200, database connected; collections/products/hero 200 with empty results |
| Containment/access | Order creation with empty payload 503; anonymous admin overview 401, both directly and through Vite |
| Source served by Vite | Current main/app/startup/overlay/CSS all 200 with expected repair content |

The product scenario uses explicitly labelled in-memory SAMPLE / TEST fixtures with mocked fetch. Existing cart tests verify storage restoration at unit level. No actual browser reload, customer order, owner mutation or successful checkout was used for verification. Native keyboard activation, touch behavior, visual layout and pointer targeting remain unverified.

Read-only database recheck still reports revision `e5c83f14a091` and zero rows in each of the six baseline tables. Repository migration head remains ahead at `13b1315d1395`; this phase did not apply it. Readiness confirms connectivity, not full schema compatibility. The empty live catalog is real, so live product cards require later authorized catalog data; no fallback products were presented as real stock.

Later owner-authentication, checkout/payment, stock, reporting and exchange work remains pending. L1 completion here means the agreed terminal-only diagnosis, shell repair and control inventory, not a claim that all future commerce controls are complete or that the site is launch-ready.

## Phase A ? owner authentication implemented

Date: 2026-10-13. Verification remained terminal-only as requested.

### Delivered behavior

- Controlled CLI owner provisioning with salted PBKDF2-SHA256 hashes and no default credentials. Password reset revokes the owner's sessions.
- PostgreSQL-backed opaque sessions: HttpOnly/SameSite cookies, Secure host-prefix cookies in production, expiry, rotation, logout revocation and restart persistence.
- Cookie authorization on every admin route; legacy API-key/Bearer access rejected. Origin checks, CSRF protection, exact-origin CORS and atomic account/IP login limits. Auth responses never echo submitted passwords; SQL parameters are hidden from debug logs.
- Console username/password form, inline errors, session restoration, expiry handling and confirmed logout. Removed browser shared-key entry and cleared legacy storage. Stock adjustment audit records now use the authenticated owner.
- New additive migration `6a1e9b32c704` creates credentials, sessions and login counters. Historical migrations were not rewritten.

### Evidence

| Check | Result |
| --- | --- |
| Full backend suite | 182 passed in 76.03s; one existing Starlette/AnyIO deprecation warning |
| Full frontend suite | 76 passed |
| Production frontend build | Passed; 27 modules |
| Authentication coverage | Missing/forged/expired/revoked sessions, inactive owner, password reset, cookie rotation, production flags, origin/CSRF rejection, generic failures, account/IP limits and concurrent atomic counters |
| Console DOM coverage | Incorrect login, cleared password, successful login, restoration, failed/successful logout and expired session |
| Disposable migration verification | Upgrade/downgrade/re-upgrade passed; an existing SAMPLE user row survived |
| Real HTTP verification | Login, CSRF rejection, session persistence across API restart and logout revocation passed |
| Local services after upgrade | 22 storefront/API HTTP checks passed; six additional checks confirmed session/admin 401 and no-store headers directly and through Vite, plus current authentication source |
| Source/bundle and whitespace | No legacy key headers/helpers or default owner passwords found in frontend source/build; `git diff --check` passed |

Evidence: `phase_a_auth_verification.json` and `phase_a_local_http_checks.json`. The verification database contains only SAMPLE data and was retained. An initial full-suite run was invalidated by an overlapping test process dropping their shared disposable tables. The fixture now obtains an advisory lock before creating/dropping tables; the clean sequential full run above passed. Development was unaffected by that test overlap.

### Local installation and data preservation

After disposable migration verification, development was upgraded from `e5c83f14a091` through the existing additive `13b1315d1395` revision to `6a1e9b32c704`. All 16 preexisting table counts remained zero; the three new authentication tables are empty. See `phase_a_development_before.json` and `phase_a_development_after.json`. No business records were seeded, reset, truncated or deleted. This is a row-count comparison, not a full database checksum.

The local API was restarted with the updated implementation on port 8000; the existing Vite service remains on port 3000. No development owner was created: choose credentials using the interactive command in `phase_a_owner_auth_runbook.md`. No password should be sent through chat or checked into source.

Native browser cookie handling, rendering and visual behavior remain unverified. Public checkout remains disabled. Authentication completion does not complete fulfillment, payments or later commerce repairs; Phase B is next.

## Phase B — checkout idempotency and stock concurrency implemented

Date: 2026-10-13. Verification remained terminal-only as requested.

The order endpoint now requires a checkout cookie and attempt key. It fingerprints the normalized whole request and stores the fingerprint with the cookie hash on the order. PostgreSQL transaction locks serialize duplicate keys across workers. Exact retries return the order; changed payloads or another checkout cookie receive 409 without customer order data. An existing historical key without binding cannot be replayed. The frontend keeps a pending key and payload across reload, retries after response loss, and lets a confirmed checkout reopen as a fresh form.

Order headers, lines, coupon usage and reservations remain one database transaction. Coupon usage limits are checked with a row lock. Multiple inventory balances are locked in stable order; reservations check stock under lock. Stock adjustments also lock the balance and reject reductions below active holds.

| Check | Result |
| --- | --- |
| Backend suite | 190 passed; one existing Starlette/AnyIO deprecation warning |
| Frontend suite and production build | 78 passed; build passed with 27 modules |
| Real PostgreSQL races | Simultaneous duplicate key yields one order and hold; last-unit buyers yield one order; reversed two-item order completes without deadlock; duplicate coupon usage counts once |
| API rollback and security | Second-line failure leaves no order or hold; changed/foreign retries 409; missing session 428; missing key 422; untrusted origin 403; adjustment below holds rejected |
| Lost response and reload | Node tests retry the exact key/payload, including after module reload; changed unresolved payload blocked |
| Disposable migration | `b79e3a2f0d61` upgrade/downgrade/re-upgrade passed; an existing SAMPLE order survived |
| Local development | Upgraded from `6a1e9b32c704` to `b79e3a2f0d61`; all 19 existing table counts unchanged (zero before and after); API restarted on port 8000 |
| Local HTTP | 22 storefront/API checks passed; checkout-session remains 503 directly and through Vite while public checkout is disabled |

Evidence: `phase_b_migration_verification.json`, `phase_b_development_before.json`, `phase_b_development_after.json` and `phase_b_local_http_checks.json`. Test databases contain only SAMPLE data and were retained. The development comparison covers table counts and revision, not a database checksum. No browser was opened, so native browser cookie behavior and visual interaction remain unverified. Public checkout remains disabled; payment and fulfillment corrections begin in Phase C.
