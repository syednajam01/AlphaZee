# B1 Follow-up: Browser Acceptance & Operations Report

**Date:** 2026-10-19  
**Tested Source Revision:** `f0fec71f461203159685fcd0dd401318bcb0b0d1` (with working tree canonical home route fix in `frontend/src/app.js`)  
**Target Environment:** Isolated Checkout Lab (`http://127.0.0.1:13001`, API `http://127.0.0.1:18001`, PostgreSQL 5434 `alphazee_checkout_test`)  
**Container Rebuild Commands:**  
```powershell
cd frontend; npm.cmd run build
docker compose -f compose.checkout-lab.yml up --build -d web
```
**Verification Test Runner:**  
`& "C:\Program Files\Python313\python.exe" scratch/verify_b1_followup.py`  
**JSON Acceptance Evidence:** [b1_followup_results.json](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_followup_results.json)  
**Security Invariant:** All captured screenshots have customer access codes strictly redacted to `SAMPLE-REDACTED-ACCESS-CODE`. Lab warnings remain prominently visible.

---

## Executive Summary

Following Codex's terminal review, availability logic corrections, and removal of unapproved commercial promises, this focused browser acceptance run verified all 5 mandated operational and storefront workflows against live Chromium running with real layout and network timing.

| Section | Domain | Result | Key Proof / Metrics |
|---|---|---|---|
| **1** | Variant Selection Acceptance | **PASS** | Sold-out first size does not block selection; size prompt triggers on unselected add; missing pair disables add button & clears variant query; deep links accurately restore or block. |
| **2** | Navigation & Media Lifecycle | **PASS** | Query parameters (`utm_source`, `ref`) preserved; rapid A→B→Home navigation restores home title, canonical, and hero; 404 cleanly displays unavailable view; 0 orphaned playing media on exit. |
| **3** | Commercial Copy & Policy Absence | **PASS (Guarded)** | Removed unapproved free shipping & 7-day exchange promises; simulated shipping labeled `PKR 0 (test checkout)`; real policies recorded as **BLOCKED ON OWNER**. |
| **4** | Layout, Accessibility & 200% Zoom | **PASS** | Multi-breakpoint matrix (360/390/768/1280/1440px) shows zero horizontal overflow and valid button geometry; Cart Drawer traps focus & restores on Escape; lab notice adds 40px top offset without occlusion; True Desktop 200% Zoom (DPR=2.0) verified. |
| **5** | Authenticated Operations & Lifecycles | **PASS** | Authenticated lab owner (`sample_m8_*`); live API edit of `material`, `care`, and `sizing` immediately rendered on storefront; full COD lifecycle completed to `delivered,remitted`; full Bank Transfer lifecycle completed to `dispatched,verified`. |

---

## Detailed Section Findings & Verification Evidence

### 1. Variant Selection Acceptance

**Test Fixture:** Product `disposable-b1-variants` (`prod-disposable-b1`):
- Variant A (`id=58`, Black S, unavailable, stock 0, PKR 4,500)
- Variant B (`id=59`, Black M, available, stock 15, PKR 4,800)
- Missing Pair: Black L (does not exist in catalog)
- Variant C (`id=60`, Olive L, available, stock 10, PKR 5,200)

**Results & Assertions:**
1. **Fresh URL (`/products/disposable-b1-variants`):**
   - Size label: `"Select a size"`
   - `hasPreselectedSize: false`, `hasVariantParam: false`
   - Display starting price: `"PKR 4,800"` (derived dynamically from the first available variant under selected color Black, ignoring the sold-out S).
2. **Unselected Add-to-Bag Attempt:**
   - Clicking `#btn-add-to-cart` triggers alert `#size-selection-prompt` with text: `"Please select a size before adding to bag."`
   - Cart drawer remains closed (`drawerStayedClosed: true`).
   - Screenshot: [b1_sec1_size_prompt.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec1_size_prompt.png)
3. **Selecting Available Variant M:**
   - Size label updates to `"M"`, prompt hidden, button enabled.
   - URL updates to include `?variant=59`.
   - Clicking Add to Bag opens Cart Drawer with 1 item, price `"PKR 4,800"`, subtotal `"PKR 4,800"`.
   - Screenshot: [b1_sec1_cart_added_available.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec1_cart_added_available.png)
4. **Selecting Missing Pair (Black + L):**
   - Clicking chip L while Black is active: Add button becomes disabled (`btnDisabledOrUnavailable: true`).
   - URL `variant` parameter is cleanly stripped (`variantParamCleared: true`).
   - Attempting to click disabled button adds nothing to cart (`post_click_cart_count == initial_cart_count`).
   - Screenshot: [b1_sec1_missing_pair_blocked.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec1_missing_pair_blocked.png)
5. **Deep Link Restoration:**
   - Deep link `?variant=59` (Black M): Color Black, Size M restored; Add button enabled (`addBtnEnabled: true`).
   - Deep link `?variant=58` (Black S, sold out): Color Black, Size S restored; Add button disabled with text `"Out of Stock"` (`addBtnDisabled: true`).

---

### 2. Navigation & Media Lifecycle

**Results & Assertions:**
1. **Query Parameter Retention:**
   - Navigating to `/products/disposable-b1-variants?utm_source=spring_drop&ref=b1_test`.
   - Selecting Size M updates URL to include `variant=59` while preserving `utm_source=spring_drop` and `ref=b1_test`.
2. **Rapid Switching & Route Metadata Recovery:**
   - Rapid sequence: Product A → Product 404 → Home (`/`) executed before delayed responses complete.
   - Verified that metadata and DOM cleanly reflect Home:
     - Document Title: `"AlphaZee — Modern Apparel & Curated Essentials"` (`isHomeTitle: true`)
     - Canonical Link: `http://127.0.0.1:13001/` (`isHomeCanonical: true`)
     - Description: `"Minimalist streetwear crafted in Pakistan. Premium cotton, structured fits, and zero compromises."`
     - `.product-page-container` is detached (`productPageDetached: true`).
     - Hero carousel section is present (`heroPresent: true`).
3. **Missing Product (404) State:**
   - Navigating to `/products/completely-nonexistent-piece-404`:
     - Document Title: `"Piece Unavailable — AlphaZee"`
     - Canonical Link: completely removed (`canonicalCleared: true`) to prevent indexing broken routes.
     - Renders `.product-unavailable-title` with user guidance to return to catalog.
     - Screenshot: [b1_sec2_unavailable_piece.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec2_unavailable_piece.png)
4. **Media Playback on Route Exit:**
   - Active videos checked on route transitions: 0 playing videos (`videoCount: 0`, `anyPlaying: false`).

---

### 3. Commercial Copy & Policy Absence Inspection

**Results & Assertions:**
1. **Home Page & Footer:**
   - Old promises verified absent: `hasOldFreeDeliveryPromise: false`, `hasOldSevenDayExchangePromise: false`, `hasOldTransitPromise: false`, `hasOldDispatchPromise: false`.
   - Replaced with honest notice: `"Delivery coverage, charges and timing will be published before public ordering opens."`
   - Misleading legal links removed. Footer only exposes legitimate operational link: `"Owner Console"` (`/admin`).
2. **Product Page Accordions:**
   - Old 24–48h dispatch and 7-day inspection promises absent (`false`).
   - Replaced with: `"Delivery timing, coverage, and return/exchange terms will be published before public ordering opens."`
3. **Cart Drawer:**
   - Removed `"Free nationwide delivery across Pakistan"`.
   - Clearly displays lab indicator: `"SAMPLE / TEST checkout — simulated orders only."`
4. **Checkout View:**
   - Shipping fee row clearly labeled: `Estimated Delivery: PKR 0 (test checkout)`.
   - Under Place Order: `"Direct Owner Verified Fulfillment. Return and exchange terms will be published before public ordering opens."`
   - Screenshot: [b1_sec3_checkout_copy.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec3_checkout_copy.png)
5. **Items Marked BLOCKED ON OWNER:**
   - Official delivery coverage, transit timing, and shipping fee structure.
   - Official return/exchange policy, time limit, and fee terms.
   - Official privacy policy and terms of service text.
   - Dedicated live customer support contact/channel.

---

### 4. Layout, Accessibility & Desktop 200% Zoom

**Multi-Breakpoint Geometric Matrix:**

| Viewport | Window Dimensions | Scroll Width | Horizontal Overflow | Primary Button Geometry | Title Visible |
|---|---|---|---|---|---|
| **360px Compact** | 360 × 640 | 360px | **No** (360 == 360) | Width: 328px, Height: 50px, Top: 730px | **Yes** |
| **390px Mobile** | 390 × 844 | 390px | **No** (390 == 390) | Width: 358px, Height: 50px, Top: 730px | **Yes** |
| **768px Tablet** | 768 × 1024 | 753px | **No** (753 < 768) | Width: 705px, Height: 50px, Top: 730px | **Yes** |
| **1280px Laptop** | 1280 × 800 | 1265px | **No** (1265 < 1280) | Width: 478px, Height: 50px, Top: 559px | **Yes** |
| **1440px Desktop** | 1440 × 900 | 1425px | **No** (1425 < 1440) | Width: 484px, Height: 50px, Top: 564px | **Yes** |

Screenshots:  
- 360px: [b1_sec4_viewport_360px_compact.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_viewport_360px_compact.png)  
- 390px: [b1_sec4_viewport_390px_mobile.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_viewport_390px_mobile.png)  
- 768px: [b1_sec4_viewport_768px_tablet.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_viewport_768px_tablet.png)  
- 1280px: [b1_sec4_viewport_1280px_laptop.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_viewport_1280px_laptop.png)  
- 1440px: [b1_sec4_viewport_1440px_desktop.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_viewport_1440px_desktop.png)

**Keyboard Accessibility & Lab Notice Offsets:**
- **Keyboard Trap:** When Cart Drawer opens, initial focus is trapped inside (`#cart-close-btn`).
- **Escape Key Handling:** Pressing Escape closes Cart Drawer and restores focus to `#cart-btn` in header (`focusRestoredToCart: true`).
- **Lab Notice Offset:** Lab notice measured at 40px height (`--lab-notice-height: 40px`). Cart drawer top offset is 40px; header top offset is 40px. No occlusion occurs between notice and UI elements (`noOcclusion: true`).

**True Desktop 200% Zoom:**
- Viewport set to 640 × 400 with `deviceScaleFactor: 2.0, mobile: False` (faithful W3C desktop 200% zoom emulation).
- `innerWidth: 640`, `scrollWidth: 625` (zero horizontal overflow).
- Product title visible and purchase button fully visible and clickable without horizontal panning.
- Screenshot: [b1_sec4_desktop_200pct_zoom.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec4_desktop_200pct_zoom.png)

---

### 5. Authenticated Operations & Full Order Lifecycles

**5.1 Owner Provisioning & Admin Authentication:**
- Provisioned dedicated lab owner: `sample_m8_4bf09f71`.
- Authenticated via `POST /api/v1/auth/login`. Session cookie `alphazee_lab_owner_session` stored in browser.
- Admin dashboard loaded at `/admin`: `#btn-admin-logout` verified visible (`authenticated: true`).
- Screenshot: [b1_sec5_admin_authenticated.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec5_admin_authenticated.png)

**5.2 Admin Product Editorial Edit & Live Storefront Update:**
- Sent `POST /api/v1/admin/products/prod-disposable-b1` with CSRF token and `expected_version=1`:
  - `material: "100% Ring-Spun Combed Cotton (Batch 04)"`
  - `care: "Machine wash cold, inside out. Do not tumble dry."`
  - `sizing: "Relaxed streetwear boxy cut. Drop shoulder silhouette."`
- Response: `200 OK` (`id: 'prod-disposable-b1'`).
- Navigated back to storefront product page `/products/disposable-b1-variants`:
  - Verified live rendering: `materialRendered: true`, `careRendered: true`, `sizingRendered: true`.
  - Proves end-to-end admin editing and immediate customer-facing reflection without invented defaults.
  - Screenshot: [b1_sec5_storefront_edited_fields.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec5_storefront_edited_fields.png)

**5.3 Cash on Delivery (COD) Complete Order Lifecycle:**
- Customer placed COD order from checkout for 2 × Variant M (PKR 9,600).
- Redacted confirmation screenshot captured: [b1_sec5_cod_order_confirmed.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec5_cod_order_confirmed.png)
- Order `0b454105-83b4-429e-8a5b-e041a8623f2a` placed with held reservation (`order_status: 'placed'`).
- **Operational Supplier Confirmation:** `confirm_supplier_acceptance` transitioned order to `'confirmed'` and reservation to `'confirmed'`.
- **Courier Dispatch:** `create_shipment` created shipment with tracking `COD-TRK-749e7cfc` and transitioned order to `'dispatched'`.
- **Courier Delivery:** `update_shipment_status` marked shipment delivered (`order_status: 'delivered'`, `cod_remittance_status: 'pending_remittance'`).
- **Cash Remittance:** `record_settlement` remitted PKR 9,600 (`cod_remittance_status: 'remitted'`).
- Final status check: **`delivered,remitted`** (PASS).

**5.4 Bank Transfer Complete Order Lifecycle:**
- Customer placed Bank Transfer order from checkout (PKR 4,800).
- Redacted confirmation screenshot captured: [b1_sec5_bank_order_confirmed.png](file:///F:/AlphaZee/.local/frontend-redesign/run_b1_followup/b1_sec5_bank_order_confirmed.png)
- Order `8150ae80-c3b7-4d3b-b3a8-89a671c36866` placed (`order_status: 'placed'`, `payment_status: 'pending'`).
- **Operational Supplier Confirmation:** `confirm_supplier_acceptance` transitioned order to `'confirmed'`.
- **Handoff Instructions:** `record_payment_instructions_sent` recorded WhatsApp dispatch with reference `BANK-REF-971a629f`, establishing 4-hour payment deadline.
- **Proof of Payment:** `upload_payment_receipt` recorded payment screenshot proof `PROOF-REF-cb795c64`.
- **Proof-Only Verification Invariant:** Verified that uploading receipt leaves `order.payment_status == 'pending'` (payment receipt does not clear funds).
- **Owner Verified Cleared Funds:** `verify_bank_payment` verified payment funds (`payment_status: 'verified'`).
- **Courier Dispatch:** `create_shipment` dispatched order with tracking `BANK-TRK-e3b97a37` (`order_status: 'dispatched'`).
- Final status check: **`dispatched,verified`** (PASS).

---

## Remaining Commercial Decisions (Blocked on Owner)

Before public launch or staging deployment, the owner must provide real commercial terms:

1. **Assortment & Media:** Real photos, videos, descriptions, and verified fabric composition for catalog items.
2. **Delivery & Logistics:** Real courier partner selection, shipping fee rate (flat, tiered, or subsidized), and realistic transit estimates (Karachi / Lahore / Nationwide).
3. **Returns & Exchanges:** Specific return window (e.g. 7 days or inspection only), exchange courier fee responsibility, and refund settlement channels.
4. **Customer Support:** Official WhatsApp support number or support email address to replace the current pending support placeholder.
