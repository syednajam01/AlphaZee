# M0 implementation contracts

Recorded 2026-10-14. These are the accepted implementation decisions for M1–M8,
not endpoints or schema fields already available. Keep existing commerce services.

## Catalog identity, drafts and publication

- Stable product/collection IDs are server generated and never change on rename.
  One collection per product; variant options remain size/color (or one default
  variant with both null). Material, care and sizing are descriptive fields.
- Product lifecycle: `draft`, `published`, `archived`. Unpublish returns to draft;
  archived records are read-only until explicitly restored to draft. Archive
  never deletes variants, stock mappings, snapshots or fulfillment evidence.
- An empty product draft may have null title, slug and collection and zero
  variants. Trim strings; empty editable identity fields become null. Unique
  constraints apply to non-null slugs. Existing values/IDs are preserved.
- Persisted variants require SKU and a structurally valid, unique normalized
  size/color combination. A missing draft price is null, not zero; active
  variants require a price. Removing an editor row must not delete a persisted
  referenced variant: deactivate/archive it by ID instead. No hard-delete API.
- Required publication fields: nonblank title; valid unique lowercase slug;
  active collection; nonblank customer description; ready primary image; at
  least one complete active variant. Full description/material/care/sizing and
  hero placement are optional. Invalid hero video/poster references block the
  corresponding hero configuration rather than inventing media.
- Publish response includes all unmet requirements, e.g.
  `{field: "primary_media_id", code: "required", message: "Choose a ready image"}`.
  The UI uses this same server result; it does not implement a conflicting rule.
- Sold-out published products can remain visible. A variant is purchasable only
  when product/collection are publicly visible, variant is active, owner
  availability permits sale, price is complete, active supplier/cost mapping
  is valid and available stock is positive. Zero price/cost is valid under the
  existing nonnegative money rule; null is incomplete. Checkout rechecks all
  eligibility and stock inside the existing locked transaction.
- Catalog edits must not invalidate existing orders' ability to complete their
  previously allocated fulfillment/return flow. New-sale eligibility checks
  belong at order creation, not retroactively in historical operations.
- Backfill legacy active products as published, inactive as draft, preserving
  their visibility/content. Preserve legacy URL media; new writes use managed
  IDs. Do not unpublish legacy records during migration solely because new
  fields are missing; explain corrective requirements on subsequent publication.

## Money, uniqueness and edit conflicts

- UI accepts decimal PKR text, e.g. `3450.50`; exact integer conversion yields
  `345050` paisas. Accept zero to two decimal digits, no exponent/NaN/negative
  values; reject extra precision. APIs write `price_minor`/`supplier_cost_minor`
  integers. Current PostgreSQL INTEGER ceiling is 2,147,483,647 minor units;
  changing that limit requires an explicit migration. Never round invalid input.
- Normalize slugs lowercase and validate URL-safe hyphenated identifiers. Keep
  SKU uniqueness compatible with current case-sensitive PostgreSQL constraints;
  trim and explain case sensitivity. Do not silently merge legacy SKUs by case.
- Option uniqueness uses existing PostgreSQL NULLS NOT DISTINCT rules after
  trimming. Blank option values normalize to null. Concurrent duplicates must
  result in a safe 409, not a 500 containing SQL or credentials.
- Products/collections have monotonically increasing edit versions. Updates
  and lifecycle commands carry `expected_version`; stale versions return 409
  with a conflict code/current version and require review/reload. Price,
  variants, gallery order and metadata changes commit together where submitted
  in one editor save; pending files remain independently staged assets.

## Owner API contract

Proposed routes under `/api/v1/admin`; names become final when M2 is implemented.
Use the existing owner session dependency, Origin/CSRF checks and no-store headers.

| Endpoint | Contract |
| --- | --- |
| `GET /products` | Search by title/slug/SKU; collection/status filter; capped pagination; owner-only draft visibility |
| `POST /products` | Create draft; generated ID/version; optional incomplete fields |
| `GET /products/{id}` | Owner detail, all variants, media associations and readiness reasons |
| `POST /products/{id}` | Version-guarded edit; update variants by stable ID, no replace/delete-orphan operation |
| `POST /products/{id}/publish`, `/unpublish`, `/archive`, `/restore` | Explicit version-guarded transition; no successful publish with unmet requirements |
| `GET/POST /collections`, `POST /collections/{id}` | List/create/edit; active state, descriptive fields and image association |
| `POST /collections/reorder` | Validate complete unique selected IDs and expected versions; atomic order change |
| `GET/POST /media` | Owner library/upload; metadata response only after successful validation |
| `POST /media/{id}/metadata`, `/delete` | Safe metadata edits; reject deletion if any association references it |
| `GET /inventory/{supplier_variant_id}/holds` | Private quantities and order links matching stock aggregation |

POST edits deliberately fit the current CORS method allowlist; no new PUT/PATCH
assumption. JSON errors distinguish `validation_failed` (422), `edit_conflict` or
`duplicate_*` (409), not-found (404), authentication (401), authorization/CSRF
(403), and media too-large (413)/unsupported (415). Keep existing operation
endpoints and response compatibility intact. All requests have pending/error
states; success requires a server response. Document final schemas in OpenAPI.

## Managed media and file boundaries

- Asset metadata: immutable UUID/storage key, validated MIME/codec, bytes,
  checksum, dimensions/duration, creator, timestamps and staging/ready state.
  Product association: asset ID, product ID, optional variant ID, alt text,
  display order and role. Roles cover primary/gallery, hero image/video/poster;
  collection covers reference assets separately. A poster must be a ready image.
- Initial formats: JPEG/PNG/WebP and MP4 H.264/WebM VP8 or VP9. Planned limits:
  10 MiB/image, 100 MiB/video, 40 megapixels/image and 120 seconds/video. Validate
  bytes by bounded decoding/probing, not extensions or user MIME alone. Reject
  SVG/HTML/executables/corrupt uploads. Implementation must verify parser and
  multipart package versions before adding dependencies.
- Files: `/var/lib/alphazee/catalog-media` in the container, one named Docker
  volume per environment; staging is not served. Generated names only, no
  client path components or remote-URL fetching. Atomic move plus ready-state
  publication; clean orphaned files by an explicit age-based scoped tool.
- Product media is public, including a draft's asset if its URL is known; owner
  UI must state this. A controlled `/api/v1/media/{id}/content` serves validated
  files with appropriate type/nosniff and video byte ranges. Private payment
  evidence stays entirely outside this service/root and order-scoped access
  remains enforced. This milestone does not add payment-file uploads implicitly.
- Detach does not delete a shared file. Delete checks every product, variant,
  collection and poster dependency while locking against concurrent attachment.
  Replace creates a new immutable asset key. Require replacement/unpublish when
  removal would break publication requirements. Back up DB and media together.

## Stock-hold response and privacy

Example owner-only response (IDs are illustrative):

```json
{
  "supplier_variant_id": "uuid",
  "physical": 10,
  "held": 2,
  "available": 8,
  "inventory_version": 4,
  "holds": [
    {"reservation_id": "uuid-1", "quantity": 1, "stage": "held",
     "order_id": "order-1", "order_number": "ABC", "order_path": "/admin/orders/order-1"},
    {"reservation_id": "uuid-2", "quantity": 1, "stage": "confirmed",
     "order_id": "order-2", "order_number": "XYZ", "order_path": "/admin/orders/order-2"}
  ],
  "total_holds": 2
}
```

Reuse `OPEN_RESERVATION_STAGES` and `legacy_stock_hold` from current reservation
queries; no second definition of an active hold. Paginate holds while keeping
the aggregate across all matching rows. Explain any legacy discrepancy rather
than fabricate a reconciliation. Dashboard can say “2 units reserved for orders
#ABC and #XYZ.” Public schemas contain no holds, supplier/wholesale cost, owner
identity, internal audit notes or customer/order details. Normal public media,
retail price, variant options and derived availability are permitted.

## Isolation map

| Purpose | Target/storage | Use |
| --- | --- | --- |
| Normal owner/catalog | `alphazee_dev`, loopback 5433; web 13000/API 18000 | Real owner data; public checkout disabled |
| Backend regression | Guarded `alphazee_test` on loopback 5433 | Existing fixture controls schema; run suites sequentially |
| Backup restore | Generated `alphazee_m0_restore_<random>_test`; archive under `.local/backups` | Private restored development data; never browser fixtures or checkout lab |
| Future migrations | Unique `alphazee_migration_<random>_test` | Historical fixtures; upgrade/backfill/reversible rollback only here |
| Future browser/checkout | Distinct project/`alphazee_catalog_browser_test`; web 127.0.0.1:13001, API 18001, DB 5434 proposed | Selected catalog only, independent owners/media and SAMPLE customers |

M3 creates media volumes; they do not exist yet. M8 must preserve loopback test
gate, normalize source/destination identity, separate cookies (ports do not
isolate cookies), and never copy customer/order/credential rows. Restore clones
contain private development information even if current commerce tables are
empty. No API is started against the restore clone. Retain its database/archive
for inspection and intentional private backup management; do not add it to Git.
