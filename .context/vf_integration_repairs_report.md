# VF integration repairs — terminal implementation record

Status (2026-10-20): implementation and terminal verification complete; updated development/lab containers are healthy. Browser acceptance is pending and is delegated to Antigravity using `vf_repairs_browser_verification_guide.md`. This is not production certification.

## Changes

- Actual dispatch/delivery and explicit physical pickup now post supplier liabilities in the same transaction. Purchase-time supplier, agreement, trigger, terms, quantities and cost segments are snapshotted. One acquisition key prevents trigger-change duplicates. Historical unsnapshotted purchases remain manual, without invented retroactive debt. Replacement supply is treated according to its real acquisition rather than universally skipped.
- Owned-stock lots retain original acquisition cost through return/RTO inspection, reservations, dispatch, cancellation and resale. Mixed owned/vendor quantities retain exact total cost in integer paisas. Vendor physical counts exclude owned units. Damaged RTO units are included as inventory write-offs.
- Unresolved shortages block both public availability and new reservations. Existing customer holds remain intact; repeated identical reports reuse the alert. Resolution requires a fresh valid physical recount and an owner note.
- Product responsibility and legacy variant assignment controls now agree. Reassignment blocks stock, holds and unresolved shortages. New mappings require explicit costs. Vendor operations check current product assignment, membership, active account and active supplier; history omits private owner notes.
- Report sales use actual delivery dates, returns use return dates, and day windows are start-inclusive/end-exclusive in Karachi time. Independent freight adds rather than using `max()`; linked expense evidence is deduplicated. Mixed acquisition costs, vendor refunds/advances, signed ledger reversals, current outstanding-balance labels and filtered CSV exports are handled explicitly.
- Server-side delivery quotes/coverage/thresholds and rule snapshots are connected to checkout. A confirmation step displays the total; changed totals are rejected. Existing delivery defaults are unconfigured until the owner explicitly activates them. Normal/public checkout remains subject to the original containment gate.
- Saved owner preferences now affect actual theme, table density, analytics date presets, sidebar order and overview-card order/visibility. Store settings edits support stale-version checks; storefront font/radius settings are applied. Hiding an announcement cannot remove the lab SAMPLE label.
- Additive migration: `a81f92c6d430`, after `6e4a2b8d0c1f`. It backfills only unambiguous legacy vendor responsibility. Existing returned stock is flagged for explicit ownership review rather than guessing how many returned units remain. The owner can record reviewed lots/costs through the variant stock panel without changing total physical units.

## Test safety correction

VF5–VF7 previously used `SessionLocal()` directly and could write to the application database. The initial run exposed this. It was stopped; fixtures now use the guarded disposable transaction, and a global test guard rejects application-engine queries. A new runner creates a fresh random `_test` database for every verification run.

That stopped run created five test owner logins and six pairs of test products/suppliers in development. The exact five logins were disabled and their sessions revoked. The exact 12 products were checked for order references (none), archived, and their 12 suppliers/vendor accesses disabled. Existing business records were preserved. These quarantined artifacts were retained rather than deleting historical rows. No further regression run is permitted to use the application database.

## Verification register

| Check | Result | Evidence / repeat command |
| --- | --- | --- |
| Full backend suite, fresh disposable database | 321 passed in 407.67s | `.local/vf-full-321-pass.txt` and `.xml`; `backend\.venv\Scripts\python.exe backend/scripts/run_isolated_verification.py` |
| Final application source: VF1–VF7, repairs, concurrent payment and financial regressions | 63 passed in 218.79s | `.local/vf-focused-63-pass.txt` and `.xml`; pass the nine VF/concurrency modules plus `test_financial_reporting.py` to the runner |
| Added per-order return/RTO economics and cash reversal assertions | 12 repair tests passed in 63.34s | `.local/vf-terminal-verification.txt` and `.xml`; runner argument `backend/tests/test_vf_integration_repairs.py` |
| Frontend | 137 passed; final Vite production build passed | `cd frontend`, `npm.cmd test`, `npm.cmd run build` |
| Migration with legacy data | Upgrade, downgrade, reupgrade passed; old returns flagged, no fabricated lots/debt | `backend\.venv\Scripts\python.exe backend/scripts/verify_vf_integration_migration.py` |
| Development, lab, production container builds | All passed; production images only, no deployment | `docker compose --env-file .env.docker.local build api migrate web`; lab uses `-f compose.checkout-lab.yml`; production uses `--env-file .env.production.example -f compose.prod.yml` |
| Live HTTP isolation/auth guards/readiness | Passed through web proxy and direct API on both stacks | `.local/vf-runtime-verification.json`; `backend\.venv\Scripts\python.exe backend/scripts/verify_vf_runtime.py` |
| Lab restart persistence | Same migration, enabled `syed123`, 78 orders and one settings row after DB/API restart | Direct PostgreSQL count checks before/after; no password reset or new business fixtures |
| Scoped whitespace checks | Passed | `git diff --check -- .agent .context backend/app backend/tests backend/scripts backend/alembic frontend` |

The full suite preceded the last reporting refinements; the final 63 regressions cover the updated application source, followed by 12 strengthened repair tests. Counts overlap and must not be added together. Backend runs report one existing Starlette/AnyIO deprecation warning. Two temporary verification mistakes (a helper returning a tuple and an incorrect vendor-session URL) were corrected before the final passes. No browser was opened.

## Local rollout and backups

- Both databases now report migration `a81f92c6d430`. Both Compose stacks report healthy DB/API/web services; migration services exited successfully.
- Development: `http://127.0.0.1:13000`, API `18000`; lab: `http://127.0.0.1:13001`, API `18001`. An earlier launch had development on default 3000/8000; using `.env.docker.local` restored the documented ports.
- Actual normal order creation, quote and checkout-session endpoints return **503**, both through the frontend and direct API. Lab checkout-session returns **200**. Owner/vendor session endpoints reject anonymous access; `/admin` and `/vendor` serve their page shells. Authenticated login and rendered UI acceptance remain browser tasks; a shell response is not proof of a usable dashboard.
- Quiet-window backups are in ignored `.local/vf-repair-backups/`: `normal.dump`, `normal-media.tar`, `lab.dump`, `lab-media.tar`. PostgreSQL archive tables of contents are readable. Full restore rehearsal is still a staging/operations task; these checks do not claim it was performed.
- No volumes were removed, development was not renamed, production was not started, and existing account passwords were not reset. Protected historical pytest artifacts were left untouched.

## Acceptance and business boundaries

Public checkout and production deployment are not authorized. Real vendor agreements, opening balances, delivery coverage/fees, support contacts and published policies still need owner confirmation. Explicitly review any flagged historical stock before selling it; recorded acquisition snapshots cannot reconstruct unknown past supplier debt. Browser acceptance, visual quality and device interaction remain pending. Advanced marketplace/POS features, arbitrary accounting formulas, arbitrary table-column builders and unrestricted admin code execution remain outside this milestone. Customization supports the implemented forms and presets, not unlimited executable customization.

Next: feed `.context/vf_repairs_browser_verification_guide.md` to Antigravity. It must create `.context/vf_repairs_browser_acceptance_report.md` and update both finance/portal acceptance reports with real UI results, failures and omissions. Do not reuse earlier VF7 helper-based proof as repaired end-to-end acceptance.
