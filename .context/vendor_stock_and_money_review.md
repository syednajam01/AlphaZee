# AlphaZee: vendor stock, manual fulfillment and money reporting

Reviewed 2026-10-19 against current supplier/auth/inventory/order and financial-report code. This is a capability review and recommended scope, not a newly implemented feature or fresh browser/database acceptance. Antigravity's media work can continue independently.

## Direct answer

**Your manual starting model is workable, but “every money report” and vendor-controlled stock updates are not fully implemented.** You currently operate the shop through owner admin. Vendors supply you with products and availability; they do not have a finished restricted login, stock-update screen or order-picking inbox.

A small vendor stock-only screen is a sensible next feature. It is much smaller than a marketplace portal, but it still needs proper account isolation, stock rules and audit history. Equally important for your stated needs is a **supplier amounts-owed/payments ledger**: the current product-cost calculation does not tell you who has actually been paid.

## What exists today

| Your question | Current status |
| --- | --- |
| Can I register a shop/vendor? | Yes: owner-managed supplier records and active/inactive status. |
| Can I connect its products and buying prices? | Yes: supplier-to-variant mappings and wholesale costs; purchases retain cost/supplier snapshots. A variant has one active supplier mapping in the current model. |
| Can I update stock myself? | Yes: owner stock adjustments, version/conflict checks, audit reasons and physical/held/available quantities. |
| Can the vendor update only its own quantity? | **Not as a usable completed feature.** A `SupplierMembership` table exists, but that is not a vendor authentication/authorization workflow. The inspected operational endpoints require an owner session. |
| Does stock automatically sync with its physical shop? | **No.** No connected shop POS/inventory feed was found. Updates entered into AlphaZee cannot detect unreported offline sales. |
| Can a vendor receive/pick/accept orders on the website? | **No dedicated vendor workflow.** You contact the vendor and record supplier acceptance in owner admin. |
| Can I manually manage dispatch, delivery and failed delivery? | Yes: shipment status, tracking/reference and recorded shipping costs; RTO receipt and inspection/restocking are supported. Your rider's actual handoff/cash process still needs rehearsal. |
| Can I distinguish delivered orders from received COD cash? | Yes: delivery, courier-held COD, partial/final cash receipts and deductions are separate. |
| Can I see returns/refunds? | Yes: completed refund liabilities, recorded refund payments, outstanding refunds and return inspection are represented. |
| Can I see supplier product cost and estimated earnings? | Yes: cost snapshots, delivered sales, recorded courier/RTO costs and estimated contribution. This is not final net profit. |
| Can I see vendor payable, paid, unpaid and statements? | **Missing as a complete ledger/reporting workflow.** Cost of goods is not a supplier payment record. |
| Is every business expense and period report covered? | **No.** The current finance summary is an all-time operational snapshot, not a full accounting system. Advertising, packaging, platform/hosting costs, salaries, tax and other overhead are not comprehensively accounted for. |

The active admin financial route uses `services/financial_report.py`; do not infer current behavior from the older `services/analytics.py` profit function or its comments.

## How to operate manually at the beginning

1. Agree the exact item/size/color, vendor price, quantity allocated to AlphaZee, collection arrangement, payment timing and failed-delivery/return responsibility with the shop. Record the supplier mapping and cost before taking orders.
2. Publish only quantities the vendor can reliably fulfill. Check new orders in owner admin and contact the vendor. An AlphaZee reservation alone does not reserve an item at the vendor's physical shop.
3. Get confirmation that the exact units are put aside. Then record supplier acceptance. If unavailable, resolve the order honestly through the supported cancellation/review process; do not dispatch a different item silently.
4. Contact the customer. For bank transfer, record the actual instruction handoff after supplier confirmation; verify received funds before dispatch. For COD, agree collection with the rider.
5. Record dispatch/reference and delivery cost. Give the rider only the details needed for delivery. For a basket from several shops, start with you consolidating it into one shipment; do not assume independent vendor parcels are already supported.
6. Record delivery and, separately, the actual cash received and any evidenced deductions. For RTO, record return receipt, cost and physical inspection before restocking sellable units.
7. Record supplier payments in an external ledger until the app supports them. Reconcile orders, rider cash, refunds and supplier balances daily. The app cannot know about a phone agreement, payment or stock change you never record.

Do not give vendors your owner password. It exposes other vendors, customers, pricing and financial operations. A stock-only experience needs restricted server-side permissions, not simply hidden admin buttons.

## Keeping vendor stock synchronized

**Best initial arrangement: a quantity explicitly allocated to AlphaZee.** If the shop commits three black-M shirts to you, its staff must honor that allocation. Listing the entire shop stock while it also sells offline creates overselling risk.

If allocation is impossible, agree a reporting routine: start-of-day check, immediate updates after offline sales, and confirmation before you promise fulfillment. Start with a conservative quantity/buffer agreed with the vendor. This reduces risk; it is not live synchronization.

Define the quantity field precisely before building vendor access:

- **On hand:** units allocated to AlphaZee and not yet dispatched, including units held for its existing orders.
- **Held:** units already reserved by AlphaZee; computed by the system.
- **Available:** on hand minus applicable holds; computed by the system.

Example: five allocated units, two held → three available. A vendor reporting “three left for new orders” must not overwrite on-hand with three, because the system would subtract the two holds again. Keep the field labels and instructions explicit.

If a new count is below existing holds, the current service rejects it. A future vendor screen must surface an owner-review shortage rather than bypassing that protection or silently cancelling orders. A stale version should require refresh/reconciliation. Show who updated the count and when; decide an inactivity threshold with the owner rather than inventing one.

## Small vendor stock feature: recommended scope

**Include:** owner-provisioned/revocable vendor login; a mobile-friendly list of only that vendor's assigned SKUs, size/color/image; allocated on-hand quantity; held/available display; last update; count correction with reason; save confirmation; owner audit trail and shortage alerts.

**Exclude initially:** order picking, customer addresses, retail price edits, wholesale-cost edits, product publication, refunds, payment actions, other suppliers' data and sales dashboards. Keep vendor accounts distinct from owner credentials. Existing membership records can be reused only with explicit per-request authorization.

Use the current versioned inventory service, not direct balance updates. Test vendor A versus vendor B, revoked accounts, forged IDs, negative/oversized quantities, stale saves, below-held counts and concurrent customer checkout. Verify the stock-only account cannot call any owner endpoint. A database membership row or an obscured URL is not security.

This is **manual stock reporting through the website**, not automatic shop synchronization. A POS/API connector can come later if a vendor actually has a compatible system. Begin with one cooperative vendor before expanding.

## Money: what the dashboard means, and what to add

Current estimated contribution is broadly:

**Delivered sales − completed refund reversals − adjusted product cost − recorded outbound/RTO courier costs − other recorded courier deductions.**

Current “business cash after refunds” is bank customer receipts plus courier cash receipts minus recorded refund payments. **It does not subtract supplier payouts or all business expenses, so it is not your bank balance or spendable profit.** Costs and cash payments must remain separate to avoid subtracting the vendor cost twice.

Illustration only: customer pays PKR 2,000, supplier cost is PKR 1,200, rider cost is PKR 200 → PKR 600 contribution before other expenses. If the rider holds the money, you have not received that cash. If the vendor is unpaid, you still owe PKR 1,200. The eventual vendor payment settles the liability; it must not charge another PKR 1,200 against the same product margin.

For the reporting you want, add these owner-facing capabilities:

| Addition | Minimum useful content |
| --- | --- |
| Supplier ledger | Supplier/order references, charge or payable, credits/adjustments, payments, outstanding balance, due dates and evidence/reference. Support partial payments and an audit trail. |
| Per-order economics | Sale/discount/refund, snapshotted vendor cost, delivery/RTO costs and other allocated expenses; estimated contribution with its exclusions shown. |
| Expense records | Dated, categorized packaging, ads, rider payments and other costs; payment reference and allocation where relevant. Avoid counting a courier cost again as an unrelated expense. |
| Reconciliation reports | Supplier balances/statements; delivered versus cash received; rider-held money; customer refunds still owed; period/date filtering and exports. Define whether each view uses order, delivery or payment date. |

Before implementing supplier payables, choose when you owe the vendor: pickup, dispatch, delivery or another agreed event. Decide what happens on cancellation, RTO, damaged items and customer returns. An RTO does not automatically mean the vendor owes you a credit; resellable inventory returning to you is different from returning it to the vendor. Software should record the actual agreement and evidence.

## Recommended sequence

1. Finish current media and storefront acceptance. In parallel, agree allocation/fulfillment/payment rules with the first vendors and use an external supplier ledger.
2. Build the supplier ledger and clear money reports if “everything in the app” is required before launch. Add expense/period reporting in a bounded follow-up; do not call the existing contribution figure final profit.
3. Add the small vendor stock-only feature, initially for one vendor. It can proceed alongside the ledger if resources allow. Keep owner-managed orders and customer contact.
4. Defer a full vendor portal, order picking, automated POS sync and split shipments until operating volume justifies them.

**Recommendation:** you are right to keep fulfillment manual initially. Vendor stock-only access is useful, but it is not the only missing feature: supplier payment tracking is essential to the complete money visibility you want. Neither addition should open production checkout automatically.

Evidence inspected: `backend/app/models/suppliers.py`, `models/finance.py`, `dependencies/auth.py`, `queries/inventory.py`, `services/financial_report.py`, `services/finance.py`, admin/owner-stock API routes, and `frontend/src/components/AdminConsole.js`. No vendor feature, financial calculation, live data or media implementation was changed for this review.
