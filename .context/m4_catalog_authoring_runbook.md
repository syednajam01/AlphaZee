# M4 product, collection and media authoring

Implemented 2026-10-15 on the existing vanilla JavaScript dashboard. Open **http://localhost:13000/admin** and sign in with your provisioned account. Products, Collections and Media now have working authoring screens. M5 and later phases remain pending; implementation stops after M4 at the owner's request.

## First product

1. Open **Collections → New collection**. Enter name/slug/description, choose a previously uploaded cover if desired, and save. Move up/down orders collections with version checks. Deactivating a collection hides its products without deleting history.
2. Open **Products → New draft**. An incomplete draft is immediately saved. Fill title, slug, collection and customer description; material/care/sizing, short description, badge and hero placement are optional.
3. **Add variant**. Enter a unique SKU, optional size/color, and an exact PKR price such as `123.45`. Activate complete variants. A product without options uses one default variant. Blank inactive prices remain unset; existing variants can be deactivated, never silently deleted.
4. Use the local file picker to upload multiple supported images/videos. Queue previews, transport progress, server validation, accepted/error states, retry and cancel are distinct. Files only enter the library after the server accepts them. Uploaded files are public even while the product is a draft.
5. Choose a library asset and role, then **Attach asset**. Select a primary image, additional gallery files, hero image/video/poster, alt text and optional gallery variant. Use keyboard-accessible Move up/down buttons to order the gallery. Attaching another primary/hero asset replaces that role; Detach keeps the file in the library.
6. For videos, open **Media**, select an image poster and **Save poster**, then revisit the product. Featured video attachment can reuse that explicit poster. A gallery video without a poster blocks publication.
7. **Save product and media** commits descriptions, variant edits and gallery together in one database transaction/version increment. Collection details and cover selection are also atomic. Failed validation/conflicts leave saved data unchanged and retain form input. Read the publication requirement list, then **Publish**. No stock is fabricated by publishing.

Products support search by title/slug/SKU, collection/status filters, pagination, revisit/edit, publish/unpublish, archive and restore-to-draft. Archive removes public purchase visibility while preserving records. Media shows dimensions/bytes, playback/image previews and attachment usage; **Delete unused file** is blocked until all product/collection/poster references are detached.

## Errors, refresh and boundaries

- Pending requests disable repeat actions and replace old success messages. Success/version appears only after acceptance. Validation messages identify fields; 409 conflicts keep the form and require explicit reload/review. Navigation/refresh/logout warn about unsaved work, and stale responses cannot repopulate an expired owner view.
- Upload cancellation may race with server acceptance: check the library before retrying a canceled or lost-response upload. Uploads do not automatically attach to a product. Temporary object URLs are revoked on completion/destruction.
- Publication and sellability differ. Supplier/cost/stock setup still uses the existing Suppliers and Inventory sections. M5 will add stock/hold explanations alongside variants; this phase does not implement that work.
- Existing storefront cards/hero receive managed primary/hero URLs through compatible public fields. The complete customer gallery/detail integration is M6. Public checkout remains disabled.
- Normal startup: `docker compose --env-file .env.docker.local up --build --wait -d`. Normal shutdown preserves database/media volumes. The `syed123` development account and chosen password hash persist; eight-hour sessions can require signing in again.

## Verification

See `m4_browser_verification.json` for the actual isolated Chrome authoring journey, screenshots and desktop/mobile checks. Fixtures and random SAMPLE credentials are confined to the separate M3 media-check stack. Automated coverage includes exact price parsing, atomic rollback, retained failed-save input, duplicate-submit prevention, stale response disposal, real upload progress/abort handling, protected media validation and attachment races. Final suite/build counts are recorded in `owner_catalog_phase_status.json`.
