# M6 — managed storefront and saved-cart recovery

Implemented 2026-10-15. Keep using **http://localhost:13000/admin** to manage products and **http://localhost:13000** to preview the customer site. Existing styling, navigation and the closed public checkout gate are preserved.

## Owner-to-customer flow

1. Create a collection and product in the dashboard; save active variants with exact PKR prices. Upload images/videos, assign a primary image, ordered gallery, optional variant associations and image posters for videos. Material, care and sizing are displayed as customer detail fields.
2. Save and publish. Only published active products in active collections enter the storefront. Inactive variants and their associated media are omitted. Published sold-out products remain visible with an unavailable state; publishing alone does not create stock.
3. Set the collection cover and optional hero placement/media through the existing screens. Cards use managed primary images, collections use their saved covers and hero slides use saved hero image/video/poster fields. Missing/broken images use the existing neutral AlphaZee placeholder; empty/error states have recovery controls.
4. Open **View Options**. The detail dialog loads fresh public data, defaults to an available variant when possible, and shows description, material, care, sizing and the ordered gallery. Variant-specific media is scoped to that exact selection; the selected variant image is preferred, otherwise the primary image is shown. Native image/video buttons support keyboard interaction and announce selection.
5. Select a video to see its poster and playback controls. Gallery videos use `preload=none`, never autoplay, and pause when changing media/variant or closing the dialog. Unsupported/unplayable media shows a recoverable message. Product grids contain images, not automatically downloading video previews. Nonprimary images load lazily; layouts remain responsive.
6. Add the selected variant to the cart. Cart and checkout summaries use its actual managed image. Reopening the cart or checkout rechecks current prices/availability. Exact variant identity is preserved: no silent substitute is chosen when an option disappears.

## Owner edits, refresh and stale carts

Accepted product/collection/media/supplier/stock writes announce a timestamp to other same-origin tabs. The storefront refetches on that announcement, on returning to the tab, and on browser page restoration. Product-detail requests and public JSON bypass stale HTTP caches. A normal customer page refresh also loads current catalog data.

Saved carts resolve via **stable product ID**, then match the exact variant ID. Slug changes update the saved slug, price, title, SKU/options and image while preserving quantity/variant identity. Legacy carts with only a slug still resolve by slug and exact variant; items with no resolvable identity remain unverified. Unpublish/archive, inactive collections, inactive variants and sold-out stock block the saved item. Network failures retain it as unverified, allowing a later retry. Items added during an in-flight reconciliation wait for their own verification. Unavailable/unverified or currently reconciling carts cannot submit checkout.

Checkout and order services still lock/recheck authoritative catalog and stock. Displayed availability is a snapshot, not a reservation. Public ordering remains disabled; M8 supplies the separate checkout lab.

## API, compatibility and privacy

- Existing slug detail: `GET /api/v1/products/{slug}`. New stable identity detail: `GET /api/v1/catalog/products/{product_id}`. Both obey the same publication/collection/variant rules and return 404 for inaccessible products.
- Detail `media` contains explicit public asset ID, role, variant association, order, alt text, kind/MIME, dimensions, duration, content URL and ready poster URL. Storage paths/keys, filenames, checksums, creator identity, supplier costs, balances, holds and customer data are excluded.
- Public cards/hero include primary alt text and aggregate purchase availability. Pagination counts/order remain consistent; variant ordering is stable by ID. Media and posters are eagerly loaded to avoid one database query per gallery item. Managed ready roles take precedence over compatibility URLs; existing legacy catalog URLs remain supported.
- No schema migration or configuration reset is needed. Head remains `f27b6d91c083`. Existing database/media volumes and owner credentials are preserved.

## Verification and repeatable checks

The full backend suite passed **249 tests**; the final catalog/media rerun passed **26 tests**, followed by **3** ordering/media contract tests. Frontend passed **102 tests**, including controlled gallery playback/cleanup, unsupported media, initial variant selection, stable-ID cart updates, legacy slug safety, reconciliation races and owner-change refresh. Development and production Docker builds passed. Alembic check found no new upgrade operations.

Actual isolated Chrome passed **83 checks with zero unexpected runtime/console errors**. Results/screenshots are recorded in `m6_browser_verification.json`; counts are in `owner_catalog_phase_status.json`. The journey includes M4/M5 regressions, managed cards/collection cover/hero, gallery playback, variant stock/media, accepted owner edits, slug/price recovery, mobile layout and purchase-path removal. The mobile gallery screenshot was inspected. SAMPLE fixtures stay in the separate media-check database/volumes; checkout stays disabled and that stack is stopped after acceptance. `m6_development_verification.json` confirms development catalog/media/orders/mappings remain empty and the existing owner remains enabled. No plaintext credentials are recorded.

Reproduce with the separate `compose.media-check.yml` stack and `backend\.venv\Scripts\python.exe backend/scripts/verify_m4_browser.py --phase-m6`. Normal startup remains `docker compose --env-file .env.docker.local up --build --wait -d`. Production still requires environment-specific setup and an explicit deployment; building images does not deploy them. M7 is the next phase after M6 acceptance.
