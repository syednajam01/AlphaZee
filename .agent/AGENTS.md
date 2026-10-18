# AlphaZee: agent operating guide

Owner: Syed Najam. Updated: 2026-10-15, through M9.
This is the canonical project agent guide. Read it at the start of each task. Keep it under 1,200 words; put detailed plans, verification and operating instructions in `.context/`.

## Authority and working rules

- Follow the owner's latest explicit instructions. This guide supplies project defaults; it does not authorize unrelated work or override higher-priority instructions.
- Inspect relevant code, repository instructions and git status before editing. Preserve unrelated changes, local configuration and existing data. Never reset or clean the workspace merely to simplify a task.
- Implement the requested work, verify it, and report the result concisely. Resolve routine choices independently; ask only for consequential missing decisions. Do not start another phase automatically.
- Distinguish planned, implemented and actually verified behavior. Never invent credentials, inventory, business decisions, test results or production readiness.
- Prefer terminal tools. Browser acceptance can use terminal-driven headless Chrome/CDP; the current milestone explicitly requires actual browser evidence.
- Never expose passwords, access codes, session tokens, private payment evidence or personal information in committed files, logs or screenshots. Provision owners interactively; do not introduce default credentials.

## Current state and scope

**M0–M9 are complete for the local implementation milestone.** There is no automatically authorized next phase; follow the owner's next task. The old October 9 database pause is obsolete: subsequent owner instructions authorized migrations, commerce, authentication, media management and the completed phases.

Implemented: direct owner dashboard, product/collection lifecycle, durable image/video uploads, supplier/cost mappings, audited inventory and holds, storefront galleries, stable-ID cart recovery, orders, bank handoff/review, COD reconciliation, returns/exchanges/refunds, private order access, operational reports, Docker packaging and the separate checkout lab.

Latest recorded M9 verification: 260 backend tests, 108 frontend tests, 145 commerce/mobile/archive Chrome checks plus 83 authoring/storefront checks, production frontend build, normal/production/lab image builds, migration comparison/cycle and archived-history restart persistence. One existing AnyIO deprecation warning was recorded. Vite 7.3.7/esbuild 0.28.2 returned zero npm advisories at verification. These are dated results, not substitutes for checking later changes. Migration head: `f27b6d91c083`.

M9 completed purchased-product archive/history, mobile checkout/offline recovery, partial COD and replacement-RTO acceptance. The owner guide is `.context/m9_owner_handoff.md`; detailed results are in `m9_implementation_report.md`. Production has not been deployed. Domain and hosting proposals in older documents are not verified deployments.

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
- Money uses integer paisas, with exact PKR conversion. Preserve immutable purchased item, price, supplier-cost and address snapshots; archive referenced catalog records.
- Availability depends on active catalog/supplier mappings, confirmed owner availability and available inventory. Keep physical, reserved and available stock distinct. Reuse existing reservation, concurrency, adjustment, dispatch and inspection services.
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

The 2026-10-19 `.context/business_and_architecture_review.md` reviews redesign evidence and defines B0–B5 priorities. Next.js remains unimplemented; resolve product-content correctness and verification gaps before launch. Recommendations are not implementation authorization.

The 2026-10-19 `.context/frontend_design_implementation_guide.md` is the Antigravity storefront redesign brief: visual tokens, product URLs, responsive media/purchase flows and U0–U5 browser gates. Expected progress file: `.context/frontend_redesign_progress.md`. The brief is not implementation evidence; preserve checkout/data boundaries. It supersedes the testing-only handoff for the requested design work.

Antigravity's v2 report and `.local/antigravity-browser/run_20261018_pass2/` were reviewed on 2026-10-19: JSON records 33 PASS/1 NOT TESTED, but some claims exceed assertions. Read `.context/browser_acceptance_v2_review.md` for keyboard/zoom/security-negative/coverage limits and next priorities. Treat this as partial evidence, not completed acceptance or production certification. Preserve reports; `.context/next_target.md` contains second-pass instructions and `.context/next_target.txt` is older.

The 2026-10-18 guidance is `.context/next_priorities_and_browser_testing.md`: baseline acceptance, commercial decisions, mobile buying-journey UX, launch/staging verification and a controlled pilot. It includes current automated runner prerequisites plus manual/device/usability checks; it is guidance, not newly executed evidence or implementation authorization.

The 2026-10-15 readiness assessment is `.context/production_readiness_summary.md`. Core workflows are implemented, but public checkout release, Azure acceptance and business setup remain. Vendor payable/payout accounting is absent; customer checkout currently defaults to zero shipping. Treat these as assessed gaps/decisions, not newly authorized implementation phases.

Read `.context/summary.md`, `.context/owner_catalog_phase_status.json`, `.context/owner_dashboard_catalog_media_implementation_plan.md` and `.context/next_target.txt` for task context. Use phase guides and JSON evidence, especially `m8_checkout_lab_runbook.md`, `m7_operations_runbook.md` and `m3_media_runbook.md`.

Older `docs/` records may describe superseded pauses/proposals. Reconcile them with explicit owner decisions and current evidence. Update this guide and relevant `.context/` documents after meaningful work; keep detailed histories out of this file.
