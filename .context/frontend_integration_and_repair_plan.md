# AlphaZee: frontend integration and corrected launch repair plan

Date: 2026-10-13
Status: Phase 0, Phase L1, Phase A, Phase B, Phase C, Phase D/E, Phase G, Phase F and Phase L2 implemented (2026-10-13). Docker containerization was inserted before Phase G at the owner's request. Phase V terminal regression, migration and local HTTP verification passed. The owner explicitly requested no browser use, so browser journeys, visual verification and final launch acceptance remain open. Public checkout remains disabled. See `repair_verification_report.md`, `frontend_control_inventory.md`, `phase_c_payment_runbook.md`, `phase_d_stock_transition_table.md`, `phase_g_runbook.md`, `phase_f_runbook.md` and `docker_deployment_runbook.md`.
Source of requirements: `next_target.txt` in this directory.

This plan supersedes the completion and launch-readiness claims in `launch_blocker_plan.md`. Preserve that file as historical context. Existing implementations are a starting point, not evidence that the corrected requirements pass.

## 1. Outcome and scope

Restore working storefront controls at localhost:3000, complete the owner console integration, and repair the commerce rules required by the updated target. Every visible control must either perform its intended action or clearly explain why it is unavailable. Mutations must persist correctly after reload.

This planning pass inspected source code only. It did not reproduce the reported browser failure, run tests, inspect the running database, or verify the GitHub commit mentioned in the target. No runtime root cause is established yet.

## 2. Evidence from the current workspace

| Area | Source finding | Consequence |
| --- | --- | --- |
| Startup | `frontend/src/main.js` creates all overlays before assembling the page and connects cart/menu listeners | Trace imports and component construction for uncaught exceptions; do not assume every button simply lacks a handler |
| Local API | `frontend/vite.config.js` proxies `/api` to localhost:8000; Compose starts PostgreSQL on 5433 only | Verify all three services and the actual process serving port 3000 |
| Owner access | `utils/api.js` stores a shared admin key in sessionStorage and sends `X-Admin-Key` | Replace browser key entry with owner login and server-managed sessions |
| Dispatch/remittance | `AdminConsole.js` renders both forms without corresponding submit handlers | Complete submit, cancel, validation, error and refresh behavior after backend contract repairs |
| Inventory | Current console provides inventory display without a stock adjustment workflow | Add audited adjustments through protected endpoints |
| Navigation | Search currently scrolls to products; footer includes `#shop`, `#track`, `#privacy`, `#terms`; WhatsApp has a placeholder destination | Check destinations and implement, relabel or explicitly disable unfinished actions |
| Checkout | Checkout submits to the order API; header still says checkout disabled | Verify and enforce an actual server-side gate; presentation text is not enforcement |
| Payments | Bank configuration contains placeholders; deadline logic begins at order creation | Gate transfers and move deadline initiation to the corrected instruction event |
| Stock | Shipment paths can advance earlier reservation stages automatically | Replace fabricated transitions with validated allocation-specific transitions |
| Returns/exchanges | Phone matching is used for ownership; replacement reservation references the original line | Introduce secure order access and independent shipment item allocations |
| Reports | Partial remittance can still receive `remitted` status | Introduce explicit settlement arithmetic and distinct reporting measures |

The workspace contains extensive existing uncommitted work. Preserve it and inspect diffs before editing. Do not revert unrelated changes or rewrite applied migrations.

## 3. Execution order

1. Phase 0: baseline, data protection and checkout containment.
2. Phase L1: reproduce startup failure, restore basic interactions, inventory controls.
3. Phase A: owner login and console authentication.
4. Phase B: whole-order idempotency and reservation concurrency.
5. Phase C: supplier confirmation, payment instructions and expiry review.
6. Phase D/E: consistent stock movement, shipment transitions and inspected returns.
6a. Docker containerization: reproducible development and production stacks, automated migrations, TLS serving and deployment runbook.
7. Phase G: secure customer order access and independently allocated exchanges.
8. Phase F: financial reporting and courier settlement using the corrected lifecycle.
9. Phase L2: finish all remaining frontend integration and persisted browser journeys.
10. Phase V: regression, migrations, browser evidence and release decision.

Frontend wiring accompanies each backend phase; L2 closes remaining gaps rather than postponing all UI work until the end.

## 4. Phase 0 — baseline and containment

- Record working-tree state, runtime versions, test commands, current Alembic revision and intended service ports. Redact credentials from evidence.
- Inspect existing checkout guards. Add a default-off server-side public order-creation gate if missing, expose safe capability flags to the UI, and display an accurate unavailable state. Direct API calls must not bypass the gate.
- Permit checkout exercises only in the isolated local/test setup; keep public checkout disabled through verification.
- Use dedicated disposable targets such as `alphazee_test`, `alphazee_browser_test` and `alphazee_migration_test`. Compare normalized host/port/database against development before fixture creation, migration rollback or cleanup.
- Browser tests must run against a separate API instance configured for the browser database, with the test Vite proxy targeting that instance. Do not redirect the user's normal development API silently.
- Clearly label fixtures `SAMPLE / TEST`; do not seed, reset, truncate or downgrade development data. Do not run `docker compose down -v`.

Acceptance: public submission is rejected server-side, browsing remains usable, test processes demonstrably target isolated data, and existing development records remain untouched.

## 5. Phase L1 — diagnose localhost and inventory all controls

### Diagnose before fixing

Execution amendment: the owner explicitly requested no browser use during L1. Use source inspection, Node DOM regression tests and live HTTP requests instead; record the limits without claiming browser Console, touch, layout or pointer-hit-test evidence.

1. Identify the listener on port 3000 and its working directory; check for Vite port fallback, stale preview servers or another application.
2. Open the actual page in a browser at desktop and mobile sizes. Capture the first Console exception with stack and failing Network requests before clearing cache or restarting anything.
3. Verify HTML, `/src/main.js`, imported modules and CSS load. Trace `DOMContentLoaded`, `initApp()` and overlay constructors. Inspect selectors, missing exports, storage parsing, duplicate IDs and exceptions during setup.
4. Check whether invisible backdrops, pointer-events, stacking order or a stuck modal intercept clicks. Test mouse, touch-equivalent and keyboard activation.
5. Check FastAPI `/api/v1/health` and `/api/v1/ready` directly and through Vite. Health alone does not prove database connectivity. Validate catalog responses and migration compatibility without exposing connection secrets.
6. Reproduce the fault, apply the smallest supported fix, and verify shell controls remain usable when catalog/API requests fail. Display a recoverable error rather than silently swallowing startup failures.

### Control register

Create `.context/frontend_control_inventory.md` during execution. For each actual visible control record selector/location, intended behavior, handler, endpoint, classification (implemented/broken/unfinished/intentionally disabled), persistence expectation and browser result. A handler found in source is not a browser pass.

| Group | Controls to enumerate and exercise |
| --- | --- |
| Header/mobile navigation | Logo, section links, search, cart, menu, close/backdrop, tracking, support link |
| Catalog | Hero slides/CTA, collections, filters, pagination/load-more, product cards, retry/empty states |
| Product details | Images, variants/sizes, quantities, stock availability, add-to-cart, close |
| Cart | Increment/decrement, remove, totals/badge, close, checkout entry, restored cart after reload |
| Checkout | Customer validation, coupon apply, payment choice, submit/retry, confirmation, finish/close |
| Tracking/returns | Secure lookup, order details, return reason/type/quantity, replacement choice, submit, close |
| Footer | Tracking, shop/collections, FAQ, policy links, owner access |
| Owner shell | Login/logout, expiry recovery, sidebar, tabs, refresh, close |
| Owner operations | Supplier creation/confirmation, inventory adjustment, payment review, dispatch, delivery, cancellation, RTO receipt/inspection, refunds, exchanges, coupons, settlements and analytics |

Correct broken anchors and route all tracking triggers through the same flow. Either provide real catalog search or rename the existing scroll action accurately. Leave unavailable support/policy destinations explicitly unavailable until genuine content/configuration is provided; do not invent contact information or policies.

Acceptance: cart/menu/modal controls work without a healthy backend, each visible control is registered, and the observed startup defect has reproducible before/after evidence.

## 6. Phase A — owner authentication

Files: backend authentication dependencies/config/models/routes, `AdminConsole.js`, `utils/api.js`, migrations and authentication tests.

- Introduce an owner identity with securely hashed credentials and controlled owner provisioning; no public owner registration or default production password.
- Provide login, current-session and logout endpoints. Use revocable server-managed sessions in HttpOnly cookies, Secure in production, an appropriate SameSite policy, expiry, session rotation and login rate limiting.
- Protect cookie-authenticated mutations against CSRF, validate origins and keep CORS narrowly configured.
- Remove the browser shared-key workflow and stored legacy keys. Never ship admin secrets in source, VITE variables or browser storage. Any retained service credential must not bypass browser authorization rules.
- Enforce authorization on every privileged endpoint. Show inline login errors, restore valid sessions after reload, and return expired sessions to login without pretending mutations succeeded.

Acceptance: anonymous/expired requests fail; valid owner sessions work; logout revokes access; CSRF attempts fail; browser bundles and storage contain no shared admin secret.

## 7. Phase B — order idempotency and concurrency

Files: order API/schema/service/model, reservation/inventory queries, checkout/API client, new migration and concurrency tests.

- Require a checkout attempt key and persist it across retries, including response loss. A genuinely changed checkout payload starts a new attempt.
- Store a canonical request fingerprint with the key and order result. Same key/same payload returns the original result; same key/changed payload returns a conflict, including simultaneous requests.
- Use database uniqueness, transactions and explicit conflict handling. Order, lines, reservations and coupon usage must commit once or roll back together.
- Bind replay access safely to the submitting checkout session; guessing/reusing keys must not disclose customer information.
- Lock shared inventory rows and use deterministic lock ordering for multiple variants. Recheck availability under lock; include stock adjustments and other competing mutations in the same concurrency design.

Acceptance: concurrent last-unit buyers cannot oversell; concurrent duplicate submissions produce one order; lost-response retries recover that order; changed payload reuse fails; a failed line leaves no partial order or holds.

## 8. Phase C — payment instructions and review

- Keep supplier acceptance and receipt of money as separate recorded events. Confirm actual allocations before inviting transfer payment.
- Serve permitted payment methods from validated backend configuration. Reject bank-transfer selection server-side while real bank details are missing; hide/disable it consistently in the UI.
- Record `payment_instructions_sent_at` only after an actual successful instruction handoff following supplier confirmation. For manual communication, record the owner's explicit sent confirmation and channel; do not equate order creation or merely generating instructions with sending them.
- Start the four-hour deadline from that event. Retry/resend must not silently extend it. Store UTC and display understandable local times.
- Expiry moves the order into payment review. Keep stock held until the owner checks for incoming/pending funds and explicitly resolves release or verified receipt; remove automatic purge/release behavior.
- Serialize payment review, verification and cancellation so races cannot release stock for a payment being accepted. Block transfer dispatch until receipt is verified.

Acceptance: checkout has no premature timer; supplier acceptance alone does not verify money; instructions establish the deadline once; expiry preserves stock pending review; unconfigured transfers and unpaid dispatch are rejected.

## 9. Phase D/E — stock, shipments, RTO and returns

Proposed invariant: deduct physical stock exactly once at dispatch and consume the corresponding sellable hold in the same transaction. Delivery makes no further physical deduction. Returned goods enter quarantine on receipt and become sellable only for quantities that pass inspection.

- Define a transition table for reservation, order, shipment and returned quantities before implementing. Align constraints, services, reporting and UI labels with it.
- Validate actual supplier confirmation and payment gates at dispatch. Delivery may advance dispatched allocations only; it must never fabricate supplier acceptance or earlier fulfillment events.
- Allocate shipment items explicitly. Shipment events act only on those items, not every reservation attached to the parent order.
- Reject cancellation of dispatched quantities. RTO initiation/arrival records logistics only, with no sellable restock at receipt.
- Inspect line quantities as sellable, damaged or unresolved. Enforce received/inspected bounds and restore only accepted quantities, exactly once, to the historical fulfilling supplier variant.
- Record every stock movement with quantity delta, reason, actor and source event. Use transactional locks/unique event references to make duplicate callbacks and concurrent inspections safe.
- Plan additive migration/backfill for existing dispatched/fulfilled records so changing deduction timing cannot deduct old shipments again. Preview reconciliation discrepancies and resolve ambiguous records explicitly.

Acceptance: dispatch deducts once; delivery deducts zero; receipt adds zero sellable stock; partial inspection adds exactly the accepted quantity; repeats add zero; changed active supplier does not redirect restock; damaged stock stays unavailable.

## 10. Phase G — secure order access and exchanges

Implemented 2026-10-13. Terminal-only verification and operations are documented in `phase_g_runbook.md`.

- Replace order-number/phone knowledge as authorization with an unguessable, order-scoped access credential issued securely to the purchaser. Store token hashes, support revocation/expiry and prevent cross-order access.
- Prefer exchanging credentials for an HttpOnly scoped session. Keep tokens out of logs, analytics and referrers. Recovery for lost credentials or historical orders requires a verified channel/owner-assisted process, not phone matching alone.
- Apply the same authorization to tracking/details and every customer return/exchange mutation, with generic failure responses and rate limits.
- Create dedicated replacement fulfillment items linked to the return and replacement variant, with explicit quantity, supplier snapshot, reservation and shipment allocation.
- Separate original and replacement fulfillment states. Default replacement COD to zero; any legitimate additional charge must be separately recorded and must never inherit the original order total.
- Validate return eligibility, quantity remaining, replacement availability and repeated requests. Complete replacement dispatch/delivery/RTO through the same allocation-specific stock rules.

Acceptance: another customer's order cannot be accessed using its phone/number; repeated approval creates one replacement; unavailable replacements fail atomically; replacement dispatch touches only replacement stock and never collects original COD again.

## 11. Phase F — reports, refunds and settlements

- Report order value, delivered sales, customer payments, courier-held COD, business cash received, refunds and expenses separately. Customer COD collection is not business bank receipt.
- Record refund execution separately from return approval/estimated refund. Include actual refund amounts and references in cash reporting; define sales reversals and COGS reversal for returns independently.
- Maintain immutable settlement entries for gross COD, documented courier deductions, net received and outstanding balance. Support multiple partial receipts and references without overwriting prior receipts.
- Reconcile cumulative net receipts plus recognized deductions against expected collectible COD. Legitimate net receipts below order total can be fully settled; unexplained shortfalls remain partial/disputed. Prevent duplicate references, excess settlement and settlement of unrelated shipments.
- Define date basis, PKR minor-unit arithmetic and expense treatment consistently; avoid counting courier deductions twice. Remove misleading profit labels until all required inputs are represented.
- Wire the remittance form to these fields with validation, pending/error/success feedback and persisted refreshed totals.

Acceptance: unpaid/undelivered orders do not inflate delivered sales; COD delivery does not invent bank cash; refunds appear once; valid courier deductions reconcile; unresolved shortfalls remain outstanding; report totals reconcile to fixtures and ledger entries.

## 12. Phase L2 — finish frontend integration

- Complete dispatch submit/cancel handlers, and refine the Phase F remittance workflow where broader owner integration requires it.
- Add inventory adjustments with supplier/variant, signed quantity change, reason and audit result. Refresh physical, held and available quantities after success.
- Wire payment review, supplier confirmation, shipment updates, inspected quantities, refund recording and independent replacement operations.
- Give every mutation pending, success and recoverable failure states. Prevent duplicate clicks while preserving retries. Avoid duplicate listeners after rerender or reopen.
- Preserve cart/form data on failures, reconcile server prices/stock/coupons, and distinguish empty data from a failed request.
- Confirm modal Escape/backdrop/close behavior, focus return, keyboard access, scroll unlocking and mobile navigation. Ensure unavailable actions explain their dependency.
- Revisit the control register until every row has browser evidence or an explicit intentional-disabled reason.

Acceptance: all supported visible controls work; each saved mutation survives reload and is verified through persisted server state; no dummy success or placeholder destination remains presented as operational.

## 13. Phase V — verification and completion evidence

Write regression tests that reproduce each material defect before repairing it. Existing source-string/mocked tests cannot establish browser behavior or PostgreSQL concurrency.

| Verification layer | Required evidence |
| --- | --- |
| Frontend tests | Run `npm test` in frontend; report results and coverage limits |
| Production build | Run `npm run build` in frontend; a build pass is not an interaction pass |
| Backend unit/API | Run relevant tests then the full suite; report mocked and database-backed results separately |
| PostgreSQL integration | Real separate-session contention, duplicate requests, transactional failures, stock/settlement invariants |
| Migration verification | Disposable database only: upgrade from prior schema with fixtures, inspect/backfill checks, rollback of new reversible migrations, re-upgrade; model `create_all()` is insufficient |
| Browser integration | Real browser plus isolated API/database; desktop/mobile; Console and Network evidence; reload persistence |

Browser journeys: browse/filter/product/cart; checkout disabled; permitted isolated COD checkout and lost-response retry; owner login/expiry/logout; supplier confirmation; configured transfer instruction/deadline/review; dispatch/delivery; cancellation rejection; RTO partial inspection; refund; replacement exchange; courier settlement and report reconciliation. Also exercise backend unavailable, invalid form input and authorization failures.

Save `.context/repair_verification_report.md` with per-phase changed files, commands, actual results, database target labels, browser evidence and unresolved issues. Mark skipped checks explicitly. Update outdated README/progress/launch-plan claims to match the verified final behavior.

Completion requires all critical regressions, migration checks and browser journeys to pass, no unresolved startup exceptions, and a complete control register. Public checkout remains disabled until these conditions and the owner's launch decision are satisfied. Real bank details, support contacts and verified recovery-channel configuration are business inputs; keep dependent features disabled until supplied while continuing independent repairs.
