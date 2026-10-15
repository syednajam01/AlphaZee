# M8: local checkout lab and selected catalog copy

The isolated lab opens checkout at **http://127.0.0.1:13001**. Admin: **http://127.0.0.1:13001/admin**. Use this exact host. Its API is on loopback port 18001 and PostgreSQL on 5434. Your normal catalog/admin stays at http://localhost:13000 with checkout closed, as selected for this phase. No production orders or deployment are enabled.

## Start and sign in

From `F:\AlphaZee`, with Docker Desktop running:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose -f compose.checkout-lab.yml up --build --wait -d
docker compose -f compose.checkout-lab.yml ps
docker compose -f compose.checkout-lab.yml exec api python scripts/provision_owner.py YOUR_LAB_USERNAME
```

Choose your own lab username and password in the interactive terminal; there is no default login. This creates a separate persistent owner, not a copy of development credentials. To reset it and revoke its sessions, append `--reset-password`. The existing `syed123` development account is unchanged. Browser acceptance creates random SAMPLE owners with ephemeral credentials solely for automation; those are not your login.

The lab uses project `alphazee-checkout-lab`, database `alphazee_checkout_test`, and its own `pgdata` and `catalog_media` volumes. API/migrations share the DB network namespace so the DB connection genuinely uses `127.0.0.1:5432`; the existing loopback checkout guard remains intact. Published ports bind only to loopback. Owner, checkout and private order cookies have distinct `alphazee_lab_*` names. Storage is origin-specific; use localhost for normal development and 127.0.0.1 for the lab consistently.

All lab pages carry a SAMPLE banner. COD, bank handoff and bank verification are simulations. Bank account/IBAN values deliberately identify no real account. **Never transfer money.** Simulated bank support is permitted only with the isolated test checkout gate and `CHECKOUT_LAB=true`; real configurations still require the existing bank validation.

## Copy selected real products

First create products/media in your normal owner dashboard. Find stable product IDs in the authenticated `/api/v1/admin/products` response (open that URL on the normal website while logged in), or inspect a product card's `data-edit-product` attribute. Use explicit product selection; no catalog is copied automatically.

Export from the normal API, which mounts the durable source media and the backend workspace:

```powershell
docker compose --env-file .env.docker.local exec -T api python scripts/catalog_lab.py export --product PRODUCT_ID --output /app/.local/catalog-transfer/my-catalog.zip --include-supplier-costs
```

Repeat `--product PRODUCT_ID` for additional selections. The output filename must be new; export never overwrites a prior file. Export uses a PostgreSQL **REPEATABLE READ, READ ONLY** transaction. It copies selected product/variant descriptions, retail prices, relevant collections, managed media/posters/associations and optionally active wholesale costs. It excludes owners/passwords/sessions, customers/orders, reservations, financial records, supplier identities/contacts/notes and unrelated media. Legacy external media URLs are omitted; attach actual managed uploads before export when needed.

`--include-supplier-costs` is an explicit choice. With it, the destination creates a new SAMPLE supplier and mappings using those costs. Without it, set mappings/costs yourself in the lab dashboard; stock is only applied to mapped variants. No source stock quantities or reservations are copied.

Validate a dry run first, then import with an explicit quantity per mapped variant:

```powershell
docker compose -f compose.checkout-lab.yml exec -T api python scripts/catalog_lab.py import /transfer/my-catalog.zip --owner YOUR_LAB_USERNAME --stock 10
docker compose -f compose.checkout-lab.yml exec -T api python scripts/catalog_lab.py import /transfer/my-catalog.zip --owner YOUR_LAB_USERNAME --stock 10 --apply
```

The lab mounts `backend/.local/catalog-transfer` read-only as `/transfer`. The bundle is catalog data: protect it if it contains private wholesale costs. It is excluded from Git and Docker build context.

The importer checks the lab destination, source/destination identity, manifest fields, archive paths, references, byte limits and checksums, then re-decodes media with the existing validators. IDs and file keys are remapped; SKU/slug collisions fail rather than overwriting destination data. Import uses one DB transaction and cleans its own staged/new files on failure. Starting quantities use the existing audited stock adjustment service with a SAMPLE reference. Imported products are **drafts**: open Products, inspect media/variants/mappings/stock and publish deliberately.

An identical bundle rerun skips existing imports and preserves their edits, stock and orders; changing `--stock` on a rerun does not reset inventory. A later edited source export is a new snapshot and may encounter slug/SKU collisions. There is no automatic sync or overwrite. Review/edit the existing lab copy or use a fresh independent lab project for a different snapshot. The current importer rejects partial prior imports for review.

## Walk through checkout

1. Publish a reviewed lab product with an active variant, positive stock and supplier mapping. Browse its card/gallery, choose the variant, add to cart, enter SAMPLE customer/address details and place a COD order. Save its private code; tracking requires that code or the order-scoped session.
2. Open the order in the lab owner dashboard. Confirm the hold, accept the supplier, dispatch with manual tracking/cost, mark delivered and record a simulated courier receipt. Delivery and cash settlement remain separate.
3. Place a bank-transfer order. Owner accepts supplier availability, previews simulated instructions, then explicitly records the simulated customer handoff. This starts the existing four-hour window. The customer submits a synthetic proof URL/reference through private tracking. Proof alone never verifies funds. Owner explicitly confirms simulated cleared funds before dispatch.
4. Cancel an eligible unpaid pre-dispatch order and check the hold release. Overdue bank orders require **Check Expired Bank Transfers**, funds review and an explicit resolution; opening pages never releases stock. The acceptance-only `lab_runtime.py --expire` helper changes only SAMPLE lab orders after handoff, never the production timer.
5. Track a delivered order and request a return/exchange. Owner approves, receives, inspects and completes using the existing services. A refund liability and actual paid refund are separate entries. An exchange reserves and ships a separate replacement. Reports distinguish sales, cash, courier-held COD, refund liabilities and estimated contribution.

The lab is empty on a fresh installation. Acceptance leaves clearly named SAMPLE products/orders only in its isolated volumes; it never inserts them into your real catalog. Add/copy your own products explicitly.

## Persistence, stop and evidence

```powershell
docker compose -f compose.checkout-lab.yml restart api web
docker compose -f compose.checkout-lab.yml stop
docker compose -f compose.checkout-lab.yml up --wait -d
```

Normal shutdown/rebuild preserves lab database rows, owner credentials and media. Do not use `down -v` when preserving them. Back up lab DB/media together using the same matched-backup principles as the [media guide](m3_media_runbook.md). Never restore lab data into development.

For repeat terminal-driven Chrome acceptance, start the separate media acceptance source and lab, then run:

```powershell
docker compose -f compose.media-check.yml up --build --wait -d
docker compose -f compose.checkout-lab.yml up --build --wait -d
backend\.venv\Scripts\python.exe backend/scripts/verify_m8_browser.py
docker compose -f compose.media-check.yml stop
```

This uses only SAMPLE fixtures in two test databases, random in-memory credentials and a fresh Chrome profile. It requires installed Chrome, the backend virtual environment and Docker. Passed: **260 backend tests** (one existing AnyIO deprecation warning), **107 frontend tests**, **98 lab Chrome checks**, frontend production build, normal/production/lab image builds and Alembic schema comparison. Runtime snapshots confirmed the product/media/poster bytes, orders and exact stock/holds survive API/web restart. Desktop Reports evidence was visually inspected; mobile storefront overflow was checked. The real development catalog/orders remain empty and its owner enabled. Both normal and lab stacks remain running; the temporary media-export source is stopped.

Actual M8 results are recorded in `m8_browser_verification.json`, `m8_runtime_verification.json`, `m8_development_verification.json` and the phase register. To repeat M8 persistence after its successful browser run: `backend\.venv\Scripts\python.exe backend/scripts/verify_m8_runtime.py`. M9 has now completed final regression/handoff; see [the owner guide](m9_owner_handoff.md) and [final evidence](m9_implementation_report.md).
