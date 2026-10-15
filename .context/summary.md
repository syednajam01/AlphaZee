# AlphaZee — short operating guide

Updated 2026-10-15: **M0–M9 complete for the local milestone**. `/admin` manages catalog/media/suppliers/stock and order/payment/return operations. The storefront uses managed media and stable-ID carts; `syed123` persists. **Checkout is open only in the isolated lab at http://127.0.0.1:13001**, as selected. Start with the [owner handoff](m9_owner_handoff.md); see [final evidence](m9_implementation_report.md), [lab guide](m8_checkout_lab_runbook.md), [operations](m7_operations_runbook.md) and [backup](m3_media_runbook.md).

## 1. What the app is

AlphaZee is a Pakistan apparel/essentials store with supplier-based fulfillment and an owner console. The frontend uses Vite, vanilla JavaScript and CSS; FastAPI/Python handles `/api/v1`; PostgreSQL stores commerce data; SQLAlchemy/Alembic manage models and migrations. Prices use integer paisas internally (100 = PKR 1).

The main flows are implemented, but the site is **not open for public orders**. Currently there are no products or collections in development. The owner creates collections/drafts/variants, uploads validated media and publishes through the dashboard. Product fields and media save atomically. Beside each saved variant, load supplier/stock, register or choose a supplier, save exact wholesale PKR cost, then receive stock with a reason/reference/note. `backend/seed.py` is an optional sample tool, not the intended real-catalog workflow.

## 2. Start, access and stop

Start Docker Desktop, then run from `F:\AlphaZee` using the existing local port configuration:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose --env-file .env.docker.local ps
```

If that environment file is missing, copy `.env.docker.local.example` to `.env.docker.local` first. Website: **http://localhost:13000**. API/docs: **http://localhost:18000/docs**. PostgreSQL: loopback **5433**. Without the environment override, Compose defaults to website 3000/API 8000; use one configuration consistently.

For open SAMPLE checkout, run `docker compose -f compose.checkout-lab.yml up --build --wait -d`. Lab website/admin: **http://127.0.0.1:13001** and `/admin`; API 18001, DB 5434. Create your separate persistent lab login with `docker compose -f compose.checkout-lab.yml exec api python scripts/provision_owner.py YOUR_LAB_USERNAME`. The lab has independent DB/media volumes and three distinct session-cookie names. COD and bank verification are simulated; no real money transfer. Use the [M8 guide](m8_checkout_lab_runbook.md) to explicitly export selected catalog/media read-only, dry-run/import as drafts, choose test stock and publish in the lab. No customer/order/session data or source reservations are copied. Same-bundle reruns preserve existing lab edits/stock.

Startup order: **PostgreSQL healthy → migrations to head → API healthy → Vite frontend**. Source changes reload locally. In the page, `main.js` loads `app.js`, builds sections/dialogs, fetches capabilities/catalog and restores saved cart state. Startup/API failures show recovery messages.

Create your owner credentials interactively, then open **http://localhost:13000/admin** (also linked from the footer):

```powershell
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
```

Your requested `syed123` account is already provisioned in the persistent development database. Its password is hashed; it is not saved in source or this guide. Sessions expire after eight hours, so signing in again may be needed. Other accounts have no default login. Add `--reset-password` to reset an owner and revoke sessions. Diagnose with `docker compose --env-file .env.docker.local logs --tail=100 migrate api web`; readiness is `/api/v1/ready`. Stop with `docker compose --env-file .env.docker.local down`; database data stays in its volume. `down -v` removes volumes and must not be used to preserve data.

## 3. Customer journey

- **Browse:** managed hero, collection covers, paginated cards and fresh product details with description/material/care/sizing. Ordered images/videos include alt text, posters, controls and variant associations. Videos wait for selection/play and pause on close/change. Missing images use the neutral placeholder; empty/error/retry states are real. Existing navigation, mobile menu and FAQs remain.
- **Cart:** add exact variants, adjust quantities/remove items and see PKR totals and managed images in cart/checkout. Storage retains items; stable product/variant IDs recover from slug changes and refresh prices/details/images. Inactive, archived, unpublished, sold-out or unverified items cannot proceed. Owner changes, tab return and refresh update the catalog. Dialogs retain keyboard/focus/close handling.
- **Checkout:** customer/address details, COD or configured bank transfer, coupon validation and confirmation are implemented. Server-calculated prices, stock holds and coupon usage commit together. A stored attempt key/payload lets a lost-response retry recover the same order without duplicate stock or coupon use. Cart changes invalidate an applied coupon.
- **Current restriction:** normal development and production reject order creation with 503. Checkout is permitted only with `APP_ENV=test`, `TEST_CHECKOUT_ENABLED=true` and a loopback PostgreSQL database ending `_test`. Production launch needs a deliberate gate change; the test flag is not a production switch.
- **Track/access:** confirmation provides a private code once; save it. Order number plus code establishes an order-scoped HttpOnly session for tracking, payment proof and returns. Phone/order number alone cannot unlock an order. Codes expire after 180 days; sessions after 30 days. Owner-verified recovery issues a new code; revocation invalidates access.
- **Promotions/attribution:** percentage, fixed and free-shipping coupons support eligibility/usage rules. Landing UTM source, medium and campaign accompany orders for marketing reports.

## 4. Owner and fulfillment flow

The direct dashboard has **Overview, Products, Collections, Media, Inventory, Suppliers, Orders and payments, Returns and exchanges, Coupons, Reports**. Products supports search/filter/pagination, draft editing and lifecycle actions; Collections supports covers/activation/order; Media supports multiple uploads, preview/progress/retry/cancel, poster assignment and guarded deletion. The product editor supports exact PKR variant prices, alt text, variant media and keyboard gallery ordering. Failed saves preserve input; stale edits require review/reload. Existing operations reuse the same backend: supplier creation/mapping, audited stock, coupons, orders, returns and reports. Section URLs support refresh/back/forward; logout/expiry returns to login.

**Order placed → supplier confirms allocations → dispatch with courier/tracking/cost → in transit/out for delivery → delivered.** Bank orders also require verified funds before dispatch. Courier booking, tracking updates and money verification are manual owner operations; there is no automatic courier or payment-gateway integration.

For bank transfer, supply valid bank configuration first. After supplier acceptance, preview instructions, send them through the customer channel, then record that handoff. This saves the account snapshot and starts a four-hour deadline. Customer proof is a URL/reference, not automatic bank verification. **Check Expired Bank Transfers** explicitly flags overdue payments; merely opening Orders does not. Review cleared/pending funds, then verify receipt or cancel/release with an audit note. Expiry alone never releases stock.

Stock rules: placing an order holds availability; confirmation preserves it; dispatch deducts physical stock once and releases the hold; delivery deducts nothing further. Eligible pre-dispatch cancellation releases holds. Variant/Inventory disclosures show physical, reserved, available and paginated quantities linked to private orders; unreconciled legacy holds remain reserved. Supplier switches preserve the previous supplier's stock/holds and order cost snapshots. Audited adjustments use expected versions and cannot cut below holds. Public availability also requires active supplier/mapping, cost and positive available stock; private costs and holds stay hidden. Checkout locks remain authoritative.

## 5. Returns, exchanges and money

- **RTO (return to origin):** initiate → record received quantities → inspect. Receipt alone does not restock. Only inspected sellable units return to the original fulfilling supplier's inventory; damaged/unresolved units stay unavailable.
- **Customer return:** private tracking → choose line, quantity, type and reason → owner approves/rejects → receive → inspect → complete. Bank-refund completion creates a liability; **Record Paid Refund** separately records actual partial/full payments and references.
- **Size exchange:** choose another active variant of the same product. Approval reserves separate replacement stock; receive and fully inspect the original before replacement dispatch. Replacement delivery/RTO follows its own allocations and does not rewrite the original sale/payment. Any explicit replacement charge is separate.
- **COD settlement:** after delivery, record courier bank receipts and evidenced deductions. Outstanding = collected COD − receipts − deductions. Partial remains outstanding; a declared final shortfall is disputed; zero balance is remitted. Duplicate/excess entries are rejected and financial evidence is append-only.
- **Analytics:** separates delivered sales, bank payments, courier-held COD, receipts, deductions, refund liabilities/payments, product costs, courier costs and estimated contribution. It includes marketing attribution. These are current-state operational figures, not a dated tax/general-ledger export.

## 6. Persistence, security and deployment

PostgreSQL persists owners/sessions, catalog/suppliers, stock/events, orders/holds, shipments, returns, coupons and financial evidence. The cart uses local storage; pending checkout/UTM use tab storage. Owner passwords and access/session tokens are hashed; cookies are HttpOnly, with Secure in production. Owner mutations require session, trusted Origin and CSRF protection; login/customer-code attempts are rate limited. Logout revokes the owner session.

Production uses `compose.prod.yml`: private DB/API, automatic migrations, static frontend served by Caddy HTTPS. Fill private `.env.production` from its example with real domain/database credentials, configure DNS/ports, back up the DB, then deploy using `docker compose --env-file .env.production -f compose.prod.yml up --build -d`. Production requires rebuilt images for edits. Full setup/backup guidance: [deployment runbook](docker_deployment_runbook.md).

## 7. Completed work and remaining limits

Completed: earlier commerce repairs (0/L1/A/B/C/D/E/G/F/L2/V), Docker packaging and M0–M9: dashboard, catalog lifecycle, durable media, authoring, supplier/stock, storefront/cart, operations/reports, independent checkout lab/copying and final local acceptance/handoff. Migration head: `f27b6d91c083` (M5–M9 need no migration). Media persists in each project’s `catalog_media` volume; back up database and files together.

M9 verification: **260 backend tests, 108 frontend tests, development/production/lab builds and 228 Chrome checks passed** (145 commerce/mobile/archive + 83 authoring/storefront). No unexpected browser/network failures; expected security denials and offline recovery were checked. Migration cycle/comparison and archived history/media/stock persistence passed. Development remains free of sample catalog/orders, the owner enabled and its checkout closed. Evidence is in the phase register and M9 reports.

M9 fixed completed replacement-RTO inspection staying actionable, clarified one-time receipt and made phone report cards readable. Vite 7.3.7/esbuild 0.28.2 report zero npm advisories; native frontend work needs Node 20.19+ or 22.12+ (Docker uses Node 22). One existing backend AnyIO deprecation warning remains. The owner handoff covers first-product setup, selected copy, payments and backups.

Remaining owner setup: real catalog, supplier/business arrangements and valid bank/support/legal/recovery configuration. Public launch/deployment needs a separate request; it has not occurred. There is no automatic next phase. Normal and lab stacks are available; temporary acceptance infrastructure is stopped.
