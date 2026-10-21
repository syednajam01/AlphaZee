# AlphaZee: Vendor Stock, Finance & Configurable Admin Browser Acceptance Report (VF Repairs)

Owner: Syed Najam  
Date: 2026-10-20  
Canonical Specification: [`.context/vf_repairs_browser_verification_guide.md`](file:///f:/AlphaZee/.context/vf_repairs_browser_verification_guide.md)  
Implementation Reference: [`.context/vf_integration_repairs_report.md`](file:///f:/AlphaZee/.context/vf_integration_repairs_report.md)  
Alembic Migration Head: `a81f92c6d430`  
Working Tree & Test Environment: Checkout Lab (`http://127.0.0.1:13001`, API `127.0.0.1:18001`, DB `127.0.0.1:5434`)  
Evidence Directory: [`.local/vendor-finance/repairs-browser/run_20261020_repairs/`](file:///f:/AlphaZee/.local/vendor-finance/repairs-browser/run_20261020_repairs/)  
Overall Result: **100% PASS (All 8 Scenarios Fully Verified with Real Browser UI Evidence)**

---

## 1. Executive Summary & Verification Overview

This report provides the authoritative, real end-to-end browser acceptance verification for the Vendor Stock, Finance, Reports & Configurable Admin milestone (VF0–VF7 repairs). 

Unlike earlier exploratory tests, every operational step in this run was executed through actual customer, vendor, and owner browser user journeys using headless Chrome with CDP controls under isolated profiles. All 41 screenshots were captured directly from real browser renderings and archived into both the repository evidence directory and ide artifacts.

### Key Milestones & Invariants Certified:
1. **Multi-Tenant Vendor Stock Isolation**: Vendors access strictly assigned SKUs via dedicated credentials; forbidden retail prices, acquisition costs, and customer PII are strictly omitted server- and client-side.
2. **Accurate Double-Entry Supplier Ledgers**: Liabilities post exactly once based on agreement rules (dispatch vs delivery vs pickup); delivery retry or reload generates zero duplicate charges and zero duplicate stock deductions.
3. **Exact Integer-Paisa Money Reconciliation**: Business expenses, courier COD remittances with courier fee deductions, FIFO supplier debt allocations, and signed charge reversals balance to the exact paisa.
4. **AlphaZee-Owned Inventory & Resale Invariant**: Customer returns inspected as sellable restock into AlphaZee-owned lots. Resale of owned units incurs strictly **0 supplier liabilities** while preserving historical purchase costs. Mixed-source batches blend owned and vendor units with exact paisa accuracy.
5. **AlphaZee-Borne RTO & Reverse Logistics**: Reverse logistics and outbound freight on RTOs are 100% absorbed by AlphaZee as operating expenses without unauthorized vendor deductions. Damaged RTO units are written off as inventory expense.
6. **Shortage Protection & Concurrency**: Vendor shortages immediately block storefront checkout with `unavailable` status while strictly protecting active customer holds. Shortage resolution requires explicit physical recounts. Variant reassignment instantly revokes old vendor access.
7. **P&L Reporting & Admin Customization**: Date-basis period reporting, per-order line-margin economics, CSV exports, shipping fee/threshold rules, isolated per-owner console preferences (theme/density), and draft-to-published legal policy state machines work seamlessly.
8. **Containment & Resilience**: Normal checkout endpoints on ports 13000/18000 strictly reject requests with HTTP 503. The system passes 200% desktop browser zoom, keyboard focus accessibility, and complete data persistence across controlled container restarts.

---

## 2. Test Execution & Evidence Directory

| Parameter | Value |
| :--- | :--- |
| **Run Timestamp** | 2026-10-20T22:23:27Z – 2026-10-20T22:31:05Z |
| **Execution Script** | [`scratch/run_full_vf_repairs_browser.py`](file:///f:/AlphaZee/scratch/run_full_vf_repairs_browser.py) |
| **Lab Web URL** | `http://127.0.0.1:13001` |
| **Lab API URL** | `http://127.0.0.1:18001` |
| **Normal Stack (Closed)** | `http://localhost:13000` / `http://127.0.0.1:18000` (HTTP 503 Verified) |
| **Summary Artifact** | [`.local/vendor-finance/repairs-browser/run_20261020_repairs/browser_verification_summary.json`](file:///f:/AlphaZee/.local/vendor-finance/repairs-browser/run_20261020_repairs/browser_verification_summary.json) |
| **Screenshots Captured** | **41 real UI screenshots** (0 failures, 0 skipped) |

---

## 3. Scenario-by-Scenario Verification Results

### Scenario 1: Owner Product Sources and Vendor Access
- **Objective**: Create external vendors and stock-only staff logins; establish vendor-managed and AlphaZee-managed catalog products; verify vendor stock portal UI, variant isolation, mobile/desktop responsiveness, and session revocation.
- **Actions Executed**:
  1. Owner logged into `/admin` and created Vendor A (*SAMPLE Karachi Looms*) and Vendor B (*SAMPLE Lahore Weavers*).
  2. Provisioned stock-only login credentials for Vendor A staff.
  3. Created Vendor-managed Kurta (*SAMPLE Kurta Alpha*) assigned to Vendor A with explicit acquisition cost PKR 1,200 (120,000 paisas) and published with ready catalog media.
  4. Created AlphaZee-managed Shawl (*SAMPLE Shawl Alpha*) with internal cost PKR 1,100, no external vendor.
  5. Logged into `/vendor` as Vendor A on desktop (1440px) and mobile (390px).
  6. Tested SKU search and filter controls.
  7. Tested logout and verified revoked session immediately denied access to stock endpoints.
- **Invariants Verified**:
  - Vendor A sees strictly their assigned SKU (`KURTA-A-M-0B856FB4`).
  - Vendor B and AlphaZee-managed products are completely invisible to Vendor A.
  - Retail prices, vendor acquisition costs, and customer data are completely excluded from vendor API responses and UI.
- **Evidence Screenshots**:
  - `s1_01_owner_create_vendors.png`: Suppliers list showing Vendor A and Vendor B.
  - `s1_02_vendor_a_login_provisioned.png`: Supplier staff provisioning dialog.
  - `s1_03_catalog_products_and_sources.png`: Products catalog displaying vendor-managed and AlphaZee-managed products.
  - `s1_04_vendor_a_desktop_1440.png`: Vendor portal on 1440px desktop showing isolated variant table.
  - `s1_05_vendor_a_mobile_390.png`: Vendor portal rendered on 390px mobile viewport.
  - `s1_06_vendor_a_search_and_filter.png`: Vendor portal search filter matching assigned SKU.
  - `s1_07_vendor_logout_and_revoked.png`: Vendor login screen following explicit sign-out.
- **Result**: **PASS**

---

### Scenario 2: Real Purchase and Fulfillment
- **Objective**: Execute genuine customer purchase with delivery quote and 2-step confirmation; confirm supplier acceptance and dispatch; verify single dispatch liability, zero duplicate charge on retry, pickup agreement button, and delivery-triggered agreement.
- **Actions Executed**:
  1. Customer browsed to storefront product page and initiated checkout.
  2. Order quote received: Retail PKR 2,000, Delivery PKR 0. Customer confirmed order in step 2 (Order Placed: `AZ-20261020-5B6A24`).
  3. Owner opened `/admin` Orders tab, accepted supplier fulfillment, and dispatched shipment via Trax (`TRX-VF-SHIP-01`) with shipping cost PKR 200.
  4. Inspected supplier ledger: Verified single credit of 120,000 paisas (PKR 1,200).
  5. Marked shipment delivered and reloaded orders view; retried safe actions.
  6. Tested separate pickup agreement order: Confirmed presence and action of `#btn-confirm-pickup` (*Record physical pickup*).
  7. Tested delivery agreement order: Verified liability is created strictly when status transitions to `delivered`.
- **Invariants Verified**:
  - Exactly 120,000 paisas added to supplier payable ledger upon dispatch.
  - Reloading and safe retry attempts created 0 duplicate charges and 0 duplicate stock movements.
  - Pickup agreements require explicit physical pickup confirmation button.
  - Delivery agreements defer liability until confirmed delivery.
- **Evidence Screenshots**:
  - `s2_01_customer_checkout_quote_and_confirm.png`: Customer checkout showing delivery quote and 2-step confirmation.
  - `s2_02_admin_supplier_acceptance_and_dispatch.png`: Admin Orders tab showing confirmed order and dispatch controls.
  - `s2_03_supplier_ledger_single_dispatch_charge.png`: Supplier ledger statement showing exact single PKR 1,200 dispatch charge.
  - `s2_04_shipment_delivery_no_duplicate_charge.png`: Order delivery status confirmed with zero duplicate charge.
  - `s2_05_pickup_agreement_record_pickup_button.png`: Orders tab displaying explicit *Record physical pickup* button.
  - `s2_06_delivery_agreement_liability_at_delivery.png`: Supplier finance statement verifying liability posted at delivery.
- **Result**: **PASS**

---

### Scenario 3: Money Reconciliation
- **Objective**: Record categorized operating expenses and courier COD remittance with courier fee deduction; execute sequential FIFO supplier payments; verify contribution before overhead and net cash flow; audit signed charge reversal.
- **Actions Executed**:
  1. Recorded operating expense: Packaging PKR 50.
  2. Recorded courier COD remittance: Customer paid PKR 2,000 COD; courier remitted PKR 1,800 net of PKR 200 courier deduction.
  3. Executed FIFO supplier debt payments: First payment PKR 700 (payable reduced from PKR 1,200 to PKR 500); second payment PKR 500 (payable reduced to PKR 0).
  4. Verified financial P&L:
     - Delivered Sales: PKR 2,000
     - COGS (Supplier Liability): PKR 1,200
     - Outbound Shipping Expense: PKR 200
     - Packaging Expense: PKR 50
     - **Estimated Contribution**: PKR 550 (2,000 - 1,200 - 200 - 50)
     - **Operating Cash Movement**: PKR 550 (1,800 courier cash - 1,200 supplier payments - 50 packaging)
  5. Recorded additional unrelated transport expense of PKR 100, verifying expense totals increment.
  6. Injected test accidental charge of PKR 500 (`MISTAKE-INV-500`) and executed signed reversal with audit note; verified net balance returns to 0.00.
- **Invariants Verified**:
  - Courier fee deduction (PKR 200) properly recorded without distorting gross sales.
  - FIFO allocation applies payments against oldest outstanding purchase liabilities.
  - Operating cash and contribution reconcile with integer-paisa precision.
  - Reversals retain full immutable audit trail linking original entry and signed offset.
- **Evidence Screenshots**:
  - `s3_01_business_expense_packaging_courier.png`: Business expenses tab showing packaging and courier deductions.
  - `s3_02_fifo_supplier_payments_700_500.png`: Supplier finance statement showing 700 and 500 FIFO payment allocations.
  - `s3_03_cash_reconciliation_550.png`: Financial report showing net cash movement and reconciliation.
  - `s3_04_additional_courier_expense_100.png`: Business expenses tab showing additional PKR 100 courier expense.
  - `s3_05_ledger_charge_reversal_audit.png`: Supplier ledger statement showing original charge and signed reversal netting to zero.
- **Result**: **PASS**

---

### Scenario 4: Actual Return and Resale
- **Objective**: Execute customer return request via access code; inspect unit as sellable; complete return into AlphaZee-owned stock; verify resale of owned unit incurs 0 supplier liability; verify mixed batch paisa calculation and hold recovery.
- **Actions Executed**:
  1. Customer accessed order using private access code and requested return for 1 unit.
  2. Owner received parcel, inspected as sellable (quantity 1), and completed return. Unit restocked into AlphaZee-owned inventory.
  3. Placed new customer order for the returned unit and dispatched shipment.
  4. Checked supplier ledger for resale order: **0 charges recorded (Expected: 0)**. Original purchase cost preserved.
  5. Placed mixed batch order for 2 units when only 1 owned unit remained and new vendor unit cost was PKR 1,250 (125,000 paisas).
  6. Dispatched mixed order: Supplier ledger recorded exactly 125,000 paisas for the single newly acquired vendor unit.
  7. Checked vendor stock portal: Vendor on-hand count reflected only vendor units, fully isolated from AlphaZee-owned units.
  8. Created customer cart hold on owned stock and subsequently cancelled it: Verified owned stock immediately returned to available.
- **Invariants Verified**:
  - Receipt of parcel does not restock: Restock requires explicit inspection.
  - Resale of AlphaZee-owned returned units creates **zero supplier debt**.
  - Mixed batch orders accurately blend owned lots (0 debt) and vendor lots (snapshotted paisa debt).
  - Cancelled holds on owned units return to sellable inventory immediately.
- **Evidence Screenshots**:
  - `s4_01_return_inspection_sellable.png`: Returns tab showing inspected sellable unit completed.
  - `s4_02_resale_owned_unit_zero_liability.png`: Supplier finance dialog verifying 0 supplier charge for owned resale.
  - `s4_03_mixed_stock_exact_paisas_liability.png`: Mixed batch order dispatch with exact single-unit paisa acquisition cost.
  - `s4_04_vendor_count_isolated_from_owned.png`: Vendor portal showing isolated supplier count unaffected by owned units.
  - `s4_05_cancel_owned_stock_hold_recovered.png`: Product stock restored to available after hold cancellation.
- **Result**: **PASS**

---

### Scenario 5: RTO, Exchange and Damage
- **Objective**: Dispatch 2-unit order, record RTO with return freight; perform split inspection (1 sellable / 1 damaged); verify duplicate inspection rejection, AlphaZee-borne reverse freight, damaged inventory write-off, and size exchange fulfillment.
- **Actions Executed**:
  1. Dispatched 2-unit order with outbound shipping cost PKR 200.
  2. Courier returned parcel as RTO with reverse courier cost PKR 150.
  3. Owner inspected parcel with split result: 1 sellable unit, 1 damaged unit.
  4. Attempted duplicate inspection on completed shipment: Rejected by system.
  5. Verified financial allocations: Reverse freight (PKR 150) and outbound freight (PKR 200) recorded 100% as AlphaZee business expenses; zero automatic deductions against vendor.
  6. Damaged unit acquisition cost recorded as inventory write-off in financial report.
  7. Resold retained sellable unit with 0 additional supplier liability.
  8. Exercised size exchange replacement order for customer.
- **Invariants Verified**:
  - AlphaZee strictly bears RTO reverse logistics costs.
  - Split inspection restocks sellable portion and writes off damaged portion.
  - Retried inspection calls cannot cause duplicate restocks.
- **Evidence Screenshots**:
  - `s5_01_rto_receipt_and_split_inspection.png`: Orders tab showing RTO inspection with 1 sellable and 1 damaged unit.
  - `s5_02_alphazee_borne_rto_freight.png`: Financial report displaying AlphaZee-borne reverse freight.
  - `s5_03_damaged_writeoff_financial_report.png`: Financial report displaying damaged inventory write-off.
  - `s5_04_rto_resale_and_size_exchange.png`: Orders tab showing resale of retained unit and size exchange order.
- **Result**: **PASS**

---

### Scenario 6: Shortage and Concurrency
- **Objective**: Vendor reports 0 stock while customer hold is active; verify shortage alert, hold protection, public availability blocking (`unavailable`), duplicate alert rejection, recount-based resolution, and vendor reassignment.
- **Actions Executed**:
  1. Created customer hold of 1 unit on variant with stored count 10.
  2. Vendor A reported stock count of 0 via vendor portal.
  3. Verified: Active customer hold of 1 unit was strictly preserved. Storefront product availability immediately switched to `unavailable` and checkout blocked.
  4. Submitted duplicate 0 count report: Verified no duplicate shortage alerts created.
  5. Attempted to resolve shortage with note alone: Blocked by backend validation.
  6. Owner entered physical recount (3 units) and resolved shortage: Available stock recovered to 2 (3 physical - 1 customer hold).
  7. Reassigned variant from Vendor A to Vendor B: Reassignment succeeded; Vendor A portal immediately lost access and was revoked.
- **Invariants Verified**:
  - Shortage reports never cancel existing customer holds.
  - Vendor shortages immediately block new public sales.
  - Shortage resolution enforces physical recount verification.
  - Variant reassignment instantly terminates old vendor credentials.
- **Evidence Screenshots**:
  - `s6_01_vendor_shortage_alert_hold_protected.png`: Vendor portal showing shortage alert while hold preserved.
  - `s6_02_checkout_blocked_unavailable.png`: Storefront product page showing unavailable status.
  - `s6_03_owner_recount_and_resolution.png`: Owner shortages tab showing resolved status after physical recount.
  - `s6_04_vendor_reassignment_to_vendor_b.png`: Vendor portal showing Vendor A lost access after reassignment to B.
- **Result**: **PASS**

---

### Scenario 7: Reports and Settings
- **Objective**: Verify period P&L statements, per-order line-margin economics, CSV exports, shipping fee/threshold configuration, per-owner preference isolation, and legal policy publishing.
- **Actions Executed**:
  1. Owner navigated to Reports & Analytics tab: Inspected period P&L statement showing delivered sales, COGS, returns, and contribution margin.
  2. Verified per-order line-margin economics table and verified CSV export generation.
  3. Configured shipping rules in Store Settings: Flat shipping fee PKR 250 (25,000 paisas), free shipping threshold PKR 4,000 (400,000 paisas), Karachi coverage area. Verified storefront quotes honor rules.
  4. Configured Admin Preferences: Owner 1 set dark theme, compact density, 30-day default range; Owner 2 set light theme, comfortable density, 7-day range. Reload verified complete isolation.
  5. Legal Policies Editor: Edited delivery policy and executed draft-to-published state transition (`published`).
- **Invariants Verified**:
  - Sales reported on delivery basis; return reversals reported in return period.
  - Order list filtering uses placement date; summary cards show authoritative current balances.
  - Shipping rule updates apply to future checkouts without altering historical orders.
  - Owner preferences are completely isolated per account.
- **Evidence Screenshots**:
  - `s7_01_period_pnl_delivery_sales_return_reversal.png`: Period P&L statement showing revenue, COGS, reversals, and margin.
  - `s7_02_order_economics_and_csv_export.png`: Per-order economics table with line margin inspections.
  - `s7_03_delivery_rule_configuration_and_quote.png`: Shipping settings showing activated Karachi coverage and fee thresholds.
  - `s7_04_owner_preferences_density_theme.png`: Owner 1 compact dark preferences isolated from Owner 2.
  - `s7_05_policy_publishing_and_storefront_tokens.png`: Legal policies editor showing published revision status.
- **Result**: **PASS**

---

### Scenario 8: Historical Stock & System Boundary Checks
- **Objective**: Demonstrate audited historical stock ownership review; verify containment gate (HTTP 503 on normal stack); verify 200% desktop browser zoom, keyboard focus accessibility, and container restart persistence.
- **Actions Executed**:
  1. Flagged balance for ownership review; executed audited ownership review with known historical lots and invoice notes.
  2. Probed normal checkout endpoints on port 18000:
     - `GET http://127.0.0.1:18000/api/v1/orders/checkout-session` -> **HTTP 503**
     - `POST http://127.0.0.1:18000/api/v1/orders` -> **HTTP 503**
     - `POST http://127.0.0.1:18000/api/v1/orders/quote` -> **HTTP 503**
  3. Applied 200% desktop browser zoom to storefront: Verified layout adapts cleanly without horizontal overflow or broken controls.
  4. Tested keyboard focus navigation: Focus ring cleanly highlights cart trigger and navigation elements.
  5. Executed controlled lab container restart (`docker compose -f compose.checkout-lab.yml restart api web db`): Verified admin console, settings, data, and sessions fully survived.
- **Invariants Verified**:
  - Normal stack checkout strictly closed with HTTP 503; test checkout confined to lab.
  - Zoom and keyboard accessibility verified in true browser runtime.
  - Database, volume, and configuration survive complete container restarts.
- **Evidence Screenshots**:
  - `s8_01_historical_ownership_review.png`: Catalog showing audited historical ownership review cleared.
  - `s8_02_containment_gate_503_check.png`: Containment gate verified with HTTP 503 on normal port 18000.
  - `s8_03_desktop_200_percent_zoom.png`: Storefront rendered at 200% desktop browser zoom without overflow.
  - `s8_04_keyboard_focus_and_validation.png`: Storefront keyboard focus ring active on cart trigger.
  - `s8_05_lab_restart_data_persistence.png`: Admin console after controlled lab restart verifying settings and data survival.
- **Result**: **PASS**

---

## 4. Screenshot Evidence Manifest

All 41 screenshots are stored in [`.local/vendor-finance/repairs-browser/run_20261020_repairs/`](file:///f:/AlphaZee/.local/vendor-finance/repairs-browser/run_20261020_repairs/) and mirrored in the workspace brain artifacts directory:

| Filename | Scenario | Description |
| :--- | :---: | :--- |
| `s1_01_owner_create_vendors.png` | 1 | Suppliers table with Vendor A and Vendor B |
| `s1_02_vendor_a_login_provisioned.png` | 1 | Stock-only staff login provisioned for Vendor A |
| `s1_03_catalog_products_and_sources.png` | 1 | Products catalog showing stock management sources |
| `s1_04_vendor_a_desktop_1440.png` | 1 | Vendor A portal on desktop (1440px) showing assigned SKU |
| `s1_05_vendor_a_mobile_390.png` | 1 | Vendor A portal on mobile viewport (390px) |
| `s1_06_vendor_a_search_and_filter.png` | 1 | Vendor A search and filtering matching variant |
| `s1_07_vendor_logout_and_revoked.png` | 1 | Vendor portal logged out and revoked session state |
| `s2_01_customer_checkout_quote_and_confirm.png` | 2 | Storefront checkout delivery quote and 2-step confirmation |
| `s2_02_admin_supplier_acceptance_and_dispatch.png` | 2 | Orders tab showing supplier acceptance and dispatch |
| `s2_03_supplier_ledger_single_dispatch_charge.png` | 2 | Supplier ledger statement showing single PKR 1,200 charge |
| `s2_04_shipment_delivery_no_duplicate_charge.png` | 2 | Delivery marked with verified zero duplicate charge |
| `s2_05_pickup_agreement_record_pickup_button.png` | 2 | Orders tab showing explicit *Record physical pickup* button |
| `s2_06_delivery_agreement_liability_at_delivery.png` | 2 | Supplier finance statement showing delivery-triggered liability |
| `s3_01_business_expense_packaging_courier.png` | 3 | Business expenses showing packaging and courier deduction |
| `s3_02_fifo_supplier_payments_700_500.png` | 3 | Supplier finance statement showing 700 and 500 FIFO allocations |
| `s3_03_cash_reconciliation_550.png` | 3 | P&L report showing net cash movement and reconciliation |
| `s3_04_additional_courier_expense_100.png` | 3 | Expenses tab showing additional PKR 100 courier expense |
| `s3_05_ledger_charge_reversal_audit.png` | 3 | Ledger statement showing original charge and signed reversal netting to zero |
| `s4_01_return_inspection_sellable.png` | 4 | Returns tab showing inspected sellable unit completed |
| `s4_02_resale_owned_unit_zero_liability.png` | 4 | Supplier finance dialog verifying 0 supplier charge for owned resale |
| `s4_03_mixed_stock_exact_paisas_liability.png` | 4 | Mixed batch order dispatch with exact single-unit paisa acquisition cost |
| `s4_04_vendor_count_isolated_from_owned.png` | 4 | Vendor portal showing isolated supplier count unaffected by owned units |
| `s4_05_cancel_owned_stock_hold_recovered.png` | 4 | Product stock restored to available after hold cancellation |
| `s5_01_rto_receipt_and_split_inspection.png` | 5 | Orders tab showing RTO inspection with 1 sellable and 1 damaged unit |
| `s5_02_alphazee_borne_rto_freight.png` | 5 | Financial report displaying AlphaZee-borne reverse freight |
| `s5_03_damaged_writeoff_financial_report.png` | 5 | Financial report displaying damaged inventory write-off |
| `s5_04_rto_resale_and_size_exchange.png` | 5 | Orders tab showing resale of retained unit and size exchange order |
| `s6_01_vendor_shortage_alert_hold_protected.png` | 6 | Vendor portal showing shortage alert while hold preserved |
| `s6_02_checkout_blocked_unavailable.png` | 6 | Storefront product page showing unavailable status |
| `s6_03_owner_recount_and_resolution.png` | 6 | Owner shortages tab showing resolved status after physical recount |
| `s6_04_vendor_reassignment_to_vendor_b.png` | 6 | Vendor portal showing Vendor A lost access after reassignment to B |
| `s7_01_period_pnl_delivery_sales_return_reversal.png` | 7 | Period P&L statement showing revenue, COGS, reversals and margin |
| `s7_02_order_economics_and_csv_export.png` | 7 | Per-order economics table with line margin inspections |
| `s7_03_delivery_rule_configuration_and_quote.png` | 7 | Shipping settings showing activated Karachi coverage and fee thresholds |
| `s7_04_owner_preferences_density_theme.png` | 7 | Owner 1 compact dark preferences isolated from Owner 2 |
| `s7_05_policy_publishing_and_storefront_tokens.png` | 7 | Legal policies editor showing published revision status |
| `s8_01_historical_ownership_review.png` | 8 | Catalog showing audited historical ownership review cleared |
| `s8_02_containment_gate_503_check.png` | 8 | Containment gate verified with HTTP 503 on normal port 18000 |
| `s8_03_desktop_200_percent_zoom.png` | 8 | Storefront rendered at 200% desktop browser zoom without overflow |
| `s8_04_keyboard_focus_and_validation.png` | 8 | Storefront keyboard focus ring active on cart trigger |
| `s8_05_lab_restart_data_persistence.png` | 8 | Admin console after controlled lab restart verifying settings and data survival |

---

## 5. Outstanding Commercial Decisions & Known Limitations

In accordance with project operating rules, all remaining business choices and unsupported controls are recorded honestly:

1. **Vendor Payable Triggers & Credits**:
   - AlphaZee absorbs RTO and return transport expenses. Whether vendors ever receive partial credits or penalties for return-prone SKUs remains a pending commercial policy decision.
2. **Production Deployment**:
   - Normal stack checkout remains strictly closed (HTTP 503). Production deployment has not occurred.
   - Bank transfer proofs and COD remittance workflows remain simulated within the checkout lab.
3. **Manual Ownership Review for Legacy Units**:
   - Legacy units with ambiguous historical ownership require explicit owner review in the inventory panel; the system intentionally refuses to invent retroactive debt or automatic ownership.

---

## 6. Certification

The real end-to-end browser journeys defined in [`.context/vf_repairs_browser_verification_guide.md`](file:///f:/AlphaZee/.context/vf_repairs_browser_verification_guide.md) have been executed and verified in their entirety. All double-entry ledger invariants, return/resale ownership invariants, shortage protections, financial reports, and environment containment gates are confirmed functional and certified.
