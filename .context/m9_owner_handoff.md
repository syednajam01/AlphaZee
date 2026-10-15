# AlphaZee owner handoff

This guide covers the implemented local application. The phase register and linked verification files record actual results. Production deployment and accepting real public orders require a separate launch decision. The owner selected open checkout only in the isolated lab.

## Start and sign in

From `F:\AlphaZee`, start Docker Desktop, then:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose -f compose.checkout-lab.yml up --build --wait -d
```

| Environment | Storefront / admin | API / database | Checkout |
| --- | --- | --- | --- |
| Normal development | http://localhost:13000 / http://localhost:13000/admin | API 18000; PostgreSQL 5433 | Closed |
| Isolated SAMPLE lab | http://127.0.0.1:13001 / http://127.0.0.1:13001/admin | API 18001; PostgreSQL 5434 | Open for simulated COD/bank workflows |

Your existing `syed123` development account persists in PostgreSQL. Sign in using your saved password; it is not stored in this guide. Sessions expire after eight hours. Create additional owners or explicitly reset a password through an interactive terminal:

```powershell
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME --reset-password
docker compose -f compose.checkout-lab.yml exec api python scripts/provision_owner.py YOUR_LAB_USERNAME
```

Run only the command you intend; resets revoke that owner's sessions. The lab needs its own owner; credentials/customer data are not copied from development. There is no default lab login. Lab pages are marked SAMPLE; never transfer actual money using their simulated bank instructions.

## Add your first real product

1. In the normal dashboard, open **Collections**, create an active collection with a name/unique slug and optionally a managed cover.
2. Open **Products**, create a draft, then save its title, slug, collection and description. Add short description, material, care, sizing and badge where useful. Drafts can remain incomplete.
3. Add sizes/colors with unique SKUs, exact PKR retail prices and active/available settings. Use up to two decimal places. The server stores integer paisas and rejects duplicate identities/options.
4. Upload your images and supported videos from the product editor or **Media**. Choose a primary image, add/reorder gallery entries and alt text, and optionally associate entries with variants. Assign a poster to every gallery video. Featured placement uses the existing hero controls. Save product/media together and resolve any displayed publish requirements.
5. Load each saved variant's supplier/stock panel. Register or choose an active supplier and save the exact wholesale cost. Receive stock through its audited adjustment form, with a reference/reason/note. The panel separates physical, held and available stock; individual holds link to private orders. Product edits do not directly overwrite inventory.
6. Publish the reviewed product. Refresh the normal storefront and check the card, collection, description, image/video gallery, chosen variant and cart. Check desktop and mobile. Editing a product changes the live catalog; saved carts reconcile identities/prices/availability.
7. Unpublish/archive when needed. Purchased item titles, prices, costs and customer addresses remain immutable order snapshots. Archiving hides purchase paths while owner orders, customer tracking, returns and reports remain accessible.

Use actual managed uploads rather than external demo images. Formats/limits: JPEG/PNG/WebP images up to 10 MiB and 40 megapixels; H.264 MP4 or VP8/VP9 WebM video up to 100 MiB and 120 seconds. Upload failures preserve useful retry feedback; published media and shared posters cannot be removed unsafely.

## Test your selected catalog with checkout

Use the [M8 lab guide](m8_checkout_lab_runbook.md) for exact read-only export and dry-run/import commands. Select stable product IDs explicitly. Optionally include active wholesale costs; supplier contacts, owners, sessions, customer/orders, reservations and financial records are excluded. Media is checksummed, decoded again, copied into the lab volume and remapped.

Choose lab starting quantities explicitly. Imported products start as drafts: review, map suppliers/costs if omitted, and publish in the lab. Identical-bundle reruns skip existing copies without resetting stock or overwriting edits. A new source snapshot is not an automatic synchronization mechanism; slug/SKU collisions require review.

Walkthrough checklist:

- Browse/select a variant, add to cart, enter SAMPLE details and submit. Save the private access code. A lost-response retry recovers the same attempt/order; server prices and reservation locks remain authoritative.
- Check the owner order and exact stock hold. Confirm supplier availability, dispatch with manual tracking/courier cost, record delivery, then actual simulated COD receipt/deductions. Partial receipts remain outstanding until reconciled; delivery alone does not prove payment.
- For bank transfer, supplier acceptance precedes instruction preview/handoff. Only explicit recorded handoff starts the four-hour window. Customer proof is evidence, not cleared funds. Verify independently (simulated in the lab), then record owner verification before dispatch.
- For overdue bank orders, explicitly check expiry, review cleared/pending funds and resolve with an audit note before releasing stock. Eligible unpaid pre-dispatch cancellation releases holds.
- Request a return or size exchange through private tracking. Owner approves, records receipt once, inspects sellable/damaged quantities and completes. Receipt alone does not restock. Completed refunds create a liability; paid refunds need a separate referenced entry. Exchanges have separate replacement allocations/shipments and their own delivery/RTO/settlement.
- For original/replacement RTO, receive and inspect explicitly. Only inspected sellable units return to the fulfilling supplier's stock. Completed replacement inspection is shown as complete; legacy reconciliation remains guarded.
- Read **Reports**: delivered sales, business cash after refunds, courier-held COD, refund outstanding and estimated contribution are distinct. Marketing shows order value, not cash. Reports are operational summaries, not a dated tax/general ledger.

## Persistence, backups and troubleshooting

Database rows and media survive ordinary shutdown/rebuild. Each project has independent `pgdata`/`catalog_media` volumes. Files live at `/var/lib/alphazee/catalog-media` in API containers; metadata stays in PostgreSQL. Back up database and media as one matched set with all writers stopped. The exact procedure and executed restore evidence are in the [M3 storage guide](m3_media_runbook.md). Never restore a test copy into development or pair DB metadata with unrelated files.

```powershell
docker compose --env-file .env.docker.local ps
docker compose --env-file .env.docker.local logs --tail=100 migrate api web
docker compose -f compose.checkout-lab.yml ps
docker compose --env-file .env.docker.local stop
docker compose -f compose.checkout-lab.yml stop
```

Stopping preserves volumes. Do not remove volumes when retaining your catalog/account. If the site cannot reach the API, inspect readiness at `/api/v1/ready` and the logs above. Owner API actions require a valid session, trusted Origin and CSRF; private customer tracking requires an order code/session. Never put owner secrets in browser source or share order codes in screenshots.

For native frontend work, use Node 22.12+ (Docker uses Node 22), `npm.cmd ci`, `npm.cmd test` and `npm.cmd run build`. M9 updates Vite/esbuild security patches; production still serves compiled static assets through Caddy. [Vite's Node requirements](https://v7.vite.dev/guide/migration#node-js-support) explain the runtime prerequisite. Deployment instructions remain in the [Docker guide](docker_deployment_runbook.md).

## Verification and remaining business setup

Final results: 260 backend tests, 108 frontend tests and 228 actual Chrome checks (145 commerce/mobile/archive plus 83 authoring/storefront), with no unexpected browser/network failures. Image builds, isolated migration cycle/comparison and archived-history restart persistence passed. The final npm audit records zero advisories; one existing backend AnyIO deprecation warning remains. See `m9_implementation_report.md` and the phase register for linked evidence. Expected denied requests/offline failures are separated from unexpected failures. Acceptance uses SAMPLE data only, with private codes/passwords excluded from reports/screenshots.

The owner still supplies real products, supplier arrangements, bank/support/legal/recovery details, domain/hosting configuration and a public launch decision. Manual supplier/courier/bank operations remain manual. No automatic bank gateway or courier booking is implied. The local implementation milestone does not authorize deployment or public checkout.
