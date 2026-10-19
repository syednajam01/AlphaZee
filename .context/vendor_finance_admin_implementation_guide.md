# AlphaZee: vendor stock, finance and configurable admin

> Latest owner refinement: `.context/vendor_stock_portal_implementation_guide.md` specifies optional product-vendor linking, AlphaZee-managed inventory and the stock-only vendor portal. Apply it within VF0/VF3/VF5/VF6; preserve progress and avoid duplicate systems.

Owner implementation brief, 2026-10-20. For Antigravity: implement VF0–VF8 sequentially, verify each phase, and record results in `.context/vendor_finance_admin_progress.md`. This is implementation guidance, not evidence that these features exist. Preserve the completed media work and all concurrent edits.

## 1. Decisions and scope

**Confirmed: AlphaZee bears RTO and customer-return costs.** Do not deduct these costs from vendor payouts or charge customers automatically. This does not determine whether a vendor must accept returned goods, credit a purchase, replace a defective item, or when AlphaZee owes the vendor. Those are separate agreements.

The owner initially handles customer contact, vendor confirmation, pickup and rider dispatch manually. Vendors need only a restricted stock-update experience. A full marketplace, vendor order picking, split shipments and POS synchronization remain out of scope.

“Fully customizable admin” means durable settings for supported business rules, storefront content/appearance and dashboard presentation, through usable forms. It does not mean editable accounting formulas, arbitrary code execution, bypassable permissions or unrestricted production switches.

Read `.agent/AGENTS.md`, `.context/vendor_stock_and_money_review.md`, `.context/brand_voice_and_story_guide.md`, `.context/admin_media_acceptance_report.md` and its actual evidence. Correct the media report's invalid checkout probe: test the real order route from the current router with valid test input and required headers; a 404 from `/api/v1/checkout/orders` is not containment proof.

Preserve integer paisas, purchase-time snapshots, audited holds, bank instruction/funds-review rules, private customer access and lab isolation. No owner reset, development fixture insertion, volume removal, production deployment or public checkout release. New migrations must extend the actual current head; do not edit previously applied migrations.

## 2. Required owner screens

| Screen | Minimum outcome |
| --- | --- |
| Dashboard | Movable/hideable KPI cards, saved date/filter presets, operational alerts and reset-layout action. Financial definitions remain visible and fixed. |
| Suppliers | Contact/status, assigned variants, settlement agreement, stock freshness, statement, payable balance, credits and payments. |
| Finance | Separate views for supplier liabilities, actual payments, expenses, courier cash, customer refunds and period reports. |
| Order detail | Customer value, cost snapshots, allocated delivery/return expenses, supplier liabilities/payments and estimated contribution; links to source entries. |
| Stock | Owner-managed counts/holds plus vendor update history and shortage-review queue. |
| Store settings | Branding, approved copy, policy/support content, delivery configuration and supported storefront presentation settings. |
| Admin preferences | Per-owner navigation favorites/order, table columns, density, default filters, dashboard arrangement and accessible theme preference. |
| Vendor stock page | Separate restricted login, assigned SKU images/options, allocated on-hand, held/available, last update and quantity correction. No customer or financial access. |

Use responsive forms, explicit labels, loading/empty/error states, actionable validation and keyboard navigation. Split new admin work into modules instead of expanding the large `AdminConsole.js` indefinitely. Existing routes and workflow controls must remain usable.

## 3. Contracts and invariants

### Supplier agreements and ledger

Per supplier, support an explicit payable trigger: **manual confirmation**, **confirmed pickup**, **dispatch** or **delivery**, plus due-date terms. Default existing suppliers to **unconfigured/manual-only**; do not invent an agreement or generate historical debt. Manual posting requires an explicit amount, reason and source. Automatic posting stays off until the owner saves a configured agreement. If pickup is selected, introduce a real dated pickup confirmation event; never infer it from dispatch.

Snapshot the chosen rule and supplier/cost/quantity on the relevant transaction. Agreement and wholesale-cost edits affect future transactions only. Maintain immutable posted supplier charges, credit notes, payments, payment allocations and reversals. Store supplier, source order/line/event, amount, currency, effective date, recorded timestamp, actor and reference/reason. Unique source-event keys prevent duplicate posting on retries or repeated status updates.

Partial payments and payment allocations across several charges must work. A payment cannot be allocated beyond its available amount or to another supplier's charge. Show unallocated advances/credits separately; do not hide a credit balance by clamping it to zero. Distinguish a purchase credit from an actual cash refund received from the supplier. Support explicit opening balances with an as-of date and evidence; historical import requires preview and deliberate application.

**Payable balance = opening liabilities + charges − credit notes − allocated payments**, with advances and unapplied credits separately reconciled. Paying a payable changes cash and liability; it must not charge product cost to profit a second time. Corrections use reversals/adjustments, not silent editing/deletion of posted entries. Draft entries may be edited before posting.

### RTO, returns and inventory ownership

Record outbound delivery, RTO transport, customer return transport, replacement delivery, inspection and write-off separately where applicable. AlphaZee pays RTO/return expenses. Purchase credits require evidence of vendor acceptance; do not automatically subtract transport costs or product price from the vendor.

If returned goods remain AlphaZee-owned, record them as owned stock after inspection. They must not incur a second supplier payable when resold. Track the acquisition/stock source needed to distinguish AlphaZee-owned returned units from new vendor supply; the existing supplier mapping alone is insufficient. Cover partial quantities, exchanges and damaged units. Never implement a shortcut that eliminates double payment by losing inventory cost or purchase history.

Do not duplicate existing cost entries: courier settlement deductions may settle an already recorded courier expense. Link settlement/payment evidence to that expense rather than creating another expense. Refund liability and refund payment likewise remain separate.

### Expenses and reports

Record expense category, amount, incurred date, paid date/payment allocation, payee, reference, optional supplier/order/shipment linkage and actor. Categories include packaging, advertising, delivery, RTO, return transport, hosting and other overhead. Historical categories may be archived, not destructively removed. Allocate shared costs explicitly with integer rounding whose allocations sum exactly to the original; unallocated overhead stays visible.

Report these separately:

- Order value, delivered sales, discounts and customer sales reversals.
- Product cost consumed/reversed, inventory write-offs, delivery/RTO/return costs and other expenses.
- Estimated contribution before overhead and recorded operating result after included overhead; disclose omissions. Do not label either final audited/tax profit.
- Bank receipts, rider/courier cash receipts, courier-held money, refunds paid/outstanding, supplier payments and supplier balances.
- Recorded cash movement by cash/bank account and reconciliation differences. Do not label it an actual bank balance without opening balances and reconciled transactions.

Every report displays date basis, range, filters and exclusions. Store timestamps in UTC; default reporting dates to Asia/Karachi with explicit start-inclusive/end-exclusive boundaries. Sales, expense recognition and cash dates differ. Show opening/movement/closing balances for period statements. Drill down to source rows; filtered totals and CSV exports must agree. Escape spreadsheet formulas and enforce authorization on exports.

### Vendor stock access

Use separate vendor credentials/sessions and explicit supplier membership checks on every read/write. Reuse appropriate authentication primitives, but do not provision vendors as owners. Owner can invite/provision, revoke and reset access without exposing passwords in logs. Protect cookies, CSRF, Origin, throttling and session expiry as for existing authenticated workflows.

Vendor sees only assigned SKU identity, image, size/color and stock figures—not retail margins, wholesale costs, other suppliers, customer addresses or order/payment actions. On-hand means units allocated to AlphaZee including units held for its orders; held and available are system-calculated. Preserve version checks and audit trails through the existing inventory service.

A count below active holds creates a recorded shortage requiring owner review; it does not silently lower the balance or cancel reservations. Never silently ignore the report. AlphaZee-owned returned inventory cannot be overwritten by a vendor stock correction. Stock staleness thresholds are owner-configurable; default to an alert rather than automatic cancellation. This feature is manual vendor reporting, not real-time synchronization with shop sales.

## 4. Admin customization boundaries

Separate **store-wide business settings** from **per-owner interface preferences**. Persist both server-side with validation, versions, audit history and reset-to-default for presentation preferences. Unknown setting keys must be rejected; expose supported controls rather than a raw JSON editor.

Store-wide settings:

- Brand logo/media references, tagline, homepage/collection copy, hero configuration and navigation labels/destinations. Reuse the existing media editor; do not build a second playlist system.
- Curated font choices, accessible color tokens, button radius, spacing density and section order/visibility with live mobile/desktop preview. Sanitize URLs and content; no arbitrary HTML/JS/CSS injection.
- Support contacts, privacy/terms, delivery and return content with draft/preview/publish and revision history. Missing terms remain clearly unpublished; no invented promises.
- Shipping coverage, supported flat/threshold-based fees, supplier agreement defaults, expense categories and low-stock/staleness thresholds. Validate conflicting rules. Shipping quotes and order totals must be calculated on the server with rule snapshots, never trusted from the browser.

Settings must show scope and effective time. Changes cannot rewrite existing orders, obligations, returns or payments. Financially consequential changes require a deliberate preview/confirmation in the owner UI. Branding changes must not hide required controls or remove accessibility states. Session/account security, database connections and deployment secrets stay out of ordinary customization. A settings toggle must never bypass the production checkout gate.

The RTO/return cost bearer is AlphaZee under the owner's current decision. Display it clearly; do not add customer/vendor charging as a casual theme/configuration option. Outbound shipping charges and a separate size-exchange delivery fee remain distinct owner decisions; do not invent fees while implementing this brief.

## 5. Implementation phases and exit gates

| Phase | Implement | Required exit evidence |
| --- | --- | --- |
| VF0 — baseline/contracts | Inspect current schema/services/UI and acceptance artifacts. Record source revision and working-tree changes, design ledger/stock-ownership contracts and list unresolved agreements. | Concrete schema/API/UI plan, migration dependencies, existing test/build baseline. Mark commercial unknowns, not guessed defaults. |
| VF1 — agreements/liabilities | Supplier agreement editor, immutable charges/credits, manual posting, opening-balance preview and idempotent event posting. | Tests for each trigger, duplicate events, partial quantities, changed supplier cost, historical preservation and no auto-backfill. Owner browser creates agreement and posts/reverses a charge. |
| VF2 — payments/statements | Partial payments, allocations, advances, supplier refunds, statement and balance drill-down. | Exact totals across multiple charges/suppliers; concurrent allocations cannot overpay a charge; double-submit creates one payment. Owner UI records and reconciles payment. |
| VF3 — stock ownership/returns/expenses | Preserve AlphaZee-owned returned units; implement supported expense records and link existing courier/refund entries. | RTO, partial return, exchange, damage and resale cases prove no duplicate payable/cost/restock. Owner records an expense and sees it once. |
| VF4 — financial reports | Per-order economics, supplier statements, expenses, period and cash reconciliation reports, CSV. | Golden fixtures below reconcile to the paisa; drill-down/export match filtered cards; correct timezone/date basis and explicit exclusions. |
| VF5 — vendor stock-only | Restricted authentication, assigned SKU page, versioned corrections, shortage alerts, owner audit/revocation. | Two vendors tested against each other's IDs; owner APIs denied; below-held/stale/concurrent updates safe; true browser login/save/logout/revocation verified. |
| VF6 — settings/preferences | Store settings, policy draft/publish, validated theme/sections, shipping rules and per-owner dashboard/table preferences. | Actual admin edits survive reload/restart; published storefront reflects supported settings; another owner retains independent preferences; old transactions unchanged. |
| VF7 — integrated acceptance | Current-source tests/builds, migrations, dev/lab/production packaging, restart persistence and role boundaries. | Browser supplier→stock→customer order→owner fulfillment→money→return→report scenario; no public checkout opening; existing media journeys still work. |
| VF8 — owner handoff | Publish concise operating instructions and final evidence register. | Implemented/tested/browser-verified/blocked statuses separated; list remaining business inputs and launch gates. No unsupported “100% complete” claim. |

At each phase: fix failures before dependent work, run meaningful tests, inspect actual browser screenshots/console/network and save evidence under `.local/vendor-finance/<run>/`. Use owner forms for UI acceptance; backend/API setup can prepare fixtures but is not proof those forms work. Do not repeatedly rerun unrelated checks without a reason.

## 6. Mandatory reconciliation fixtures

Use isolated lab/disposable data. These are test assumptions, not production supplier agreements.

1. **Delivered COD:** price PKR 2,000, cost 1,200, delivery 200, packaging 50. Contribution before overhead is 550. Rider collects 2,000 and remits 1,800 while deducting the already recorded 200 delivery fee. Supplier paid 700, then 500: liability 500, then zero. Supplier payments do not reduce the 550 contribution again. Paid packaging leaves net recorded cash movement 550 once all receipts/payments are entered.
2. **RTO before delivery, pickup-triggered purchase:** no delivered sale; cost 1,200 remains payable unless a real vendor credit occurs. Outbound 200 plus RTO 150 are AlphaZee expenses. Sellable goods retained by AlphaZee remain inventory; they are not automatically a second 1,200 expense or a vendor credit. Resale cannot generate another payable for the same acquired unit.
3. **Customer return:** a completed refund creates liability; only payment reduces cash. AlphaZee bears return transport. Resellable/damaged inspection quantities produce the correct inventory/cost treatment. A vendor credit requires its own supporting event; never infer it from the customer refund.
4. **Concurrency/retry:** two simultaneous payments, repeated dispatch, duplicate return completion and repeated vendor stock updates cannot duplicate postings or corrupt holds. Validate multi-supplier baskets and partial quantities without cross-supplier allocations.
5. **Period settings:** an order placed before midnight Karachi time, delivered the next day and paid later appears in the appropriate separate views. Later policy/theme/cost edits do not alter its snapshots. Compare opening + movement = closing for supplier and cash statements.

Also verify archived products/suppliers preserve evidence, report links do not reveal other vendors' data, exports handle formula-like text, and unauthorized requests cannot infer private order details.

## 7. Existing code map and handoff

Backend: `models/suppliers.py`, `models/finance.py`, `models/inventory.py`, `models/orders.py`, `models/returns.py`; `queries/inventory.py`, reservation/stock rules; `services/financial_report.py` (active reporting), `finance.py`, `orders.py`, `shipments.py`, `returns.py`; owner/admin APIs, auth dependencies and migrations. Reuse established services and add dedicated modules for new domains.

Frontend: `AdminDashboard.js`, `AdminConsole.js`, `admin/VariantStock.js`, `admin/StockHolds.js`, `admin/CatalogWorkspace.js`, `utils/api.js`, storefront configuration and current media components. Do not replace the backend, introduce a full accounting platform, or migrate frameworks as a side effect.

Final file: `.context/vendor_finance_admin_acceptance_report.md`, with phase status, schema head, exact commands/results, actual UI evidence, known gaps and a daily workflow: **review orders → confirm supplier → dispatch → reconcile rider cash → record supplier payment/expenses → handle returns → review balances**. Include the vendor's short stock-update walkthrough and a list of every configurable admin setting with its scope.

Outstanding owner inputs: supplier payable trigger and due terms; vendor credit/return agreement; outbound shipping fees/coverage; customer return eligibility/window; real support/policy content; opening balances. Implement safe drafts and manual workflows while these remain unresolved. Do not enable automated obligations or publish invented business terms just to finish a phase.
