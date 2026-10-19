# AlphaZee: optional product vendor and stock-only portal

Owner refinement, 2026-10-20. This supplements `.context/vendor_finance_admin_implementation_guide.md`, particularly VF0/VF3/VF5/VF6; it does not start a separate competing implementation. Antigravity must read its in-progress finance work, reconcile this specification, and preserve finished media functionality. Add VS0–VS5 subtasks to the existing progress register.

## Mentor's assessment

**This is a good first vendor feature.** You keep control of products, prices, orders, customers and payments. Each shop gets a simple place to update the stock it supplies. A full vendor marketplace can wait.

Three important distinctions:

1. “No vendor” means **AlphaZee-managed inventory**, not necessarily an AlphaZee-manufactured product. Brand/manufacturer and inventory responsibility are separate facts.
2. A product is linked to at most one external vendor in this first version, but stock is counted per size/color SKU. Three black-M shirts and two black-L shirts are separate balances.
3. The portal records the vendor's updates; it cannot detect physical-shop sales by itself. Agree which units the shop makes available to AlphaZee, and require prompt updates when that stock changes.

This guide authorizes the described implementation within existing development/test boundaries. It does not authorize public checkout, deployment, supplier agreements or new commercial promises. AlphaZee continues to bear RTO/customer-return costs under the finance brief.

## 1. Owner experience

### Admin → Vendors

Create the vendor/shop record with name, contact and active status. Separately create or invite its stock user: username, secure credential setup, access status, last login and linked vendor. Provide reset/revoke actions; never show stored passwords. Start with one account per shop in the UI, without designing the database to forbid future staff accounts.

Distinguish **disable login** from **suspend vendor supply**. Disabling credentials revokes sessions; it does not silently delete stock or orders. Suspending supply stops new checkout eligibility for its supply while preserving historical orders, stock evidence and owner resolution actions.

### Admin → Add/edit product

Add a clear field:

> **Who manages this product's stock?**
> - **AlphaZee — no external vendor**
> - **Vendor — choose an active shop**

Explain the effect below it: vendor users can update allocated quantities only; AlphaZee controls everything else. The owner maintains acquisition/unit costs even for owner-managed inventory. No external vendor must not mean missing stock, unlimited availability or an assumed zero cost.

Use searchable vendor selection and an assigned-product list on the vendor detail screen. Product choice applies to all its variants in this version. Adding a new variant inherits its source but starts with zero stock until a real count is entered. Vendor creation remains an owner action; vendors cannot self-register into arbitrary shop memberships.

### Vendor → `/vendor`

Separate login and mobile-first stock screen. Show only assigned products/SKUs: thumbnail, title, SKU, size/color, allocated on-hand, AlphaZee-held quantity, available quantity and last update. Search/filter by name/SKU and stock state; paginate large lists.

Main actions: **Update counted quantity**, reason such as shop sale/restock/count correction, optional note, **Save**, visible result. Add **Report shortage** when the actual count is below holds. Show the vendor's recent update history and logout. No product publication, price/cost changes, order picking, customer details, finances or owner dashboard access.

## 2. Quantity semantics and example

Label the editable field **Count allocated to AlphaZee (includes reserved units)**. Explain: “Enter all units still held at your shop for AlphaZee, including its reserved orders. Do not include stock you have not made available to AlphaZee.”

Example: on-hand 3, held 0, available 3. One of these units sells in the shop. Vendor enters **2**, reason **Shop sale**. Server records old 3 → new 2, actor/time/reason and returns available 2. Repeated Save must not subtract another unit: this is an absolute count, not an unguarded decrement.

If an AlphaZee order reserves one unit first: on-hand 3, held 1, available 2. A shop sale of another unit gives on-hand 2, held 1, available 1. The vendor must not enter “1 available” into the on-hand field; that would count the hold twice. Show all three numbers together.

If the vendor reports 0 while 1 is held, preserve the committed reservation and record a shortage for owner action. Block new sales against that affected supply until resolved. Show the reported count separately from the last accepted balance. Never pretend the update succeeded, clamp the report silently, or cancel the customer's order automatically.

Dispatch/reservation/return stock movements remain server-owned. Explain that vendors must not decrement the same AlphaZee shipment again after the system records dispatch. Report physical handoff discrepancies to the owner.

## 3. Data model and compatibility

Current public eligibility in `backend/app/queries/catalog_stock.py` relies on active `SupplierVariant`, `Supplier`, cost and `InventoryBalance` records. Existing owner UI configures suppliers at variant level. Therefore, a product dropdown alone cannot implement the requested behavior.

Record a design decision before migration. Recommended compatible approach: distinguish external supply from an explicit internal AlphaZee inventory source, retaining existing mapping/reservation primitives. An internal source must have an explicit type, no vendor membership/login, and be excluded from external vendor lists and payable generation. Do not use a fake ordinary vendor or special display-name string as the security/accounting boundary.

Product-level stock responsibility is the authority for portal visibility; variant mappings must agree with it. Server-side saves atomically validate/synchronize these mappings. Avoid two independent editable fields that can disagree. Existing records with one consistent external source may be backfilled accordingly; mixed, missing or ambiguous mappings go into an owner-review state. Do not silently convert historical stock into owner inventory or move quantities between shops.

Owner-managed stock participates in normal availability, reservations, checkout, cancellation, dispatch, inspection and reporting. It still needs verified unit costs for meaningful economics. It generates no external vendor payable merely because a customer buys it. Already-acquired vendor goods held/owned by AlphaZee retain acquisition history; resale must not create a second vendor debt.

Vendor counts must not overwrite AlphaZee-owned returned units or stock held elsewhere. Integrate with VF3's stock-ownership model. Preserve supplier/cost snapshots and reservation source IDs on existing orders even if the current product's responsible vendor later changes.

## 4. Linking, unlinking and reassignment rules

- Owner-managed → vendor: preview all affected variants, mappings, quantities and obligations; configure the new supply explicitly. Do not copy owner stock into vendor stock.
- Vendor A → vendor B: immediately revoke A's product access when the assignment commits. B sees only its newly configured balance, not A's quantities or history.
- Vendor → owner-managed: revoke vendor access; require a recorded physical receipt/ownership transfer to populate owner stock. An unlink operation is not a stock transfer or supplier payment.
- In the first version, block reassignment while open holds, unresolved shortages or nonzero source stock require resolution. Provide a precise reason and a supported path: fulfill/cancel through existing controls, reconcile stock or record a real transfer. Never zero stock just to bypass the guard.
- Historical mappings, orders, supplier liabilities and audit records remain intact. Outstanding supplier payments still belong to the original supplier. Archive records instead of erasing their history.
- Verify old vendor access against current assignment on every request, including requests from a stale open browser tab. Source changes and stock writes must lock/version compatible records so concurrent reassignment cannot accept an unauthorized write.

## 5. Security and API requirements

Use separate vendor sessions/credentials or a rigorously scoped principal that cannot satisfy owner authorization. Reuse password hashing, revocation, rate limiting, CSRF and Origin protection patterns. Provision credentials through a secure one-time setup or deliberate owner reset flow; no defaults or plaintext persistence. Do not let a self-submitted vendor ID choose membership.

Suggested APIs: vendor login/logout/session; paginated assigned variants; versioned count update; shortage report; own update history. Derive the vendor from the authenticated principal, then verify membership, assignment, SKU status and source ownership. Return generic not-found/denied responses for unauthorized IDs without leaking another shop's data.

Stock updates reuse the existing audited inventory service. Require expected version, nonnegative integer count, bounded reason/note and a retry/idempotency key. On conflict, show the fresh balance and ask the vendor to review; do not silently retry an obsolete count. A stock update racing a customer reservation must never leave negative availability or overwrite a hold.

The vendor response schema must omit customer/order identities, access codes, supplier prices, retail margins and finance fields. Aggregate held quantity is sufficient. Owner audit includes actor, source, old/new values, reason, timestamp, version and request reference. Owner can resolve shortages with recorded evidence; vendor cannot mark them resolved by bypassing a hold.

Stock freshness is visible. Optional owner-configured staleness alerts are useful, but do not invent automatic cancellation rules or claim live POS synchronization. Keep vendor credentials and sample fixtures out of committed files/screenshots.

## 6. Phases and required verification

| Phase | Implement | Exit evidence |
| --- | --- | --- |
| VS0 — reconcile design | Inspect active VF work; map product ownership, variant sources, authentication and VF3 stock ownership. Document migration/backfill decisions. | No duplicate identity/ledger system; explicit handling of legacy mixed mappings and existing owner data. |
| VS1 — source/linking | Product dropdown, internal inventory source support, assignment validation, inherited variant source, reassignment guards. | Owner-managed product can reserve/dispatch normally in lab; linked product reaches correct vendor; snapshots, costs and existing stock preserved. |
| VS2 — vendor access | Owner creates/revokes vendor credentials; separate login/session and restricted read API. | Vendor A cannot read B, AlphaZee-owned stock or any owner endpoint; expiry/reset/revocation work; no private fields in responses. |
| VS3 — stock updates | Mobile stock page, counted quantity, conflict handling, audit history, shortages and owner queue. | 3→2 case works; repeat Save once; below-held report blocks new sales without deleting reservations; no mutation of owned-return stock. |
| VS4 — concurrency/integration | Coordinate assignments, reservations, dispatch and finance integration. | Concurrent checkout/count/reassignment safe; old vendor immediately denied; returns/resale do not duplicate supplier liability. |
| VS5 — browser/persistence | Real owner/vendor workflows, responsive views, restart and regression. | Current-build browser evidence, exact assertions, tests/build/migrations/containers pass, saved counts/accounts/assignments survive restart without deleting volumes. |

Required browser scenario: owner creates vendors A/B → creates one AlphaZee-managed product and one A-linked product with M/L variants → vendor A logs in and sees only its assigned SKUs → changes M from 3 to 2 → owner audit and storefront reflect it → lab customer reserves one → stale/below-held updates are handled → owner resolves the shortage → revoke A and prove its existing session fails.

Also test: product reassignment blocked while held; a permitted reassignment after resolution; B cannot edit A via guessed API IDs; vendor cannot edit prices using extra payload fields; archived products are not editable; offline save preserves input; 360px mobile layout and keyboard operation. Prepare API fixtures if necessary, but perform actual login/dropdown/quantity/save actions for UI acceptance.

Write `.context/vendor_stock_portal_acceptance_report.md` and update the shared VF progress file. Include tested revision/working-tree state, migration head, commands, browser assertion results, redacted screenshots and limitations. Read-only inspection plus a successful login is not full access-control verification. No “complete” claim until both owner-managed and vendor-managed paths work through real inventory operations.

## 7. Owner handoff and boundaries

Provide two short instructions:

- **Owner:** create vendor → provision stock login → choose stock responsibility while creating product → configure variants/cost/source → enter or request counts → publish → monitor shortages/audit.
- **Vendor:** log in → find exact size/color → enter current allocated count → choose reason → save → confirm accepted figures or report a shortage → log out.

Future extensions may include staff permissions, order picking and POS connectors. Build only the stock-only portal now. Continue finance/settings phases from the main VF guide without resetting their progress. Product photographs, retail decisions, customer support, order fulfillment and financial controls remain under the owner's control.
