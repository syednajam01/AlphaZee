# M7: owner operations and financial reports

Implemented 2026-10-15. Open http://localhost:13000/admin and sign in with the existing persistent owner account. M7 uses the existing order, inventory, payment, return and accounting services; no migration or business-data reset is needed.

## Daily operations

- **Orders and payments:** search order numbers or customer phones, filter status and page through results. Private stock-hold links open the selected order. Expand evidence for address, customer notes, immutable line snapshots, supplier acceptance, proof references and shipments. Historical snapshots remain independent of subsequent catalog edits.
- **COD:** confirm supplier availability, dispatch with courier/tracking and exact PKR cost, advance shipment status, then record delivery. Open COD settlement to review the balance and prior entries; record actual receipts and evidenced deductions. A final shortfall remains disputed. Original and charged replacement shipments use the same append-only settlement service.
- **Bank transfer:** configure valid bank details, confirm the supplier, preview instructions, actually send them and explicitly record the handoff/reference. Previewing changes nothing. Handoff starts the four-hour deadline. A proof link/reference is evidence only: review the bank independently and check the cleared-funds confirmation before verifying payment. Dispatch requires verified funds.
- **Overdue bank orders:** opening a page does not expire or cancel anything. Use **Check Expired Bank Transfers**, inspect cleared/pending funds, and explicitly resolve with a note. Releasing an unpaid order cancels it and releases its reservation through the existing service.
- **Cancellation/RTO:** eligible pre-dispatch cancellation releases reservations. For a dispatched RTO, record reason and courier fee, then actual receipt and sellable/damaged inspection quantities. Receipt alone never restocks; only inspected sellable units become available.
- **Customer returns:** filter by status; inspect the linked order and return history. Approve or reject/withdraw approval before receipt. Record one actual positive receipt quantity, then inspect it. The current service does not support incremental follow-up receipts. Complete the inspected return; a bank refund creates a liability. **Record Paid Refund** separately records actual partial/full payments with reference. Completed history shows those payments.
- **Size exchanges:** approval reserves the selected replacement and optional exact charge. Receive and inspect the original, dispatch the replacement, then advance in transit/out for delivery/delivered. Charged delivered replacements expose COD settlement. The original sale is preserved. Legacy returns requiring reconciliation remain blocked by existing backend safeguards.
- **Private order access:** independently verify the customer, enter an audit note and issue a replacement code. It appears once in the current form; copy through the verified customer channel and clear it. Revocation invalidates existing access. Codes are excluded from verification reports.
- **Coupons:** create percentage, fixed PKR or free-shipping coupons with minimum subtotal/usage limits; delete when appropriate. Monetary inputs accept up to two decimal places without rounding; percentage and usage limits require whole values.

## Reading the figures

Overview and Reports reuse the existing financial summary. Delivered sales represent delivered merchandise, not bank deposits. Cash received is business cash after recorded refunds; courier-held COD remains separate. Refund outstanding is completed refund liability less recorded payments. Estimated contribution includes recorded product/courier costs and refunds under existing service definitions; it is not a tax statement or a dated general ledger. Marketing reports show order value, not cash. Courier deductions and explicit courier expenses retain existing deduplication rules. Empty data displays truthful zero/empty states.

## Verification and isolation

Passed: **251 backend tests** (one existing AnyIO deprecation warning), **107 frontend tests**, **65 isolated Chrome checks**, frontend production build, development/production image builds and Alembic schema comparison. The normal development stack is healthy and the isolated test stack is stopped with volumes preserved. Actual evidence is recorded in `owner_catalog_phase_status.json`, `m7_browser_verification.json` and `m7_development_verification.json`. Regression coverage includes literal order search, stable pagination, bank cash versus delivered sales, read-only GETs, JSON mutation headers, empty 204 responses, exact PKR inputs, proof escaping, explicit funds confirmation and stale recovery responses. Desktop report evidence was visually inspected; mobile order-page overflow was checked at 390px.

For a repeat acceptance run, use the isolated M3 media project with its M7-only synthetic bank override:

```powershell
docker compose -f compose.media-check.yml -f compose.operations-check.yml up --build --wait -d
backend\.venv\Scripts\python.exe backend/scripts/verify_m7_browser.py
docker compose -f compose.media-check.yml -f compose.operations-check.yml stop
```

This terminal-driven headless Chrome check creates SAMPLE fixtures only in `alphazee_m3_media_test`, uses independent volumes, keeps public checkout disabled and never uses the development owner password. It requires installed Chrome, frontend dependencies and the backend virtual environment. The helper rejects other databases; do not use its synthetic bank configuration for real payments. Repeated runs retain isolated SAMPLE data. Screenshots are under the report's `.local/m7-browser/...` artifact path.

M7 verifies owner processing of service-created orders. Customer checkout, selected-catalog copying and simultaneous normal/lab sessions belong to M8; full milestone handoff belongs to M9. Normal development data and the existing owner remain intact. Production images are built for validation, without deploying production or opening checkout.
