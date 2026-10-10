# AlphaZee — Work Progress & Verification Log

Updated: 2026-10-09. Owner: Syed Najam.

---

## 1. Completed Work

### Phase 1: Catalog Foundation Repair (§3, §4, §5)
- **Catalog Queries Fixed**:
  - Replaced invalid `.where()` chained on `selectinload` with supported `selectinload(Product.variants.and_(Variant.is_active.is_(True)))`.
  - Added `Collection` join with `Collection.is_active.is_(True)` to exclude products with inactive parent collections across listings, details, and hero carousel.
  - Aligned count and data queries in `get_active_products` using `base_stmt.subquery()`.
  - Added deterministic secondary sort by `Product.id.asc()` to pagination and hero ordering.
- **Model Consistency Fixed**:
  - Replaced `UniqueConstraint` with PostgreSQL 16 `Index("uq_variant_product_size_color", "product_id", "size", "color", unique=True, postgresql_nulls_not_distinct=True)` to handle `NULL` options.
  - Aligned `Collection.products` ORM cascade (`cascade="save-update, merge", passive_deletes=True`) with database `ON DELETE RESTRICT` foreign key.
  - Added `Variant.normalize_option()` helper to strip whitespace and coerce empty strings to `None`.
  - Documented whole PKR integer division truncation limitation on `Variant.price_pkr`.
- **Config & Alembic Setup**:
  - Refactored `alembic/env.py` to instantiate `create_engine` directly from `settings.database_url`, avoiding ConfigParser `%`-interpolation errors.
  - Added `backend/alembic/versions/.gitkeep` for clean checkouts.
  - Documented Python 3.13 requirement and rationale in `backend/README.md`.
  - Added `backend/pytest.ini` (`pythonpath = .`).

### Phase 2: Test Isolation, Seed Review & Frontend Integration (§6, §7, §8)
- **Test Safety & Isolation**:
  - Updated `backend/tests/conftest.py` with URL validation via `sqlalchemy.engine.make_url()`. Refuses execution if targeting development or lacking `_test` suffix.
  - Added savepoint isolation (`session.begin_nested()`) and `try ... finally` cleanup for dependency overrides.
  - Added `backend/tests/test_readiness.py` covering healthy (200) and degraded (503) states without credential leakage.
- **Development Seed Script**:
  - Restricted `seed.py` execution strictly to `settings.app_env in {"development", "test"}`.
  - Enhanced `upsert_variant()` to check existing records by `(product_id, size, color)` matching NULLs, preventing duplicate constraint violations on changed SKUs.
  - Added console notice marking seeded products and availability as local demo data.
- **Frontend Catalog Integration**:
  - Configured Vite proxy for `/api` in `frontend/vite.config.js`.
  - Built central API client `frontend/src/utils/api.js`.
  - Created `frontend/src/utils/money.js` with `formatPkr(paisas)`.
  - Created `frontend/src/utils/dom.js` with `escapeHtml()` and `sanitizeMediaUrl()`.
  - Integrated `FeaturedProducts.js`, `Hero.js`, `Collections.js`, and `ProductModal.js` with live API endpoints, loading skeletons, and interactive error/retry states without silent mock fallbacks.

### Phase 3: Cart Behavior, Checkout Safety & Documentation (§9, §10, §11, §12)
- **Cart Behavior**:
  - Upgraded storage key to `alphazee_cart_v2`.
  - Keyed cart items strictly by integer `variant_id`.
  - Added defensive parsing and validation of stored objects; malformed items are discarded and storage errors never crash storefront initialization.
  - Added `cart.reconcileWithApi()` to check live variant availability on cart drawer open without spamming the API on quantity clicks.
- **Checkout Preview Safety**:
  - Removed fake order placement alert and cart clearing.
  - Clearly labeled checkout as a prototype preview; disabled submission; preserved cart items.
  - Removed unsupported 256-bit card/gateway encryption badges; updated copy to reflect planned COD and verified bank transfer.
  - Labeled admin preview with "Concept Demo" badge.
- **Documentation Suite**:
  - Created root `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/progress.md`, and `docs/database-design-pending.md`.

### Phase 4: Refinements & Edge Case Hardening
- **Cart API Reconciliation**:
  - Supported `liveVariant.price.minor` object structure returned by public API schemas in addition to legacy `price_minor`.
  - Removed requirement for `liveVariant.is_active` (which public catalog endpoint omits); defaults to available when `availability === 'available'` and `is_active !== false`.
  - Caught 404 responses from `fetchProductBySlug(slug)` and automatically marked matching cart items as `is_available = false`.
- **Strict Variant ID Validation**:
  - Enforced that `variant_id` must be a positive integer or clean numeric string; strictly rejects `{}` objects, arrays, booleans, zero, negative numbers, and non-numeric strings.
- **Fractional Rupee Formatting**:
  - Updated `formatPkr()` to check `minorUnits % 100 !== 0` and format with two decimal places (e.g. `PKR 3,450.50`) instead of truncating decimals with `Math.floor`.
- **Backend Test Savepoint Isolation**:
  - Implemented true nested savepoint isolation via `connection.begin_nested()` and SQLAlchemy `after_transaction_end` event listener in `backend/tests/conftest.py`.
- **Automatic Option Normalization**:
  - Added SQLAlchemy `@validates("size", "color")` to `Variant` model to automatically trim whitespace and coerce empty strings to `None` on initialization and attribute assignment.

### Phase 5: Backend Money Precision, Safe-Integer Validation & Offline State
- **Backend Money Formatting & Model Comment**:
  - Updated `CurrencyAmount.from_minor()` in `backend/app/schemas/catalog.py` to format with two decimals when fractional paisas exist (`f"PKR {minor / 100:,.2f}"`), while whole rupees format without decimals (`f"PKR {pkr:,}"`).
  - Corrected contradictory model comment in `backend/app/models/catalog.py` to state that 1 PKR = 100 paisas, PKR 3,450 = 345000 paisas.
- **Network / Offline Cart Availability**:
  - Updated `cart.reconcileWithApi()` so network errors/offline states preserve cart items but mark availability as `is_available: false` and `availability: 'unverified'`.
  - Updated `CartDrawer.js` to render an `"Availability Unverified (Offline)"` amber badge and disable checkout button when cart contains unverified items.
- **Complete Cart Validation**:
  - Enforced `Number.isSafeInteger(id) && id > 0` on `variant_id` for both numeric and string-parsed inputs, rejecting floats and values exceeding `Number.MAX_SAFE_INTEGER`.
  - Guarded `updateQuantity` and `addItem` to reject fractional quantities (e.g. `1.5`) and fractional deltas.
  - Guarded nested `price.minor` to strictly require non-negative safe integers; guarded `getState()` total computation to prevent negative cart totals.

### Phase 6: Storefront Contract Alignment & Price Safety (Issue 1)
- **Central Price Contract Helpers**:
  - Added `extractPriceMinor()` and `formatDisplayPrice()` to `frontend/src/utils/money.js` supporting both API `CurrencyAmount` objects (`{ minor, pkr, formatted, currency }`), legacy minor fields, and plain numbers.
  - Returns `"Price unavailable"` fallback when prices are missing or invalid, avoiding silent zero substitution.
- **Storefront Component Contract Consistency**:
  - `FeaturedProducts.js`: Product cards read `product.min_price` via `formatDisplayPrice()`.
  - `ProductModal.js`: Detail popup reads `activeVariant.price.minor`, displays `"Price unavailable"` if missing/invalid, disables the add-to-cart button, and passes the valid `activePriceMinor` to the cart.
  - `Hero.js`: Slide price tags read `item.min_price` via `formatDisplayPrice()`.
- **Cart Price Rejection**:
  - `cart.js` `validateCartItem()` rejects adding items with missing or invalid prices instead of coercing to zero.
  - `reconcileWithApi()` marks items unavailable if the live variant price is missing or invalid.

### Phase 7: Collection Display & Filters Contract Alignment (Issue 2)
- **API Response Contract Handling**:
  - Documented `{ collections: Array, total: number }` return contract on `fetchCollections()` in `frontend/src/utils/api.js`.
  - Updated `Collections.js` to unpack `res.collections || res`:
    - Renders collection cards with links and click triggers when populated.
    - Renders `"No Collections Configured"` empty state box when collections list is empty.
    - Renders `"Collections Unavailable"` error box with interactive `btn-retry` button on network/server errors.
    - Exposed `section.reload` callback.
  - Updated `FeaturedProducts.js` `loadCollections()` to unpack `res.collections || res`, populating collection filter tabs alongside `"All Products"`.
- **Component Test Coverage**:
  - Added `frontend/tests/collections.test.js` covering populated, empty, and failed collection responses and FeaturedProducts filter tab rendering.

### Phase 8: Variant Option Selection & Integrity (Issue 3)
- **Strict Variant Resolution**:
  - Removed silent fallback `|| variants[0]`. Require exact variant match for selected size and color: `activeVariant = variants.find(...) || (sizes.length === 0 && colors.length === 0 ? variants[0] : null)`.
  - Initial selection defaults to `variants[0]` attributes (`size`, `color`) if available, avoiding impossible initial states.
  - When non-matching combinations are chosen: `activeVariant = null`, status badge displays `"Combination Unavailable"`, and Add to Cart button is disabled with text `"Unavailable Combination"`.
  - Option pills for combinations that do not exist under current selections receive styling `.is-unavailable` and line-through visual feedback.
  - Cart addition passes the authoritative matching variant attributes: `variant_id: activeVariant.id`, `sku: activeVariant.sku`, `size: activeVariant.size`, `color: activeVariant.color`.
- **Modal Fetch Safety**:
  - `ProductModal.open()` checks if variants are already present before making redundant network requests via slug, protecting tests and pre-loaded models from unneeded fetch errors.
- **Automated Regression Suite**:
  - Added `frontend/tests/options.test.js` validating sparse variant combinations, impossible combination rejection, disabled button state, out-of-stock and missing/invalid price handling, and exact variant attribute copying into cart.

### Phase 9: Hero Presentation Media & Contract Alignment (Issue 4)
- **Backend Schema & Route Alignment**:
  - Created `HeroProductSchema` in `backend/app/schemas/catalog.py` containing presentation media (`hero_image_url`, `hero_poster_url`, `hero_video_url`), benefit statement (`hero_benefit`), ordering (`hero_order`), and structured minimum variant price (`min_price: Optional[CurrencyAmount]`).
  - Added `_build_hero_product(product)` helper in `backend/app/api/v1/catalog.py` and updated `/products/hero` route `response_model` to `list[HeroProductSchema]`.
  - Added backend unit test in `backend/tests/test_catalog_unit.py` verifying schema serialization, media preservation, and structured price formatting.
- **Frontend Video Streaming On-Demand**:
  - Stored video streaming URL on `video.dataset.videoSrc`. Slide 0 video loads and plays immediately; slide 1+ videos defer loading `.src` until navigated to.
  - In `goToSlide(targetIndex)`: when a slide activates, if its video `.src` is unpopulated, it is loaded from `dataset.videoSrc` and played; inactive slides automatically have their video paused, saving CPU and bandwidth.
  - Slide price tags read `item.min_price` via `formatDisplayPrice()`, displaying `"From PKR ..."` or `"Price unavailable"`.
  - Added `section.destroy()` method and timer `.unref()` to cleanly tear down the auto-advance interval without keeping the process alive.
- **Automated Component Suite**:
  - Added `frontend/tests/hero.test.js` testing on-demand video loading, background video pausing, benefit copy rendering, structured price display, and graceful empty-state brand fallback.

### Phase 10: Media URL Security & Injection Prevention (Issue 5)
- **Hardened URL Validation**:
  - Updated `isValidMediaUrl()` in `frontend/src/utils/dom.js` to reject strings containing double quotes, single quotes, backticks, angle brackets (`<`, `>`), newlines (`\r`, `\n`, `\t`), or backslashes before processing.
  - Ensures protocol is strictly `http:`, `https:`, or root-relative (`/` not `//`).
  - Updated `sanitizeMediaUrl(url, fallback)` to safely substitute clean fallbacks whenever an invalid or injection string is provided.
- **Safe DOM Image Construction**:
  - Created `createSafeImageElement({ src, alt, className, width, height, loading, fallback })` helper in `frontend/src/utils/dom.js`. Sets `.src` and `.alt` via native DOM properties instead of string interpolation.
  - Updated `FeaturedProducts.js`, `ProductModal.js`, `Collections.js`, and `CartDrawer.js` to construct and insert image elements safely via DOM properties.
- **Automated Security Regression Suite**:
  - Added `frontend/tests/dom.test.js` validating protocol constraints, quote breakouts (`" onerror="alert(1)`), tag breakouts (`><script>`), backticks, newlines, and DOM property assignment.

### Phase 11: Cart Verification & Checkout Guarding (Issue 6)
- **Unverified Slug Handling**:
  - Updated `reconcileWithApi()` in `frontend/src/utils/cart.js` to identify cart items missing a slug (`!item.slug`) and immediately mark them as `is_available: false` and `availability: 'unverified'`.
  - Ensures items without catalog slugs never remain marked available or bypass verification.
- **Price Validity & Unavailable State**:
  - Updated `getState()` in `frontend/src/utils/cart.js` so that `hasUnavailable` is immediately `true` if any cart item has an invalid price (`extractPriceMinor(item.price_minor) === null`) or `!item.is_available`.
  - Enforced that live variants with missing or negative prices are strictly marked `is_available: false` and `availability: 'unavailable'`.
- **Active Reconciliation Checkout Guarding**:
  - Exposed `isReconciling: Boolean(this.isReconciling)` in `cart.getState()`.
  - Updated `CartDrawer.js` to disable checkout navigation while `state.isReconciling` is `true`, displaying `"Verifying Cart..."` and an informational status message.
  - Prevents checkout button activation until live catalog prices and availability are confirmed.
- **Automated Regression Suite**:
  - Added tests in `frontend/tests/cart.test.js` covering items missing slugs, invalid price deactivation, and `isReconciling` checkout guarding.

### Phase 12: Catalog Navigation, Pagination & Request Sequencing (Issue 7)
- **Pagination & "Load More" UI**:
  - `frontend/src/utils/api.js`: Added optional `signal` to `fetchProducts`, `fetchProductBySlug`, and `fetchHeroProducts`.
  - `frontend/src/components/FeaturedProducts.js`: Added catalog pagination state (`currentPage = 1`, `pageSize = 12`, `totalProducts = 0`, `isLoadingMore = false`).
  - Added bottom "Load More Products (X of Y)" button when `products.length < totalProducts`. Clicking fetches the next page and appends new products avoiding ID duplication.
  - Renders `"Showing all X pieces"` notice when all catalog products are loaded.
- **Out-of-Order Request Sequencing Protection**:
  - `FeaturedProducts.js`: Implemented integer request sequencing via `activeRequestId`. Filter tab switching and pagination increment `activeRequestId`; slower previous requests that resolve later are safely discarded, preventing race conditions from overwriting newer selections.
  - `ProductModal.js`: Implemented `activeModalRequestId` sequencing. If a user rapidly clicks different product cards, slower older detail fetches are discarded and never overwrite the active modal.
- **Automated Regression Suite**:
  - Added `frontend/tests/pagination.test.js` verifying "Load More" pagination appending, showing all pieces caption, rapid filter switching discarding stale responses, and modal rapid clicking discarding out-of-order slug responses.

### Phase 13: Demo Content Cleanup & Honest Prototype Presentation (Issue 8)
- **Prototype Storefront Announcement Banner**:
  - `frontend/src/components/Header.js`: Added top announcement strip honestly labeling the storefront as an MVP concept prototype with orders and payments disabled.
  - Styled with dedicated CSS in `frontend/src/styles/header.css`.
- **Neutral Local Image Placeholder**:
  - `frontend/src/utils/dom.js`: Replaced external third-party Unsplash photo fallbacks with `PLACEHOLDER_IMAGE_URL` (a clean inline dark SVG data URI with minimal AZ monogram and "IMAGE COMING SOON").
  - Updated `FeaturedProducts.js`, `ProductModal.js`, `Collections.js`, and `CartDrawer.js` to rely on this local neutral fallback rather than pointing to external fashion photography.
- **Business Claims & Copy Alignment**:
  - Removed unverified default `"In Stock"` badge and hardcoded `"Ready to ship"` status from `FeaturedProducts.js` and `ProductModal.js`.
  - Removed invented fabric marketing descriptions from fallback fields in `ProductModal.js`.
  - Updated `ProductModal.js` delivery line to state `"Delivery: Estimated 3–5 business days nationwide (COD & manual bank transfer)"`.
  - Cleaned up `frontend/src/data/store-config.js`: removed unsupported 256-bit encryption claims, card payment gateway claims, unconfirmed 7-day exchange promises, and broken `wa.me/yourwhatsapp` placeholder links. Updated to reflect confirmed manual COD and verified bank transfer invariants.

### Phase 14: Database Test Target Normalization & Credential-Independent Guarding (Issue 9)
- **Credential-Independent Database Target Comparison**:
  - `backend/tests/conftest.py`: Updated `validate_test_database_url(url_str, app_url_str)` to parse URLs using SQLAlchemy `make_url()`.
  - Normalizes `(canonical_host, port, db_name)` independently of username and password credentials.
  - Canonicalizes `localhost` and `127.0.0.1` as equivalent.
  - Rejects execution if test target matches application target even if different credentials are supplied, or if the database name matches the application database name or is a non-test database (`alphazee_dev`, `alphazee`, `postgres`, or non-`_test` suffix).
- **Automated Configuration Test Suite**:
  - Updated `backend/tests/test_config.py` with unit tests verifying allowed disposable test URLs, rejection of non-test databases, rejection of credential-independent matches targeting the same database, and localhost / 127.0.0.1 canonicalization.

---

## 2. Checks Executed & Results

1. **Backend Unit & Configuration Suite (Python 3.13)**:
   - Command: `pytest tests/test_catalog_unit.py tests/test_config.py -v`
   - **Result**: `18 passed, 0 failed` in 0.15s.
   - Covers: `validate_test_database_url` target normalization, CORS origins parser, environment helpers, `HeroProductSchema` and `_build_hero_product`, `CurrencyAmount.from_minor` fractional formatting, query compilation (`JOIN collections`, active filters, deterministic pagination, and hero ordering), model constraint inspection (`NULLS NOT DISTINCT`, aligned cascades, automated option normalization with `@validates`, and price helpers).
2. **Backend Standalone Health Probe**:
   - Command: `pytest tests/test_health.py -k test_health -v`
   - **Result**: `2 passed, 1 deselected` in 0.08s (requires no database connection).
3. **Frontend Unit & Component Suite (Node.js 25 built-in runner)**:
   - Command: `npm test` (executes `node --test tests/*.test.js`)
   - **Result**: `49 passed, 0 failed` across 11 suites in 1.2s.
   - Covers:
     - `pagination.test.js`: "Load More" pagination appending, "Showing all pieces" notice, request sequencing discarding out-of-order filter responses, modal sequencing discarding out-of-order detail responses, Header prototype banner presence, and storeConfig claim cleanup.
     - `dom.test.js`: URL protocol checking, quote breakout prevention, tag breakout prevention, newlines, and DOM property image creation.
     - `options.test.js`: sparse variant combinations, impossible combination rejection, out-of-stock variant deactivation, invalid price deactivation, and exact attribute copying.
     - `hero.test.js`: on-demand video loading, inactive video pausing, benefit text rendering, structured price display, and fallback rendering.
     - `collections.test.js`: populated, empty, and failed collections contract unpacking and FeaturedProducts filter tabs.
     - `cart.test.js`: `CartStore` `alphazee_cart_v2` storage, items missing slugs marked unverified, active reconciliation guarding (`isReconciling`), safe-integer `variant_id` validation, fractional quantity/delta rejection, negative/missing price rejection, live invalid price deactivation, offline unverified availability preservation, 404 deactivation, item removal, and quantity clamping.
     - `money.test.js`: `formatPkr`, `extractPriceMinor`, `formatDisplayPrice`, `pkrToMinor`.
4. **Frontend Production Build**:
   - Command: `npm run build` in `frontend/`
   - **Result**: `✓ built in 549ms`, 20 modules transformed, zero errors.
5. **Import & Syntax Verification**:
   - Python 3.13 clean import of schemas, queries, models, and config.

---

## 3. Checks Deferred Due to Database Pause

- Full database-backed integration tests in `backend/tests/test_catalog.py` (which invoke `conftest.py`'s `create_all()`).
- Database seed script execution (`seed.py`).
- Alembic migration generation (`alembic revision --autogenerate`).
- Alembic migration execution (`alembic upgrade head`).

---

## 4. Safety Confirmation

**No migrations were generated or applied. No database schemas were altered. No databases were dropped or reset. No seed commands were run.**

