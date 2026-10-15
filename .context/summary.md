# AlphaZee — short operating guide

Updated 2026-10-14 through M2. Catalog lifecycle APIs now support drafts, versioned edits and archival; upload/editor screens remain M3/M4 work. The stale Docker Vite `/admin` module was fixed with polling/restart. Normal catalog is empty and public checkout stays disabled; isolated browser and database verification are recorded in [M2 guide](m2_catalog_runbook.md).

## 1. What the app is

AlphaZee is a Pakistan apparel/essentials store with supplier-based fulfillment and an owner console. The frontend uses Vite, vanilla JavaScript and CSS; FastAPI/Python handles `/api/v1`; PostgreSQL stores commerce data; SQLAlchemy/Alembic manage models and migrations. Prices use integer paisas internally (100 = PKR 1).

The main flows are implemented, but the site is **not open for public orders**. Currently there are no products or collections in development. Owner APIs can save incomplete drafts, variants and collections; the full editing screen and managed uploads are still pending. New publication requires validated media from M3. `backend/seed.py` is an optional sample tool, not the intended real-catalog workflow.

## 2. Start, access and stop

Start Docker Desktop, then run from `F:\AlphaZee` using the existing local port configuration:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose --env-file .env.docker.local ps
```

If that environment file is missing, copy `.env.docker.local.example` to `.env.docker.local` first. Website: **http://localhost:13000**. API/docs: **http://localhost:18000/docs**. PostgreSQL: loopback **5433**. Without the environment override, Compose defaults to website 3000/API 8000; use one configuration consistently.

Startup order: **PostgreSQL healthy → migrations to head → API healthy → Vite frontend**. Source changes reload locally. In the page, `main.js` loads `app.js`, builds sections/dialogs, fetches capabilities/catalog and restores saved cart state. Startup/API failures show recovery messages.

Create your owner credentials interactively, then open **http://localhost:13000/admin** (also linked from the footer):

```powershell
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
```

There is no default login. Add `--reset-password` to reset that owner and revoke sessions. Diagnose with `docker compose --env-file .env.docker.local logs --tail=100 migrate api web`; readiness is `/api/v1/ready`. Stop with `docker compose --env-file .env.docker.local down`; database data stays in its volume. `down -v` removes volumes and must not be used to preserve data.

## 3. Customer journey

- **Browse:** hero carousel, collections/filter tabs, paginated products, detail dialog, size/color selection, navigation, mobile menu and FAQs. Catalog comes from the API; loading, empty, unavailable and retry states are handled.
- **Cart:** add variants, adjust quantities, remove items and see PKR totals. Local storage retains the cart; opening it rechecks live price/availability. Offline or unavailable items cannot proceed. Dialogs support close/backdrop/Escape and focus handling.
- **Checkout:** customer/address details, COD or configured bank transfer, coupon validation and confirmation are implemented. Server-calculated prices, stock holds and coupon usage commit together. A stored attempt key/payload lets a lost-response retry recover the same order without duplicate stock or coupon use. Cart changes invalidate an applied coupon.
- **Current restriction:** normal development and production reject order creation with 503. Checkout is permitted only with `APP_ENV=test`, `TEST_CHECKOUT_ENABLED=true` and a loopback PostgreSQL database ending `_test`. Production launch needs a deliberate gate change; the test flag is not a production switch.
- **Track/access:** confirmation provides a private code once; save it. Order number plus code establishes an order-scoped HttpOnly session for tracking, payment proof and returns. Phone/order number alone cannot unlock an order. Codes expire after 180 days; sessions after 30 days. Owner-verified recovery issues a new code; revocation invalidates access.
- **Promotions/attribution:** percentage, fixed and free-shipping coupons support eligibility/usage rules. Landing UTM source, medium and campaign accompany orders for marketing reports.

## 4. Owner and fulfillment flow

The direct dashboard has **Overview, Products, Collections, Media, Inventory, Suppliers, Orders and payments, Returns and exchanges, Coupons, Reports**. Products/Collections/Media are explicit placeholders until M2–M4. Existing operations reuse the same backend: supplier creation/mapping, audited stock, coupons, orders, returns and reports. Section URLs support refresh/back/forward; logout/expiry returns to login.

**Order placed → supplier confirms allocations → dispatch with courier/tracking/cost → in transit/out for delivery → delivered.** Bank orders also require verified funds before dispatch. Courier booking, tracking updates and money verification are manual owner operations; there is no automatic courier or payment-gateway integration.

For bank transfer, supply valid bank configuration first. After supplier acceptance, preview instructions, send them through the customer channel, then record that handoff. This saves the account snapshot and starts a four-hour deadline. Customer proof is a URL/reference, not automatic bank verification. **Check Expired Bank Transfers** explicitly flags overdue payments; merely opening Orders does not. Review cleared/pending funds, then verify receipt or cancel/release with an audit note. Expiry alone never releases stock.

Stock rules: placing an order holds availability; confirmation preserves the hold; dispatch deducts physical stock once and releases the hold; delivery deducts nothing further. Eligible pre-dispatch cancellation releases holds. Concurrent buyers, retries and adjustments cannot oversell reserved stock. Historical shipments needing reconciliation require explicit owner decisions.

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

Completed: earlier commerce repairs (0/L1/A/B/C/D/E/G/F/L2/V), Docker packaging, M0 backup/contracts, M1 direct dashboard and M2 catalog lifecycle/APIs. Development migration head: `e15a9c2b7046`.

M2 verification: **218 backend tests, final 17 focused catalog tests, 88 frontend tests, builds, real edit-version contention and isolated migration/backup checks passed**. Browser checks include the actual `/admin` login and isolated draft/publication guard. See [M2 guide](m2_catalog_runbook.md) and [earlier verification](repair_verification_report.md).

Still needed: media uploads and authoring screens (M3/M4), supplier/stock detail integration, real catalog/business setup, valid bank/support/legal/recovery configuration, isolated checkout lab and complete commerce browser acceptance. No public production deployment has been completed; public checkout stays closed.
