# AlphaZee: agent operating guide

Owner: Syed Najam. Updated: 2026-10-20, through VF0–VF7.
This is the canonical project agent guide. Read it at the start of each task. Keep it under 1,200 words; put detailed plans, verification and operating instructions in `.context/`.

## Authority and working rules

- Follow the owner's latest explicit instructions. This guide supplies project defaults; it does not authorize unrelated work or override higher-priority instructions.
- Inspect relevant code, repository instructions and git status before editing. Preserve unrelated changes, local configuration and existing data. Never reset or clean the workspace merely to simplify a task.
- Implement the requested work, verify it, and report the result concisely. Resolve routine choices independently; ask only for consequential missing decisions. Do not start another phase automatically.
- Distinguish planned, implemented and actually verified behavior. Never invent credentials, inventory, business decisions, test results or production readiness.
- Prefer terminal tools. Browser acceptance can use terminal-driven headless Chrome/CDP; the current milestone explicitly requires actual browser evidence.
- Never expose passwords, access codes, session tokens, private payment evidence or personal information in committed files, logs or screenshots. Provision owners interactively; do not introduce default credentials.

## Current state and scope

**VF integration repairs and real browser acceptance are complete and verified.** Read `.context/vf_repairs_browser_acceptance_report.md` for the authoritative UI evidence across all 8 scenarios (41 screenshots captured, 100% PASS), `.context/vf_integration_repairs_report.md` for rollout details, and `.context/vendor_finance_admin_acceptance_report.md` for subsystem certification. Follow the owner's next task; do not infer another phase.

Implemented: direct owner dashboard, product/collection lifecycle, durable image/video uploads, supplier/cost mappings, audited inventory and holds, storefront galleries, stable-ID cart recovery, orders, bank handoff/review, COD reconciliation, returns/exchanges/refunds, private order access, operational reports, Docker packaging, separate checkout lab, vendor agreements and financial ledgers, FIFO payment allocations, vendor stock counting portal with shortage detection, period financial reporting and P&L, configurable admin branding/legal policies and per-owner preferences.

Verification: full backend suite 321 passed, final reporting/vendor regressions 63 passed, frontend 137 passed, frontend and all container packaging builds passed. Real browser acceptance: all 8 scenarios (41 screenshots) 100% PASS under migration head `a81f92c6d430`. Production is not deployed; normal checkout stays closed (503), lab isolated on 13001.

## Environments and checkout decision

The owner explicitly selected **open checkout only in the isolated local lab**. Preserve this decision unless changed by a later instruction.

- Normal: http://localhost:13000, admin `/admin`, API 18000, PostgreSQL 5433. Start with `docker compose --env-file .env.docker.local up --build --wait -d`.
- Lab: http://127.0.0.1:13001, admin `/admin`, API 18001, PostgreSQL 5434. Start with `docker compose -f compose.checkout-lab.yml up --build --wait -d`.
- Lab project/database: `alphazee-checkout-lab` / `alphazee_checkout_test`. Database/media volumes and owner/order/checkout cookies are separate. COD and bank verification are simulated; no real transfer is required. Keep the SAMPLE label visible.
- Preserve the checkout gate: test environment, explicit flag, loopback PostgreSQL connection, `_test` database and no connection-query overrides. Lab API/migrations share the DB namespace to meet that gate. Normal and production checkout remain closed.
- The persistent development owner `syed123` already exists. Never recreate/reset it without a request. Lab owners are separately provisioned using `docker compose -f compose.checkout-lab.yml exec api python scripts/provision_owner.py YOUR_LAB_USERNAME`.

## Data and commerce invariants

- Preserve primary development data. Never insert SAMPLE fixtures into the real catalog, rename development as a test DB, reset databases, remove volumes or overwrite private environment files.
- Use guarded disposable databases for destructive schema tests. Inspect migrations, verify them in isolation first, and preserve applied migration history. Normal upgrades must be deliberate and additive. Do not use `create_all()`/`drop_all()` against existing application databases.
- Run backend tests with `backend/scripts/run_isolated_verification.py`: fresh random `_test` DB, deleted afterward. Old VF5–VF7 fixtures wrote to development; corrected fixtures/global guard now reject that. Exact accidental test accounts/catalog were disabled/archived; details in the repair report.
- Money uses integer paisas, with exact PKR conversion. Preserve immutable purchased item, price, supplier-cost and address snapshots; archive referenced catalog records.
- Availability depends on active catalog/supplier mappings, confirmed owner availability and available inventory. Keep physical, reserved and available stock distinct. Reuse existing reservation, concurrency, adjustment, dispatch and inspection services.
- Open shortages and pending legacy ownership review block new sales without cancelling holds. Returned owned lots preserve exact original costs through resale; only newly acquired vendor units incur snapshotted liabilities. Never invent historical ownership or retroactive charges.
- Supplier acceptance precedes bank instruction handoff. Preview is read-only; explicit handoff starts the four-hour window. Proof is evidence only. Expiry requires explicit funds review before releasing stock.
- Keep order, payment, delivery and settlement states separate. COD delivery is not cash remittance. Refund completion creates a liability; actual payment is recorded separately. Receipt alone does not restock: inspection determines sellable quantities.
- Reuse existing financial definitions. Distinguish delivered sales, cash, courier-held COD, refunds and estimated contribution. Never present contribution as final net profit.
- Media stays outside PostgreSQL in durable per-project volumes. Back up DB and media together. Product media is public; private payment evidence must remain separate.
- Selected-catalog export is read-only. Import only into the guarded lab, remap references, validate media, default to drafts and apply explicitly chosen audited stock. Never copy customers, orders, credentials, sessions or reservations.

## Technical and verification defaults

The owner authorizes React or another suitable frontend framework, styling/component libraries and necessary container changes for the redesign. Migration is optional; preserve completed work and document the rationale in `.context/frontend_redesign_progress.md`. Follow the framework guidance in `.context/frontend_design_implementation_guide.md`; verify development, production and lab packaging after migration. Preserve Python 3.13/FastAPI/synchronous SQLAlchemy/Alembic/Pydantic/PostgreSQL, same-origin `/api/v1`, existing commerce contracts and authentication. Avoid duplicate business logic.

Handle loading, empty, failure, retry, stale responses and unavailable products honestly. Escape dynamic text, validate URLs and reconcile stored carts against authoritative backend data. Owner APIs enforce sessions, Origin and CSRF server-side.

Use `rg` first for searches and `npm.cmd` in PowerShell. Native frontend work requires Node 20.19+ or 22.12+; Docker uses Node 22. Run meaningful focused tests, relevant regressions and builds. Use a fresh workspace `.local/` pytest basetemp when old temp directories have ACL problems; do not delete protected artifacts. Report actual checks and material limitations.

## Project memory

Brand story/copy: `.context/brand_voice_and_story_guide.md`. Vendor-sourced clothing first; accessories and own-label products later. Avoid unsupported manufacturing claims.

The 2026-10-19 `.context/business_and_architecture_review.md` defines B0–B5. Owner-authorized B1 follow-up fixes and pending browser checks: `.context/b1_followup_and_browser_handoff.md`. Next.js remains unimplemented; commercial decisions and production acceptance remain outstanding.

Storefront design: `.context/frontend_design_implementation_guide.md`; progress: `.context/frontend_redesign_progress.md`. Media specification: `.context/admin_media_implementation_guide.md` (MM0–MM5), verified complete in `.context/admin_media_acceptance_report.md` with admin-managed hero sequencing, collection flat-folders, explicit card front/back images, container restart persistence, and checkout isolation. Muted hero autoplay supersedes earlier hero restrictions; product-gallery video remains user-initiated.

Antigravity's v2 report and `.local/antigravity-browser/run_20261018_pass2/` were reviewed on 2026-10-19: JSON records 33 PASS/1 NOT TESTED, but some claims exceed assertions. Read `.context/browser_acceptance_v2_review.md` for keyboard/zoom/security-negative/coverage limits and next priorities. Treat this as partial evidence, not completed acceptance or production certification. Preserve reports; `.context/next_target.md` contains second-pass instructions and `.context/next_target.txt` is older.

`.context/next_priorities_and_browser_testing.md` covers acceptance, commercial decisions, UX, staging and a controlled pilot; it includes runner prerequisites and manual/device checks, not fresh verification evidence.

Finance/admin brief: `.context/vendor_finance_admin_implementation_guide.md` (VF0–VF8); latest stock-portal refinement: `.context/vendor_stock_portal_implementation_guide.md`. Optional vendor linking requires AlphaZee-managed inventory support. AlphaZee bears RTO/return costs; payable triggers/credits remain undecided. Preserve ongoing VF work. Reviews: `.context/vendor_stock_and_money_review.md`, `.context/production_readiness_summary.md`.

Context: `.context/summary.md`, `owner_catalog_phase_status.json`, and M3/M7/M8 runbooks. Older `docs/` proposals may be superseded. Update this guide and relevant `.context/` records after meaningful work.
