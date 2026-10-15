# AlphaZee: owner dashboard, catalog and media implementation plan

Date: 2026-10-14. Source: `next_target.txt`. Updated 2026-10-15: M0–M8 completed; M9 pending. See [M8 evidence](m8_checkout_lab_runbook.md) and `owner_catalog_phase_status.json`. The owner selected opening checkout only in the isolated lab.

This plan was originally prepared at the owner's planning-only request. The owner has since authorized phase implementation. The target's explicit browser acceptance requirements supersede the earlier terminal-only verification approach for the relevant future phases; M0 is a terminal baseline with a private isolated backup restore.

## Goal and completion boundary

The owner opens `http://localhost:13000/admin`, logs in, creates collections and actual products, uploads images/videos, configures variants, supplier costs and stock, publishes, and sees the result at `http://localhost:13000`. Routine catalog work must require neither source edits nor SQL/seed scripts. Existing commerce operations remain accessible. A separate environment supports sample orders and simulated payment verification. No production deployment or public checkout enablement is included.

## Inspected baseline

| Area | Existing implementation | Required extension |
| --- | --- | --- |
| Frontend startup | `main.js` loads `app.js`; storefront mounts `AdminConsole.js` as a modal | Routed dashboard with direct login, refresh and section navigation |
| Owner protection | `/auth` sessions, hashed passwords/tokens, trusted Origin, CSRF, logout, expiry and rate limiting | Apply unchanged protections to every new owner endpoint, including uploads |
| Catalog | `Collection -> Product -> Variant`; unique slugs/SKUs and size/color combinations; active flags; existing hero fields | Draft/published/archived lifecycle, descriptions/details, owner editing/search and publication validation |
| Schema constraints | Product currently requires title, slug and collection; variant requires SKU/price; product relationship has delete-orphan cascade | Explicit incomplete-draft strategy and protection against accidental variant deletion |
| Media | URL fields only; hero supports video/poster references; no managed upload library | Validated binary uploads, durable files, metadata, associations and safe cleanup |
| Availability | Public catalog serializes the manually set variant availability flag | Derive purchasability using existing supplier/stock rules as well as the owner availability switch |
| Inventory | Physical/held/available totals, locked stock adjustments, reservation and event services | Per-order hold explanation and links, plus product-editor integration |
| Operations | Orders/payments, suppliers, coupons, returns/exchanges and financial reports already exist | Reuse inside dashboard; preserve lifecycle/accounting services |
| Runtime | Development Compose, production Caddy/static image, migrations and readiness | Media volumes/serving; isolated checkout profile; `/admin` deep-link behavior |
| Test checkout | `start_browser_test.py`, test Vite proxy; gate requires test mode and loopback PostgreSQL `_test` database | Documented, durable test stack with distinct DB/media and controlled catalog copying |
| Verification | Last recorded: 209 backend / 83 frontend tests and builds passed; browser acceptance unverified | New regression, migration, media durability and actual browser evidence |

Primary inspected files: `backend/app/models/catalog.py`, `schemas/catalog.py`, `queries/catalog.py`, `models/inventory.py`, `queries/inventory.py`, `api/v1/admin.py`, `config.py`, `scripts/start_browser_test.py`; frontend startup, `AdminConsole.js`, `utils/api.js`, `utils/dom.js`, Vite/Caddy configuration; Compose and existing runbooks. No `AGENTS.md` was found by the repository file search. Check again before implementation if repository instructions change.

## Decisions that apply across phases

- Preserve development records, local configuration and volumes. Add migrations after the actual current head (last verified `c94e31f7d562`); never edit an applied migration. Test upgrades/backfills/rollback on an isolated copy before applying development upgrades.
- Keep the current visual identity and vanilla JavaScript stack. Extract reusable dashboard sections instead of duplicating `AdminConsole.js` or replacing tested commerce services.
- Keep one collection per product and the existing size/color options for this milestone. A product without options has one default variant. Material/care/sizing are descriptive fields, not a new generalized options engine. Reuse `is_hero`, hero order/benefit and media roles for featured placement.
- Publication and stock are distinct: a complete published product may be sold out. Purchasability additionally requires an active variant, owner-permitted availability, valid active supplier mapping/cost and positive available stock; order creation still validates under locks.
- Use exact decimal-text parsing for PKR input (at most two fractional digits) and integer paisas in APIs/storage. Reject negative values, excessive precision and amounts outside database/JavaScript safe bounds. Do not use `parseFloat(value) * 100` for writes.
- Product/variant archiving changes future sales visibility, not existing orders, allocations, prices, costs, returns or reporting. No catalog hard-delete endpoint in this milestone. Unpublish/archive must also block direct checkout attempts and stale carts.
- Catalog product assets are public resources; draft previews must make that clear. Payment evidence never enters this media library or public asset root. Existing private order access protections remain mandatory.
- Use server-confirmed success, clear validation, pending states and recoverable errors throughout. Do not fabricate data to fill empty dashboards.

## Phase M0 — baseline, isolation and implementation contracts

**Dependencies:** none. **Deliverable:** a protected baseline and agreed API/schema contracts.

1. Record working-tree changes, current revision, service ports, test targets and relevant row counts without logging credentials. Preserve unrelated changes, including existing test-fixture file issues.
2. Verify normal stack readiness, checkout-disabled capabilities and anonymous owner rejection. Record current suite/build results; older counts are evidence, not a fresh execution.
3. Back up the development database before schema work and prove backup restoration in a disposable target. Establish separate migration/test database labels and file roots.
4. Define draft/publication field requirements, media roles, stock-hold response shape, edit-conflict behavior and public/private serializers before UI work.
5. Establish evidence files for this milestone: phase status, migration results and browser checklist. Do not overwrite the earlier completed repair plan.

**Acceptance:** source data/config remain unchanged; verification targets are demonstrably isolated; schema/API decisions are recorded. Completed 2026-10-14: backup restored, row/config and normalized schema/sequence comparisons passed, 209 backend and 83 frontend tests passed, frontend build passed. Contracts: `m0_catalog_media_contracts.md`; evidence: `m0_implementation_report.md` and `m0_baseline_verification.json`.

## Phase M1 — direct `/admin` entry and dashboard shell

**Dependencies:** M0. **Likely files:** frontend startup/router, new admin shell/section modules, existing API/session utilities, `AdminConsole.js`, Vite and Caddy configuration.

1. Route `/` to the existing storefront and `/admin` to a full-page owner login/dashboard. Use bookmarkable section routes, for example `/admin/products`; handle refresh, back/forward, unknown sections and authenticated order links.
2. Fetch the owner session on entry; show a loading state, login on 401, and dashboard on success. Reuse login/logout/expiry handling and CSRF memory state. Do not flash private content while checking authentication.
3. Provide navigation for Overview, Products, Collections, Media, Inventory, Suppliers, Orders and payments, Returns and exchanges, Coupons and Reports. Reuse operational sections; show honest empty/new-section states while later phases are pending.
4. Change the storefront owner link to `/admin`; keep a clear return-to-store link. Extract modal-specific close/focus logic so it does not trap focus or lock scrolling on the full-page dashboard.
5. Support narrow screens, keyboard navigation and unsaved-edit warnings. Ignore stale requests after navigation, as the current console already does.
6. Verify SPA fallback for `/admin/...` in Vite and the production Caddy image. Document existing interactive provisioning/reset commands without creating default credentials.

**Acceptance:** direct login, navigation, refresh, expiry and logout work; protected APIs reject anonymous requests independent of frontend state. Existing operations still render and call their original endpoints. Completed 2026-10-14: 87 frontend tests, 25 backend auth/session tests, frontend/production-image builds and 13 isolated Chrome checks passed. See `m1_dashboard_runbook.md` and `m1_browser_verification.json`.

## Phase M2 — catalog lifecycle, schema and protected APIs

**Dependencies:** M0; can proceed alongside M1. **Likely files:** catalog models/migrations; new owner catalog schemas, router and service; public catalog queries; order eligibility checks.

1. Add explicit draft/published/archived state, archived timestamp, short/full descriptions, material/care/sizing fields and edit version. Treat lifecycle state as authoritative; keep legacy `is_active` compatibility centrally synchronized rather than allowing contradictory writes.
2. Support a draft without collection, media or variants. Use generated immutable IDs; allow incomplete editable identity fields through compatible nullability changes, with publication validation requiring title/unique slug/active collection. Preserve existing IDs and valid legacy values. Backfill existing active records as published and inactive records as unpublished drafts; do not invent content or stock.
3. Persist only structurally valid variant rows; allow inactive variants with missing price via an explicit nullable draft field if needed. Require unique SKU and valid option combination before saving a variant; allow a product draft with no variants while those inputs remain unfinished. Activation/publication explains missing price or options. Never represent a missing price as zero.
4. Replace destructive nested variant replacement with ID-based updates and explicit deactivate/archive actions. Preserve variants with order/inventory references and keep existing order snapshots untouched.
5. Add owner product list/search/filter/pagination/detail/create/update endpoints; separate publish, unpublish and archive commands. Add collection list/create/edit/reorder/activate/deactivate and hero-placement management. Use owner-specific schemas rather than exposing ORM objects.
6. Return field-level validation and 409 conflicts for duplicate SKU/slug/option combinations or stale edit versions. Enforce constraints in PostgreSQL as well as service validation. Normalize whitespace and define case handling consistently.
7. Publish only with a valid title/slug/active collection, required customer description, ready primary image and at least one complete active variant. Return an actionable list of unmet requirements. No stock requirement for publishing; explain sellability separately.
8. Preserve existing catalog URLs/legacy media references during migration. Media readiness validation becomes active with M3; no bypass that accidentally publishes new incomplete records. Enforce published visibility in all public list/detail/hero and order-entry paths.

**Acceptance:** owner-only catalog writes, incomplete draft saves, actionable publish rejection, conflict handling and historical-order preservation pass API tests. Migration upgrades/backfills and any reversible downgrade pass on isolated historical fixtures; no development downgrade is used. Completed 2026-10-14: migration/backup verification, 218 backend tests, final 17 focused catalog tests, 88 frontend tests/build and browser checks. New publication remains guarded until M3 ready media; authoring UI remains M4. The stale Docker Vite `/admin` module issue was corrected with polling/restart. See `m2_catalog_runbook.md`.

## Phase M3 — upload storage and media service

**Dependencies:** M2 schema foundation. **Likely files:** media models/migration/service/router, storage configuration, backend dependencies/Dockerfile, Compose volumes and public serving routes.

1. Store file metadata separately from associations: asset ID, generated storage key, validated type, byte size, checksum, dimensions/duration, upload state and creator; product association includes display order, alt text, optional variant ID and presentation role. Reference poster assets explicitly. Cover collection images and hero image/video/poster roles in shared-reference checks.
2. Initial supported uploads: JPEG/PNG/WebP images and MP4 (H.264) or WebM (VP8/VP9) videos. Proposed limits: 10 MiB/image, 100 MiB/video, 40 megapixels/image, 120 seconds/video. Enforce actual content/codec validation through image decoding and bounded media probing, not just MIME/extension. Pin and verify the selected parser/multipart dependencies and required container binaries during implementation.
3. Require owner session, Origin and CSRF for upload/metadata/delete operations. Stream with byte limits, bound parser work, reject corrupt files, SVG/HTML/executables, mismatched types and unsafe paths. Generate immutable server filenames; never trust client filenames as filesystem paths. Do not fetch arbitrary remote URLs server-side.
4. Stage uploads outside the served area, validate, atomically move to final storage, then mark ready. Attach only ready assets. Compensate failed saves; track orphaned staged/ready files for an explicit age-based cleanup tool. A crashed upload must not leave a successful product reference to a missing file.
5. Serve product assets through a dedicated public route, e.g. `/api/v1/media/{asset_id}/content`, using controlled content types, `nosniff`, immutable keys and byte-range support for video seeking. Invalid asset IDs return a file error, never the SPA index.
6. Mount a named catalog-media volume at `/var/lib/alphazee/catalog-media`; staging stays outside the public subtree. Use separate volumes for development, production and checkout test projects. Set non-root write permissions; avoid storing uploads in the image or source tree.
7. Detaching a product image removes an association only. Refuse deleting referenced files, including poster/collection/hero dependencies; serialize attach/delete decisions to prevent races. Never overwrite bytes behind an existing public key. Require a replacement primary image or unpublish before removing the last publish-required image.
8. Document DB-plus-media backup/restore as one consistent set, the container path and how to discover the actual Docker volume name. Restart/rebuild must retain assets.

**Acceptance:** valid image/video uploads survive restart; oversize/corrupt/disguised/path-traversal uploads fail; shared references survive detach/delete attempts; failed transactions leave no broken references; private payment evidence is never publicly served. Completed 2026-10-15: isolated migration, 13 real Docker media checks, asset checksums after restart/recreation/matched restore, and persistent owner login passed. See `m3_media_runbook.md`.

## Phase M4 — usable Products, Collections and Media screens

**Dependencies:** M1–M3. **Likely files:** new admin catalog/media components, shared form/money/upload utilities, API client and existing styling.

1. Products list: search, collection/status filters, pagination, draft/published/archived badges, edit links and explicit publish/unpublish/archive actions.
2. Product editor: identity, descriptions/details, collection, badge/hero settings, variant table with unique SKUs, sizes/colors, exact PKR prices and active controls. Show validation next to fields and separate publication requirements from sellability requirements.
3. Save drafts without losing unfinished form content after server errors. Persist complete edits atomically; show saved version/time only after confirmation. Handle concurrent edit conflicts with reload/review, not silent overwrite.
4. Collections editor: names/slugs/descriptions, media selection, active state and accessible ordering controls. Explain that deactivating a collection hides its products publicly without deleting them.
5. Media library: local file picker, multiple-image/video selection, previews, real upload progress via a compatible upload client, retry/cancel, alt text and attachment usage. Keep progress, validation and final server acceptance distinct. Revoke temporary object URLs when finished.
6. Product gallery: choose primary image, reorder using keyboard-capable buttons (drag optional), replace/remove associations, assign media to a variant, choose video poster and hero media. Saving descriptions must not accidentally discard gallery changes.

**Acceptance:** the owner creates a collection and draft with variants/media, revisits it, edits it and publishes without source/SQL changes. Failed upload/save retains useful input; no false success or dead controls. Completed 2026-10-15: product/collection/media screens, atomic detail/gallery saves, error recovery and 34 isolated Chrome checks passed; 234 backend and 92 frontend tests plus builds passed. See `m4_catalog_authoring_runbook.md`. M5 was subsequently authorized and completed; see its evidence below.

## Phase M5 — supplier setup and readable stock holds

**Dependencies:** M2/M4. **Likely files:** existing supplier/inventory schemas and endpoints, reservation queries, Products/Inventory/Orders sections.

1. Link each variant directly to the existing supplier creation/mapping and wholesale-cost flow. Keep the one-active-supplier invariant and existing historical supplier allocation behavior.
2. Offer a stock-adjustment action alongside the variant, calling `adjust_inventory` with expected version, reason and note. Product saves must never overwrite balances or manufacture stock events.
3. Add an authenticated hold-detail endpoint per supplier variant. Return reservation ID, quantity, stage, order ID/number and a dashboard order link. Sum exactly the same open/legacy hold predicate used by existing stock enforcement; avoid inconsistent totals between endpoints.
4. Display physical, reserved and available separately; e.g. `10 / 2 / 8`, then `2 units reserved for orders #ABC and #XYZ`, expandable into individual quantities. Handle multiple holds, legacy reconciliation and zero holds; paginate large lists.
5. Derive public purchase availability from the current mapping/stock and owner availability setting. Public responses expose no wholesale costs, supplier identities, reservation details or customer data. Stock remains authoritative at locked checkout time.

**Acceptance:** reservation details reconcile with aggregate totals; cancellation releases holds, dispatch deducts once and inspection restocks only accepted quantities. Existing concurrency tests still pass; unauthorized hold reads fail. Completed 2026-10-15: inline supplier/cost/stock, shared hold predicate, paginated order links, supplier history and private stock-based public availability. 246 backend / 96 frontend tests, 55 Chrome checks, builds and no-schema-change verification passed. See `m5_supplier_stock_runbook.md`.

## Phase M6 — real storefront integration

**Dependencies:** M3–M5. **Likely files:** public catalog schemas/queries, Hero, Collections, FeaturedProducts, ProductModal, cart/checkout and safe media helpers.

1. Serve only published eligible catalog records and active variants; inactive collections hide their products. Keep accurate pagination/counts and stable order. Sold-out published products can display an unavailable state.
2. Deliver primary image and ordered media metadata through explicit public serializers. Product details show descriptions/material/care/sizing, image gallery, supported video with poster and variant media. Preserve existing page styling; no broad redesign.
3. Connect cards, hero, collections, variant selection, cart and checkout snapshots to real managed assets. Use genuine empty/error states and the existing neutral placeholder where appropriate; no random/demo photo substitution.
4. Refetch after owner changes or customer refresh. Reconcile stale carts on price, variant activation, unpublish and archive changes. Treat slug changes explicitly so a saved cart can resolve by stable identity or show a recoverable unavailable item instead of silently changing variants.
5. Keep images responsive and lazy-load nonprimary media; avoid automatic video downloads in product grids. Provide playback controls and useful unsupported-media feedback.

**Acceptance:** changes to description/price/primary media survive refresh and appear on the storefront; archive/unpublish removes purchase paths; public JSON contains no private fields; the existing design and navigation remain functional. Completed 2026-10-15: explicit public managed-media contract, stable variant order, responsive image/video gallery and detail fields, managed cards/hero/covers, stable-ID stale-cart recovery, checkout gating and accepted owner-change refresh. 249 backend / 102 frontend tests, 83 isolated Chrome checks and Docker builds passed. See `m6_storefront_runbook.md`.

## Phase M7 — operational dashboard and reports completion

**Dependencies:** M1, M5; integrate after M6 for a complete owner journey.

1. Move/reuse all existing operational actions in routed sections: supplier confirmation, instruction handoff, proof review, expired-payment review, cancellation, dispatch/status, RTO receipt/inspection, returns/exchanges, replacement dispatch, refunds, COD settlement, access recovery/revocation and coupons.
2. Stock-hold order links open the correct order directly. Keep confirmation/error/pending states and refresh affected totals after mutations. Opening a tab must not perform business mutations.
3. Preserve supplier acceptance before bank instruction handoff, the four-hour window, explicit review before hold release, and owner verification of funds. Payment screenshots are evidence only.
4. Overview/Reports consume existing backend figures. Use names such as delivered sales, cash received, courier-held COD, refund outstanding and estimated contribution. Preserve append-only evidence and prevent duplicate courier expense counting. Provide truthful empty states.

**Acceptance:** every navigation item and operation is connected to its existing service; no duplicate lifecycle/accounting implementation; historical records remain accessible after catalog edits/archival.

## Phase M8 — separate checkout lab and selected-catalog copy

**Dependencies:** M3–M7; infrastructure can be prepared earlier after M0. **Deliverables:** separate Compose profile, guarded transfer tool, test configuration and walkthrough runbook.

1. Keep normal site/admin on `localhost:13000` with checkout disabled. Create a clearly named test project, `_test` database and independent catalog-media volume; proposed web URL `http://127.0.0.1:13001`, API host port 18001, PostgreSQL host port 5434. Label all test screens prominently.
2. Preserve the literal loopback gate: an API using `DATABASE_URL=...@db:5432/...` will fail it even in a test container. Proposed Docker solution: test API/migration containers share the test DB network namespace (`network_mode: service:db`), connect to `127.0.0.1:5432`, and publish the API port on that namespace's service. Test web proxies to that service at port 8000. Validate on Docker Desktop before adopting; if unsupported, extend the existing host API launcher against the separate loopback test DB instead of relaxing the gate.
3. Keep test allowed origins exact and test settings isolated. Cookies are not port-isolated: use distinct documented hosts and test-specific cookie names for owner, checkout and order access, preserving normal/production behavior. Verify both environments can remain logged in simultaneously and tokens never authorize the other database.
4. Implement an explicit selected-product export/import tool with dry-run manifest. Read source through a read-only transaction; copy selected products/variants, collections and their managed media/posters only. Include only necessary supplier mapping/cost data with deliberate selection; never owner credentials/sessions, customer/order data, reservations, financial records or unrelated supplier contacts.
5. Remap IDs/references in the destination; checksum files; validate formats/paths again; handle collisions and reruns deterministically. Reject any destination matching the normalized source or lacking the test gate. Do not share source filesystem paths, mutate source metadata or automatically synchronize later changes.
6. Let the user specify test starting quantities; apply these through the existing audited stock-adjustment service with a SAMPLE/TEST reason. Never copy active reservations or infer test inventory from orders. Import into staged data, validate, then commit; on failure clean only the import's own files/records. Default imported products to drafts for review.
7. Provision a separate test owner interactively. Provide synthetic bank configuration usable only in the guarded lab; reject it elsewhere. Label instruction handoff/payment verification as simulated and require no real transfer. Use a controlled test clock/isolated fixtures for expiry tests without changing the production timer.
8. Write exact create/start/status/stop/import/provision commands and URLs once scripts exist. Back up test data if preserving a walkthrough; cleanup must target only the named test project/roots.

**Acceptance:** selected catalog/media copies work with no source writes and no customer data copied; both stacks coexist; test checkout works while normal/direct API checkout stays 503; cookies/media/storage remain isolated.

## Phase M9 — regression, browser acceptance and handoff

**Dependencies:** all prior phases. **Deliverables:** actual execution evidence, updated summary/runbooks and owner first-product guide.

### Automated and migration checks

- Owner API authentication/CSRF/Origin tests for all new CRUD/upload/hold endpoints; expired-session and private-field leakage cases.
- Draft/publish/archive validation, duplicate and concurrent SKU/slug conflicts, stale edit version, exact paisa conversion and historical-order preservation.
- Upload decoding/type/size/timeout/path checks, poster/shared references, attach-versus-delete races, failed-save cleanup, media range responses and restart persistence.
- Public visibility and stale-cart checks; real PostgreSQL reservation/stock/settlement regressions and repeated selected-catalog import without duplication/source changes.
- New migrations tested on disposable legacy fixtures: upgrade, backfill inspection, reversible downgrade where safe, re-upgrade, and Alembic schema comparison. Development receives forward migration only after validation.
- Run focused tests first, then full backend suite, frontend tests, production frontend build, development/production Compose validation and image builds. Document actual counts/warnings and evaluate the previously reported dependency advisories when selecting new dependencies.

### Browser evidence: isolated data only

| Journey | Required observation |
| --- | --- |
| Direct dashboard | Open `/admin`, login, navigate, refresh, back/forward; check desktop and mobile |
| Author catalog | Create collection and draft, add variants, upload multiple images and supported video/poster, map supplier/cost, set stock, publish |
| Public product | Check collection/card/detail/gallery/video/variant/cart against saved data |
| Edit/persist | Edit description, fractional PKR price and primary image; reload; restart/rebuild app and confirm rows and media bytes survive |
| COD | Place an isolated order, confirm hold/order link, supplier acceptance, dispatch, delivery, partial/final courier reconciliation and reports |
| Bank | Supplier acceptance, simulated instruction handoff, proof submission, explicit simulated verification; separate overdue-review/cancel case |
| Retry/cancel | Lost response/repeated submit creates one order; eligible cancellation releases the expected hold |
| Returns | Receive/inspect a refund return, record separate refund payment; test size exchange and replacement shipment/RTO paths |
| Archive/history | Archive purchased product; public purchase paths disappear while original order/return/report snapshots survive |
| Security/errors | Logout/expiry rejects protected actions; invalid upload/input, offline API and failed save show useful errors; test and normal sessions remain isolated |

Capture browser Console/Network failures and screenshots at representative desktop/mobile sizes; verify keyboard controls, responsive tables, scroll and media playback. Use authored SAMPLE/TEST assets in isolated data, never demo inserts into the actual catalog. Browser fixtures must contain no real customer data or logged passwords/access codes.

If browser tooling is unavailable, mark those checks **not executed**, record the reason and provide exact manual steps with expected outcomes. Do not claim full milestone acceptance from unit tests alone.

### Final owner handoff

Update `summary.md`, the control register and deployment guide; add a concise catalog/media runbook with: normal startup/admin/storefront URLs; interactive provisioning/reset commands; first real product steps; media paths and backup/restore; separate checkout setup/import commands; COD/bank/cancellation/return walkthrough; verification results and remaining limitations. Existing normal commands remain:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME
docker compose --env-file .env.docker.local exec api python scripts/provision_owner.py YOUR_USERNAME --reset-password
```

Only execute the relevant provisioning or reset command interactively. Future test-profile/tool commands must be documented from implemented files, not presented as already available.

## Execution order and tracking

Recommended order: **M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9**. Build the isolated runtime early enough to run browser checks as each vertical flow becomes usable. Each phase ends with its acceptance evidence and an update to this status register; a phase is not complete merely because its files exist.

| Phase | State | Completion evidence to record |
| --- | --- | --- |
| M0 Baseline/contracts | Completed | `m0_implementation_report.md`; backup restore, baseline checks and contracts |
| M1 Dashboard entry | Completed | `m1_dashboard_runbook.md`; direct route, auth, navigation, browser and production deep links |
| M2 Catalog domain/API | Completed | `m2_catalog_runbook.md`; migration, backups, protected lifecycle, concurrency and history tests |
| M3 Managed media | Completed | `m3_media_runbook.md`; migration, validation, references, restart/recreate and matched restore |
| M4 Authoring screens | Completed | `m4_catalog_authoring_runbook.md`; atomic authoring, 234 backend / 92 frontend tests, 34 Chrome checks |
| M5 Supplier/stock details | Completed | `m5_supplier_stock_runbook.md`; 246 backend / 96 frontend tests, 55 Chrome checks |
| M6 Storefront | Completed | `m6_storefront_runbook.md`; 249 backend / 102 frontend tests, 83 Chrome checks |
| M7 Operations/reports | Completed | `m7_operations_runbook.md`; 251 backend / 107 frontend tests, 65 isolated Chrome checks |
| M8 Checkout lab | Completed | `m8_checkout_lab_runbook.md`; 260 backend / 107 frontend tests, 98 Chrome checks, selected media copy and restart proof |
| M9 Acceptance/handoff | Pending | Actual tests/browser results and owner guide |

Final success means routine real-product management is possible through `/admin`, products and durable media appear correctly on the storefront, historical commerce data remains valid, and isolated checkout walkthroughs have documented execution evidence. Public ordering and production deployment remain outside this milestone.
