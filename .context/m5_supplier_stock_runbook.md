# M5 — supplier setup and readable stock holds

Completed 2026-10-15. Open **http://localhost:13000/admin/products** with your existing owner login. Save a variant, then choose **Load supplier and stock** beside it.

## Owner workflow

1. Choose an active supplier, or expand **Register a supplier here** and enter its name/unique slug. Enter wholesale cost as exact PKR (for example `12.34`, stored as 1234 paisas), then **Save supplier and cost**. Registration selects the new supplier but requires an explicit mapping save.
2. Enter a positive/negative whole-unit **Quantity change**, reason, optional invoice/reference and note, then **Save stock adjustment**. This calls the existing version-checked inventory service and creates an immutable event attributed to the owner. It rejects stale versions, negative/overflow balances and adjustments below reserved quantities. Product detail saves do not change stock.
3. Read **Physical / Reserved / Available** and each reservation's quantity, stage and order link. **Previous/Next holds** paginates 20 rows at a time; totals cover every holding reservation. Inventory also has a **See reserved orders** disclosure. Order links restore the owner session and filter Orders to the linked order.
4. **Previous supplier** disclosures retain that supplier's physical stock and reservations. Switching suppliers neither transfers old stock nor rewrites costs on purchased order lines. A new mapping begins at zero physical stock. Re-selecting a retained supplier reuses its balance and reservations.
5. Failed actions retain input; **Reload saved stock** explicitly discards local stock drafts after confirmation. Other unsaved stock groups survive successful actions. Save/reload a changed mapping before adjusting stock. Save/reload stock drafts before a product detail save. Navigation warnings include both product and stock drafts.

## Stock and public availability

All totals and purchase enforcement use one predicate: reservation stage `held`/`confirmed`, **or** `legacy_stock_hold=true`. Dispatched legacy holds remain reserved until reconciled; orphan references are displayed honestly without inventing an order link. Available = max(0, physical − reserved). Protected hold reads share the balance lock used exclusively by stock writers, keeping aggregate and page data consistent.

Public variant availability requires the owner's Available switch, active variant, retail price, active supplier mapping, active supplier, non-null nonnegative wholesale cost and positive available stock. Existing Unknown/Unavailable owner choices remain effective. Publication/active collection still gate public product access and checkout. Public JSON exposes no supplier identity, cost, stock balance, hold/order detail or customer data. Checkout rechecks supplier and stock under its existing locks; displayed availability is a snapshot. Supplier reassignment takes the variant lock shared by checkout and serializes competing assignments.

Order placement reserves; confirmation retains the hold; eligible cancellation releases it. Dispatch deducts physical stock once and releases its allocation; delivery does not deduct again. Returns only restock inspected accepted units under existing services. Public checkout remains disabled; synthetic acceptance orders bypass only that HTTP gate by calling the real service inside the isolated test database.

## API and verification

- Owner-only `GET /api/v1/admin/catalog/variants/{id}/stock`: current mapping/readiness and historical supplier details.
- Owner-only `GET /api/v1/admin/inventory/{supplier_variant_id}/holds?page=1&page_size=20`: consistent totals and paginated holds (maximum 100/page).
- Existing supplier assignment and inventory adjustment endpoints retain session/Origin/CSRF protections; adjustments accept optional `notes` and legacy version zero. `GET /api/v1/admin/orders?order_id={uuid}` supplies the private order deep link.
- **246 backend tests**, **96 frontend tests**, frontend build, development Docker build/start and production API/web image builds passed. A focused stock UI rerun passed after preserving disabled pagination controls on error. Alembic check reports no new upgrade operations; head remains `f27b6d91c083`.
- **55 isolated Chrome checks** passed, including M4 regressions and M5 registration/cost/receipt, multiple orders + legacy hold, order deep links, rejected adjustment recovery, supplier-switch history, public privacy/availability and mobile overflow. See `m5_browser_verification.json`; screenshots are under its `.local` artifact path. No unexpected console/runtime errors.
- `m5_development_verification.json` confirms the normal development catalog/media/orders/mappings remain empty, the provisioned owner is enabled, protected reads reject anonymous users and checkout stays closed. No credentials were reset or recorded. Persistence proof remains `m3_owner_persistence_verification.json`.

Reproduce: start the isolated `compose.media-check.yml` stack, then run `backend\.venv\Scripts\python.exe backend/scripts/verify_m4_browser.py --phase-m5`. It uses fresh random SAMPLE owner credentials and a guarded `prepare_m5_holds.py` fixture restricted to the test database. Stop that stack with `docker compose -f compose.media-check.yml stop`; preserve volumes. M6 remains pending.
