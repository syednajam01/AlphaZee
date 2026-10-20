# VF0–VF6 independent review for Antigravity

Reviewed 2026-10-20 while VF7 was in progress. Scope: both implementation guides, progress report, and current source/tests. This is a static code review, not a fresh test run or browser certification. Concurrent edits may supersede findings; check current source before fixing. Preserve existing work/data.

**Verdict:** substantial progress, but do not accept VF1–VF6 as fully integrated yet. The new screens, modules, migrations, vendor sessions, product-source selector and test coverage are useful. Several business-critical requirements currently exist as isolated helpers or fields rather than complete journeys.

## Fix before final acceptance

1. **Automatic supplier charges are disconnected from fulfillment.**
   - `backend/app/services/supplier_finance.py::post_event_liability_if_applicable` has no application callers found under `backend/app`; tests call it directly.
   - Wire real pickup/dispatch/delivery events to atomic liability posting. A selectable pickup trigger needs an actual pickup confirmation action.
   - The helper currently reads the latest supplier agreement and can fall back to the current variant supplier. Snapshot supplier/agreement/terms for the transaction. Its key includes trigger type: changing dispatch to delivery must not charge the same acquisition twice.
   - It commits internally and rolls back the whole session on uniqueness errors. Ensure fulfillment and ledger posting have a single transaction boundary with safe duplicate handling.
   - Verify through actual owner fulfillment actions, including retries, agreement changes and partial/replacement supply. Blanket skipping all replacement lines is not proof that no vendor acquisition occurred.

2. **Returned-stock ownership is not connected to stock movements.**
   - Searches found the `OrderLine.ownership_source` field and payable skip, but no ownership assignment in order creation/return services or quantity-level ownership accounting in inventory.
   - An artificially constructed owned order line proves only the skip condition. Implement the real return/RTO inspection → retained owned inventory → reservation → resale flow, preserving cost and acquired quantities.
   - Test mixed owned/vendor units of the same SKU, partial returns, damage and replacements. Vendor corrections must never overwrite owned units.

3. **A shortage alert does not stop additional sales.**
   - `services/vendor_portal.py::update_vendor_counted_quantity` records a shortage but retains the old on-hand count and returns its positive available quantity.
   - No shortage checks were found in availability/reservation paths. Example: stored 10, held 3, reported 1 still exposes 7 available.
   - Preserve holds, record the reported count, block new reservations against unresolved deficient supply and provide a validated owner-resolution flow. Cover duplicate reports and stale retries.
   - Correct the progress report's claim that the reported count is saved as physical stock: the reviewed branch leaves the balance unchanged.

4. **Supplier reassignment guards are incomplete.**
   - `services/owner_catalog.py` checks active holds, but not nonzero old-source stock or unresolved shortages. Existing target mappings can be reactivated with historical balances.
   - Enforce the portal guide's explicit source-change/transfer rules, consistent product and variant assignments, and lock against simultaneous vendor edits. Do not silently reactivate stale stock.
   - Vendor reads/writes rely on active supplier mappings rather than requiring agreement with the product's current vendor responsibility. Verify old vendor requests fail immediately after reassignment and legacy variant controls cannot bypass the product assignment.
   - Newly created mappings default supplier cost to zero. Require explicit cost confirmation rather than making an unknown acquisition cost look free.

5. **Period reporting can misstate money.**
   - `services/financial_report.py::get_period_financial_report` filters delivered sales by `Order.placed_at`, so an order placed yesterday and delivered today is reported in the wrong sales period.
   - Return COGS reversals also inherit the original-order period filter, which can omit this month's return of an older sale.
   - Freight deduplication uses `max(shipment_total, expense_total)`. This is not linkage-based deduplication: independent freight of 200 plus 100 must total 300, while two records of the same 200 expense must total 200.
   - Use actual event dates, start-inclusive/end-exclusive boundaries, linked expense identities, and tests spanning different placement/delivery/return/payment periods. Reconcile exports and drilldowns to the same definitions.

6. **Shipping/settings persistence does not establish functional integration.**
   - `standard_shipping_fee_minor` was found in settings/model/schema code, not the checkout calculation path; `orders.py` uses its order-command shipping value.
   - Implement authoritative shipping quotes, coverage/rule validation and purchase-time snapshots; prove tampered browser totals cannot override them.
   - Settings currently introduce a PKR 200 default while the progress text says PKR 250. Neither is an owner-approved commercial decision. Keep unspecified rules clearly unconfigured or explicitly lab-only.
   - `fetchAdminPreferences` was only found consumed by the settings editor. Prove saved theme/density/report presets affect the actual workspace, independently for two owners.
   - Reconcile all requested customization controls against what actually works; list missing dashboard arrangement, navigation/table controls and other unsupported options as deferred rather than complete.

## VF7 evidence required

- Run the real journey: owner creates vendor/login → links product or chooses AlphaZee stock → vendor edits SKU count → customer checks out → owner confirms/picks up/dispatches/delivers → records supplier payment and courier cash → returns/inspects → resells → reconciles reports.
- Use UI actions for UI acceptance. Direct ORM fixture construction and direct service calls are useful tests but cannot prove the integration above.
- Include two vendors, two owners, cross-role denials, revoked sessions, stale writes, concurrent allocations/reservations, shortage blocking, source reassignment and restart persistence.
- Keep the main app checkout closed. Preserve media flows and test normal/lab/production packaging.
- Correct report inconsistencies, including opening-balance preview target 50,000 versus claimed resulting balance 32,000. Screenshots and PASS counts must support the exact asserted behavior.
- Update the shared progress file and both required acceptance reports with implemented/tested/browser-verified/blocked distinctions. Do not restart phases or duplicate systems; repair these gaps within the ongoing milestone.

No application code, databases or running containers were changed during this review.
