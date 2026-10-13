# AlphaZee — Work Progress & Verification Log

Updated: 2026-10-09. Owner: Syed Najam.

Historical milestone log through 2026-10-09. The current verification status and
release decision are in [the repair verification report](../.context/repair_verification_report.md).
The older test counts and launch-blocker language below describe their dated
milestones, not current launch readiness.

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

### Phase 15: Catalog Baseline Migration & Disposable PostgreSQL Verification
- **Catalog Initial Migration Generated & Lifecycle Verified**:
  - Migration script: `backend/alembic/versions/cdfea0b392b4_create_initial_catalog_tables.py`.
  - Target database: isolated disposable test database `alphazee_migration_test` (port 5433).
  - Verified DDL structure:
    - `availability_status` PostgreSQL enum (`'AVAILABLE'`, `'UNAVAILABLE'`, `'UNKNOWN'`).
    - `collections` table with UNIQUE on `slug`.
    - `products` table with FK `collection_id` referencing `collections(id)` `ON DELETE RESTRICT`.
    - `variants` table with FK `product_id` referencing `products(id)` `ON DELETE CASCADE`.
    - `uq_variant_product_size_color` UNIQUE index on `(product_id, size, color)` with `NULLS NOT DISTINCT` (PostgreSQL 16+).
    - `ck_variant_price_nonnegative` CHECK constraint (`price_minor >= 0`).
  - Added clean enum drop in `downgrade()`: `sa.Enum(name='availability_status').drop(op.get_bind(), checkfirst=True)`.
  - Full lifecycle tested on isolated database: `upgrade head` -> `downgrade base` -> `upgrade head` completed with zero errors.
- **PostgreSQL Catalog Integration Test Suite**:
  - Created `backend/tests/test_catalog_integration.py` covering:
    - PostgreSQL 16+ `NULLS NOT DISTINCT` preventing duplicate `(product_id, NULL, NULL)` combinations.
    - Check constraint `ck_variant_price_nonnegative` rejecting negative prices.
    - FK `ON DELETE RESTRICT` preventing collection deletion when referenced by products.
    - FK `ON DELETE CASCADE` deleting all variants when a product is deleted.
    - Global SKU uniqueness across all products.
    - Enum value persistence and reload.

### Phase 16: Supplier & Inventory Foundation Models, Optimistic Locking & Concurrency Verification
- **ORM Models Implemented**:
  - `backend/app/models/suppliers.py`: `UserAccount`, `Supplier`, `SupplierMembership` with validation on `status` (`active`, `inactive`, `suspended`).
  - `backend/app/models/inventory.py`: `SupplierVariant`, `InventoryBalance`, `StockEvent` with validation on `reason` in approved enum set.
  - Re-exported all models in `backend/app/models/__init__.py`.
- **Alembic Foundation Migration**:
  - Generated revision `38e5f1393859_create_supplier_inventory_foundation.py`.
  - Verified DDL structure:
    - `suppliers` table with UUID PK and CHECK on `status`.
    - `user_accounts` table with UUID PK and UNIQUE on `auth_subject`.
    - `supplier_memberships` table with composite PK and cascading FKs.
    - `supplier_variants` table with FKs, `supplier_cost_minor >= 0` check, and partial unique index `uq_sv_one_active_per_variant` on `variant_id` WHERE `active = true`.
    - `inventory_balances` table with `on_hand >= 0` check and `version BIGINT` optimistic lock counter.
    - `stock_events` immutable audit log table with CHECK on `reason`.
  - Executed migration lifecycle: `upgrade head` -> `downgrade -1` -> `upgrade head` on `alphazee_migration_test` with zero errors.
- **Query & Concurrency Layer**:
  - Created `backend/app/queries/inventory.py` with `adjust_inventory()`, `StaleInventoryError`, `get_inventory_balance()`, `get_stock_events()`, `get_active_supplier_variant()`, and `get_active_suppliers()`.
  - Atomic adjustment executes targeted `UPDATE ... WHERE version = :expected_version` and appends `StockEvent` in a single transaction.
- **Integration & Two-Session Concurrency Test Suite**:
  - Created `backend/tests/test_suppliers_unit.py` and `backend/tests/test_inventory_unit.py`.
  - Created `backend/tests/test_inventory_integration.py` containing a genuine two-session concurrency test:
    - Session A and Session B both read balance at version 0, on_hand 10.
    - Session A updates to on_hand 8, expected_version 0 and commits -> version becomes 1.
    - Session B attempts update with stale expected_version 0 -> raises `StaleInventoryError` and rolls back.
### Phase 17: Stock Reservations & Owner Inventory Reporting Engine
- **ORM Model Implemented**:
  - `backend/app/models/inventory.py`: `StockReservation` with `quantity > 0` check, validated `stage` enum set (`held`, `confirmed`, `dispatched`, `fulfilled`, `cancelled`, `returned`), and partial aggregation index `idx_sr_open_stage`.
  - Re-exported `StockReservation` in `backend/app/models/__init__.py`.
- **Alembic Reservation Migration**:
  - Generated revision `138c3538bf20_create_stock_reservations.py`.
  - Verified DDL structure:
    - `stock_reservations` table with UUID PK and CHECK on `quantity > 0` and `stage`.
    - Partial index `idx_sr_open_stage` on `(supplier_variant_id, quantity)` WHERE `stage NOT IN ('fulfilled', 'cancelled', 'returned')`.
    - FK `supplier_variant_id` referencing `supplier_variants(id)` with `ON DELETE RESTRICT`.
  - Executed migration lifecycle: `upgrade head` -> `downgrade -1` -> `upgrade head` on `alphazee_migration_test` with zero errors.
- **Reservation Engine & Reporting Query Layer**:
  - Created `backend/app/queries/reservations.py`:
    - `get_inventory_summary()`: Computes real-time `Physical` (`on_hand`), `Held` (sum of open reservations), and `Available` (`max(0, Physical - Held)`).
    - `create_stock_reservation()`: Atomically guards against over-allocation when `requested > Available` (raising `InsufficientStockError`).
    - `transition_reservation_stage()`: Advances reservation lifecycle, synchronizes physical on-hand stock and audit events upon `fulfilled`, and releases held stock on `cancelled`.
- **Integration & Unit Test Suite**:
  - Created `backend/tests/test_reservation_unit.py` and `backend/tests/test_reservation_integration.py` (10 test cases):
    - Real-time calculation of owner triple `Physical 10 | Held 2 | Available 8`.
    - Insufficient stock prevention when reservation exceeds Available.
    - Cancellation immediately releasing Held stock and restoring Available.
    - Fulfillment atomically decrementing physical stock and appending `StockEvent(reason='reservation_fulfilled')`.
    - Terminal stage locking (preventing reopening closed reservations).
    - Database check constraints on `quantity > 0` and `stage`.

### Phase 18: Orders, Purchase Snapshots, Checkout Processing & Payment Verification
- **ORM Models Implemented**:
  - `backend/app/models/orders.py`: `Order`, `OrderLine`, `PaymentReceipt` with phone normalization (`normalize_pakistan_phone`), validated payment/order statuses, and snapshot columns.
  - Re-exported all order models in `backend/app/models/__init__.py`.
- **Alembic Orders Migration**:
  - Generated revision `addb61a5d782_create_orders_and_payment_tables.py`.
  - Verified DDL structure:
    - `orders` table with UUID PK, check constraints on subtotal, shipping fee, total, payment method/status, order status.
    - `order_lines` table with UUID PK, purchase-time snapshots (title, SKU, size, color, customer price, supplier cost), and `quantity > 0` check.
    - `payment_receipts` table with UUID PK, receipt image URL, and bank reference.
  - Executed migration lifecycle: `upgrade head` -> `downgrade -1` -> `upgrade head` on `alphazee_migration_test` with zero errors.
- **Order Service & Processing Layer**:
  - Created `backend/app/services/orders.py`:
    - `place_order()`: Recalculates authoritative pricing from catalog, resolves active supplier variants, creates purchase snapshots, and locks stock reservations atomically.
    - `upload_payment_receipt()`: Uploads bank transfer screenshots.
    - `verify_bank_payment()`: Confirms received bank funds and advances order/reservation stages to `confirmed`.
    - `cancel_order()`: Cancels order and immediately releases all held stock reservations.
    - `deliver_order()`: Marks order delivered and fulfills reservations (decrementing physical inventory and recording `StockEvent`).
- **Integration & Unit Test Suite**:
### Phase 20: Interactive Owner Administration Dashboard, Supplier Management & Order Tracking UI
- **Admin Schemas & Endpoints**:
  - `backend/app/schemas/admin.py`: Added `AdminOverviewResponse`, `SupplierCreateRequest`, `SupplierVariantAssignRequest`, `SupplierResponseSchema`, `SupplierVariantResponseSchema`.
  - `backend/app/api/v1/admin.py`:
    - `GET /api/v1/admin/overview`: Computes live gross revenue from verified payments, order status breakdown (`placed`, `confirmed`, `delivered`), total active SKUs, and low-stock count (`available <= 2`).
    - `GET /api/v1/admin/suppliers`: Lists registered approved suppliers with active SKU count and settlement currency.
    - `POST /api/v1/admin/suppliers`: Registers new suppliers with unique slug validation.
    - `POST /api/v1/admin/suppliers/{supplier_id}/variants`: Maps a catalog variant to a supplier with `supplier_cost_minor`, deactivates competing active supplier variants within the same transaction to uphold partial unique index `uq_sv_one_active_per_variant`, and ensures an `InventoryBalance` row exists.
  - Re-exported all new schemas in `backend/app/schemas/__init__.py`.
- **Backend Admin API Tests**:
  - `backend/tests/test_api_admin.py`: Added `test_admin_overview_metrics` and `test_admin_supplier_crud_and_variant_cost_assignment`.
  - All 101 backend tests passing (`101 passed, 0 failed`).
- **Frontend Admin Console & Tracking Modal UI**:
  - `frontend/src/utils/api.js`: Added `fetchAdminOverview`, `fetchAdminInventory`, `adjustAdminInventory`, `fetchAdminOrders`, `verifyOrderPayment`, `deliverOrder`, `cancelOrder`, `fetchAdminSuppliers`, `createAdminSupplier`, `assignSupplierVariant`.
  - `frontend/src/components/AdminConsole.js`: Built complete interactive owner administration dashboard with:
    - Live Overview cards (Gross Verified Revenue, Pending Action Orders, Active SKUs, Low Stock warnings).
    - Orders management table with inline payment verification, delivery fulfillment, and cancellation actions.
    - Inventory & Stock table with real-time `Physical | Held | Available` metric chips and optimistic concurrency version-guarded stock adjustment modal.
    - Suppliers management tab with supplier registration form and variant cost assignment modal.
  - `frontend/src/components/OrderTrackingModal.js`: Built customer self-service order tracking with order number and Pakistan mobile phone verification, visual step progress indicator, and inline bank transfer receipt screenshot upload.
  - `frontend/src/components/Header.js` & `frontend/src/main.js`: Added "Track Order" navigation link and mounted `AdminConsoleModal` and `OrderTrackingModal`.
  - `frontend/tests/admin.test.js`: Added unit tests covering admin API client methods.

### Phase 22: Promotional Discounts, Coupon Codes, Marketing Attribution (UTM), Customer Returns & Size Exchanges
- **Promotions & Returns ORM Models & Alembic Migration**:
  - `backend/app/models/promotions.py`: Created `Coupon` model supporting percentage discounts (with optional maximum discount cap), fixed-amount rupee discounts, and free shipping waivers. Enforces nonnegative values, code uniqueness, and validity date constraints.
  - `backend/app/models/returns.py`: Created `OrderReturn` model supporting bank transfer refunds, size exchanges (linked to replacement variant ID), and store credit. Enforces status lifecycle (`requested`, `approved`, `item_received`, `inspected_passed`, `completed`, `rejected`), return reasons, nonnegative refund amount in paisas, and restocking audit timestamps.
  - `backend/app/models/orders.py`: Added `discount_amount_minor`, `coupon_code_snapshot`, `utm_source`, `utm_medium`, `utm_campaign`, non-negative discount check constraint, and `returns` cascade relationship.
  - Generated and verified Alembic revision `8f6817131a9a_create_coupons_and_order_returns_tables.py` on disposable `alphazee_migration_test` (tested full `upgrade` -> `downgrade -1` -> `upgrade` lifecycle).
- **Service Layer**:
  - `backend/app/services/promotions.py`: `validate_coupon()`, `record_coupon_usage()`, `create_coupon()`, `list_coupons()`, `delete_coupon()`. Authoritatively calculates discount amounts in integer paisas, validates usage limits, minimum subtotals, and expiry dates.
  - `backend/app/services/returns.py`: `create_return_request()`, `approve_return_request()`, `complete_return_and_restock()`, `reject_return_request()`, `list_order_returns()`. Completing return atomically adjusts inventory on hand and records `StockEvent(reason='rto_return')`.
  - `backend/app/services/orders.py`: Enhanced `CreateOrderDTO` and `place_order()` to validate promo codes, apply discount amounts to total payable, snapshot coupon codes, and store marketing UTM parameters.
  - `backend/app/services/analytics.py`: Added `get_marketing_attribution_summary()` aggregating orders, gross revenue, and promotional discounts by campaign/source.
- **Storefront & Admin API Routing**:
  - `POST /api/v1/coupons/validate` (storefront coupon validation against live cart subtotal).
  - `POST /api/v1/returns/request` (customer return / exchange request submission).
  - `GET /api/v1/admin/coupons`, `POST /api/v1/admin/coupons`, `DELETE /api/v1/admin/coupons/{id}`.
  - `GET /api/v1/admin/returns`, `POST /api/v1/admin/returns/{id}/approve`, `POST /api/v1/admin/returns/{id}/complete`, `POST /api/v1/admin/returns/{id}/reject`.
  - `GET /api/v1/admin/analytics/marketing` (marketing campaign conversion and discount report).
- **Frontend Integration**:
  - `frontend/src/utils/utm.js`: Utility to automatically capture landing UTM query parameters and cache in session storage.
  - `frontend/src/utils/api.js`: Added `validateCoupon`, `requestOrderReturn`, coupon CRUD, return management, and marketing analytics methods.
  - `frontend/src/components/CheckoutView.js`: Added promo code box with live validation, discount breakdown row, and UTM parameter forwarding in order placement payload.
  - `frontend/src/components/OrderTrackingModal.js`: Added customer return & exchange request submission panel and status display.
  - `frontend/src/components/AdminConsole.js`: Added **Coupons & Promos** management tab, **Returns & Refunds** resolution tab, and **Marketing Attribution (UTM)** performance breakdown in Analytics.
- **Comprehensive Verification**:
  - `backend/tests/test_api_coupons.py`: Percentage, fixed, and free-shipping coupon validation and API endpoint tests.
  - `backend/tests/test_api_returns.py`: Customer return request, admin approval, and inventory restock tests.
  - `backend/tests/test_analytics.py`: Added marketing attribution analytics tests.
  - `frontend/tests/promotions.test.js`: Unit tests for UTM capture, coupon validation, return workflows, and admin methods.
### Phase 23: Admin Authentication Gate (Launch Blocker 1)
- **Defect Reproduction (Red Test Stage)**:
  - Created `backend/tests/test_api_auth.py` asserting `401 Unauthorized` for anonymous admin requests and invalid credentials across all privileged endpoints (`/overview`, `/inventory/summary`, `/inventory/adjust`, `/orders`, `/suppliers`, `/analytics/profit-loss`, `/coupons`, `/returns`).
  - Formally reproduced defect: anonymous requests originally succeeded with `200 OK`.
- **Backend Configuration & Security Hardening**:
  - `backend/app/config.py`: Added `admin_api_key` configuration with strict production safety validation (raises `ValidationError` if empty, default, or under 32 characters when `app_env="production"`).
  - Updated `backend/.env.example` documenting `ADMIN_API_KEY`.
  - `backend/app/dependencies/auth.py`: Implemented `require_admin_key` using constant-time `secrets.compare_digest` to prevent timing attacks. Supports both `X-Admin-Key` custom header and `Authorization: Bearer <token>`.
  - `backend/app/api/v1/admin.py`: Attached `dependencies=[Depends(require_admin_key)]` directly to the `APIRouter` declaration, locking all 16 current and future administrative endpoints.
  - `backend/app/main.py`: Whitelisted `X-Admin-Key` in CORS middleware `allow_headers`.
- **Test Suite Modernization**:
  - `backend/tests/conftest.py`: Added `admin_headers` and `admin_client` fixtures pre-authenticated with the owner admin key.
  - Updated `test_api_admin.py`, `test_api_shipments.py`, `test_analytics.py`, `test_api_returns.py`, `test_api_coupons.py`, and `test_config.py` to use authenticated fixtures while `test_api_auth.py` tests unauthenticated/invalid rejection.
- **Frontend Integration**:
  - `frontend/src/utils/api.js`: Added `getAdminKey`, `setAdminKey`, and `clearAdminKey` with automatic `X-Admin-Key` header injection on `/admin/*` requests.
  - `frontend/src/components/AdminConsole.js`: Added interactive **Owner Authorization Required** unlock prompt on `401 Unauthorized` responses and a lock console button (`🔒 Lock`) in the sidebar footer.
  - `frontend/tests/admin.test.js`: Added unit tests verifying session key management and header injection.

### Phase 24: Reservation Concurrency & Checkout Idempotency (Launch Blocker 2)
- **Defect Reproduction (Red Test Stage)**:
  - Created `backend/tests/test_reservation_concurrency.py`:
    - `test_concurrent_reservations_cannot_oversell`: Simulated two concurrent threads attempting to hold the last remaining unit of an inventory balance. Formally reproduced oversell defect before row locking.
    - `test_reservation_idempotency_returns_existing_record`: Verified that repeated reservation requests with an identical `idempotency_key` return the existing held reservation rather than creating duplicate holds.
    - `test_order_checkout_idempotency_header`: Verified that duplicate `POST /api/v1/orders` requests with the same `Idempotency-Key` return the original order without creating duplicate database orders or duplicate stock holds.
- **ORM Models & Alembic Schema Migration**:
  - `backend/app/models/inventory.py`: Added `idempotency_key` (String 128, nullable) to `StockReservation` and partial unique index `uq_sr_idempotency_open` (`WHERE stage NOT IN ('cancelled', 'returned') AND idempotency_key IS NOT NULL`).
  - `backend/app/models/orders.py`: Added `idempotency_key` (String 128, nullable) to `Order` and partial unique index `uq_orders_idempotency_key` (`WHERE idempotency_key IS NOT NULL`).
  - Generated revision `e5c83f14a091_add_reservation_and_order_idempotency_keys.py`.
  - Executed full migration lifecycle (`upgrade head` -> `downgrade -1` -> `upgrade head`) on disposable test database `alphazee_migration_test` with zero errors.
- **Pessimistic Locking & Idempotent Hold Query Layer**:
  - `backend/app/queries/reservations.py`: In `create_stock_reservation()`:
    - Checked for existing active reservation matching `idempotency_key`.
    - Acquired exclusive row lock: `SELECT ... FROM inventory_balances WHERE supplier_variant_id = :id FOR UPDATE` (`with_for_update()`).
    - Recalculated available stock strictly under the row lock: `available = balance.on_hand - active_held`.
    - Enforced `requested <= available`, raising `InsufficientStockError` if stock is exhausted by a concurrent transaction.
- **Checkout Service & Endpoint Idempotency**:
  - `backend/app/schemas/orders.py`: Added `idempotency_key` to `OrderCreateRequest` and `OrderResponseSchema`.
  - `backend/app/services/orders.py`: Handled idempotent lookups in `place_order()`, returning existing orders on match and passing line-derived keys (`{order_idempotency_key}:{variant.id}`) to `create_stock_reservation()`.
  - `backend/app/api/v1/orders.py`: Accepted `Idempotency-Key` header and mapped to order creation request.
  - `backend/app/main.py`: Added `"Idempotency-Key"` to CORS middleware `allow_headers`.
- **Frontend Integration**:
  - `frontend/src/utils/api.js`: Generated unique client UUID for `Idempotency-Key` header and payload in `submitOrder()`.
  - `frontend/tests/checkout.test.js`: Verified transmission of `Idempotency-Key` header.

### Phase 25: Payment & Supplier Confirmation Separation (Launch Blocker 3)
- **Defect Reproduction (Red Test Stage)**:
  - Created `backend/tests/test_payment_separation.py`:
    - `test_dispatch_unverified_bank_transfer_rejected`: Verified that attempting to dispatch an unpaid bank-transfer order raises `OrderNotDispatchableError` (422) instead of allowing dispatch.
    - `test_verify_payment_does_not_confirm_supplier_or_advance_reservations`: Verified that `verify_bank_payment()` only updates `payment_status = "verified"`, leaving `order_status = "placed"` and stock reservations in `"held"` stage.
    - `test_confirm_supplier_acceptance_advances_order_and_reservations`: Verified that `confirm_supplier_acceptance()` explicitly sets `order_status = "confirmed"`, records `supplier_confirmed_at`, and advances open reservations from `"held"` to `"confirmed"`.
    - `test_four_hour_payment_window_and_expired_order_cancellation`: Verified that bank transfer orders receive a 4-hour `payment_deadline_at`, while COD orders receive `None`. Calling `cancel_expired_bank_orders()` auto-cancels elapsed unverified orders and releases held stock.
- **ORM Models & Alembic Schema Migration**:
  - `backend/app/models/orders.py`: Added `payment_deadline_at`, `supplier_confirmed_at`, and `supplier_notes` to `Order` with `idx_orders_payment_deadline` index.
  - Generated revision `13b1315d1395_add_payment_deadline_and_supplier_.py`.
  - Verified full migration lifecycle (`upgrade head` -> `downgrade -1` -> `upgrade head`) on disposable test database `alphazee_migration_test` with zero errors.
- **Service & Dispatch Safety Layer**:
  - `backend/app/services/orders.py`:
    - Updated `place_order()` to calculate 4-hour deadline for bank transfer orders.
    - Refactored `verify_bank_payment()` to strictly execute financial verification without altering order status or reservations.
    - Created `confirm_supplier_acceptance()` and `cancel_expired_bank_orders()`.
  - `backend/app/services/shipments.py`:
    - Hardened `create_shipment()` to reject unpaid bank transfer orders and require `order.order_status == "confirmed"`.
    - Updated `update_shipment_status()` to fulfill `"confirmed"` reservations upon courier delivery.
- **Honest Bank Configuration & Administrative UI**:
  - `backend/app/config.py` & `.env.example`: Added configurable bank transfer settings with `bank_iban = "PENDING_IBAN_CONFIGURATION"`.
  - `backend/app/schemas/orders.py`: Dynamic `BankInstructionsSchema` defaults and added deadline/supplier fields to `OrderResponseSchema`.
  - `backend/app/api/v1/admin.py`: Added `POST /orders/{order_id}/confirm-supplier` and `POST /orders/cancel-expired`.
  - `frontend/src/data/store-config.js` & `CheckoutView.js`: Added pending IBAN notice and 4-hour payment window alert.
  - `frontend/src/components/AdminConsole.js`: Separated "Verify Bank Transfer", "Confirm Supplier", and "Dispatch Courier" action flows, plus added toolbar button to purge expired bank orders.
  - `frontend/tests/admin.test.js`: Added unit tests for supplier confirmation and expired order cancellation.

### Phase 26 (Phase D: Delivery, Cancellation & Stock Transitions — Launch Blocker 4)

- **Red-Green-Refactor Reproduction**:
  - Created `backend/tests/test_delivery_transitions.py` covering:
    - `test_cancelling_dispatched_order_rejected_with_422`: Verified cancelling a dispatched order raises `OrderNotCancellableError` and returns HTTP 422.
    - `test_deliver_order_transitions_reservations_sequentially`: Verified reservations progress through `held` -> `confirmed` -> `dispatched` -> `fulfilled` sequentially without skipping stages.
    - `test_rto_in_transit_does_not_release_stock`: Verified initiating RTO marks shipment as `rto_initiated` while held stock remains reserved.
    - `test_rto_received_releases_stock_back_to_available`: Verified warehouse physical arrival (`rto_delivered`) cancels reservations and releases held inventory back to available stock.
- **Service & Domain Invariants**:
  - `backend/app/services/orders.py`: Added `OrderNotCancellableError` and enforced sequential reservation progression upon delivery.
  - `backend/app/services/shipments.py`:
    - Updated `create_shipment()` to advance line reservations from `confirmed` to `dispatched`.
    - Updated `update_shipment_status()` to advance reservations sequentially to `fulfilled` on delivery.
    - Added `initiate_rto_order()` and `receive_rto_parcel()` implementing the safe two-step RTO lifecycle.
- **Admin API & Frontend Management**:
  - `backend/app/schemas/admin.py`: Added `OrderRtoInitiateRequest`.
  - `backend/app/api/v1/admin.py`:
    - Guarded `POST /orders/{order_id}/cancel` to catch `OrderNotCancellableError` and return 422.
    - Added `POST /orders/{order_id}/rto` and `POST /orders/{order_id}/rto-received`.
  - `frontend/src/utils/api.js`: Added `initiateOrderRto` and `receiveOrderRto`.
  - `frontend/src/components/AdminConsole.js`: Added contextual RTO actions for dispatched and in-transit orders, hiding direct cancellation for dispatched orders.
  - `frontend/tests/admin.test.js`: Added two-step RTO integration tests.

### Phase 27 (Phase E: Safe RTO Restocking & Return Supplier Fix — Launch Blocker 5)

- **Red-Green-Refactor Reproduction**:
  - Created `backend/tests/test_rto_restock.py` covering:
    - `test_rto_received_does_not_automatically_restock`: Verified physical arrival records presence without touching inventory balance.
    - `test_inspect_and_restock_condition_ok_increases_stock_with_audit`: Verified explicit inspection increases physical on-hand inventory via `adjust_inventory` with `StockEvent` delta.
    - `test_inspect_and_restock_damaged_condition_does_not_restock`: Verified damaged goods are logged without returning to sellable inventory.
    - `test_customer_return_restocks_fulfilling_supplier_not_new_active_supplier`: Verified customer returns restock the fulfilling supplier snapshot from `StockReservation` rather than the current active supplier.
- **Service & Domain Invariants**:
  - `backend/app/services/shipments.py`: Decoupled `rto_delivered` arrival from inventory changes; added `inspect_and_restock_order()` requiring explicit condition inspection; fixed `StockEvent` missing delta bug.
  - `backend/app/services/returns.py`: Updated `complete_return_and_restock()` to resolve the historical fulfilling supplier variant from `StockReservation`.
- **Admin API & Frontend UI**:
  - `backend/app/api/v1/admin.py`: Added `POST /api/v1/admin/orders/{order_id}/rto-inspect`.
  - `frontend/src/utils/api.js`: Added `inspectAndRestockRtoOrder()`.
  - `frontend/src/components/AdminConsole.js`: Added interactive inspection and restocking buttons for uninspected RTO parcels.

### Phase 28 (Phase F: Accurate Financial Reporting & Remittance Guards — Launch Blocker 6)

- **Red-Green-Refactor Reproduction**:
  - Created `backend/tests/test_financial_reporting.py` covering:
    - `test_unpaid_placed_orders_excluded_from_revenue`: Verified unpaid placed orders (`payment_status == 'pending'`) are strictly excluded from gross revenue, COGS, and profit.
    - `test_verified_bank_and_cod_collected_included_in_revenue`: Verified only verified bank transfers and collected/delivered COD orders count toward realized revenue and COGS.
    - `test_completed_returns_deducted_from_revenue`: Verified completed customer returns deduct `refund_amount_minor` from net revenue and gross profit.
    - `test_zero_or_negative_cod_remittance_rejected_with_422`: Verified zero and negative COD remittances are rejected with HTTP 422.
    - `test_partial_cod_remittance_requires_explicit_flag_and_reason`: Verified short courier settlements are rejected with HTTP 422 unless explicit `is_partial=True` and `partial_reason` are provided.
    - `test_mark_cod_remitted_by_order_id_endpoint`: Verified recording remittance by order ID endpoint and model properties `remittance_amount_minor` and `is_partial_remittance`.
- **Financial Calculation & Analytics Layer**:
  - `backend/app/services/analytics.py`:
    - Updated `get_profit_loss_summary()`: Filtered orders strictly by `payment_status.in_(["verified", "verified_received", "cod_collected"])`.
    - Deducted `SUM(OrderReturn.refund_amount_minor)` from completed returns.
    - Realized COGS calculated only on paid/collected lines.
    - Net Gross Profit computed as `net_revenue_minor - cogs_minor - total_courier_expenses_minor`.
- **Logistics & COD Remittance Security**:
  - `backend/app/models/shipments.py`: Added `remittance_amount_minor` and `is_partial_remittance` ORM model properties.
  - `backend/app/services/shipments.py`: Added `InvalidRemittanceError`, enforced remittance amount and partial guards, and added `mark_cod_remitted()` helper.
  - `backend/app/schemas/admin.py`: Added partial remittance fields to `CodRemittanceRequest`, properties to `ShipmentAdminResponseSchema`, and net revenue/refund fields to `ProfitLossResponseSchema`.
  - `backend/app/api/v1/admin.py`: Added `POST /api/v1/admin/orders/{order_id}/remittance`, wired remittance guards with HTTP 422 mapping, and enriched `/analytics/profit-loss` endpoint.

### Phase 29 (Phase G: End-to-End Exchange Completion & Ownership Verification — Launch Blocker 7)

- **Red-Green-Refactor Reproduction**:
  - Created `backend/tests/test_exchange_flow.py` covering:
    - `test_return_request_with_wrong_phone_rejected_with_403`: Verified returns submitted with unverified/mismatched phone are rejected with HTTP 403 Forbidden.
    - `test_return_request_with_valid_phone_accepted`: Verified returns with matching normalized phone are accepted with HTTP 201 Created.
    - `test_approve_exchange_creates_replacement_reservation_and_shipment`: Verified approving size exchanges atomically creates replacement `StockReservation` with `stage == "held"` and new replacement `Shipment` with `status == "booked"`.
    - `test_approve_exchange_with_no_stock_raises_422`: Verified approving size exchange when replacement variant stock is exhausted raises `InsufficientStockError` and returns HTTP 422 Unprocessable Entity.
    - `test_approve_refund_return_does_not_create_replacement_shipment`: Verified standard refund return approvals do not create extra shipments or reservations.
- **Service & Domain Invariants**:
  - `backend/app/services/returns.py`:
    - Added `CustomerOwnershipError`.
    - Enforced phone normalization and ownership verification in `create_return_request()`.
    - In `approve_return_request()`: Resolved active supplier variant for `exchange_variant_id`, created replacement stock reservation under row lock, and created replacement `Shipment` record with status `"booked"` and `cod_remittance_status="not_applicable"`.
- **API & Schemas**:
  - `backend/app/schemas/returns.py`: Enforced required `customer_phone` on `OrderReturnCreateRequest`.
  - `backend/app/api/v1/returns.py`: Mapped `CustomerOwnershipError` to HTTP 403 Forbidden.
  - `backend/app/api/v1/admin.py`: Mapped `InsufficientStockError` in return approval to HTTP 422 Unprocessable Entity.

---

## 2. Checks Executed & Results

1. **Full Backend Test Suite (Python 3.13 / PostgreSQL 16)**:
   - Command: `pytest -v` (in `backend/`)
   - **Result**: `144 passed, 0 failed` in 23.89s.
   - Includes: All 7 launch blocker test suites (Phase A auth gate, Phase B reservation concurrency & idempotency, Phase C payment/supplier separation, Phase D delivery transitions & 2-step RTO, Phase E safe RTO restocking, Phase F financial reporting & remittance guards, Phase G exchange completion & phone ownership verification), plus all catalog integration, inventory balances, order lifecycle, courier logistics, unit economics, readiness probes, and marketing UTM attribution tests.
2. **Frontend Test Suite (Node.js 25 built-in runner)**:
   - Command: `npm test` (in `frontend/`)
   - **Result**: `67 passed, 0 failed` across 14 suites in 1.38s.
3. **Frontend Production Build**:
   - Command: `npm run build` (in `frontend/`)
   - **Result**: `✓ built in 1.17s`, 22 modules transformed, zero errors.

---

## 3. Current Scope & Safety Confirmation

- **Historical scope**: These 2026-10-09 checks preceded the later G/F/L2 implementation and Phase V verification; they did not include browser journeys or prove launch readiness.
- **Current development database**: Migrations through `c94e31f7d562` have since been applied to development. Phase V's rollback/re-upgrade ran only on a disposable `_test` database.
- **Checkout**: Public order submission remains disabled by the server-side gate. The current decision and remaining checks are recorded below.

## 4. Current verification — 2026-10-13

Phase V terminal checks passed: 209 backend tests (database-backed tests use
isolated PostgreSQL), 83 frontend
Node tests, frontend production build, real separate-session courier settlement
contention, and disposable G/F migration upgrade/downgrade/re-upgrade with a
historical short-payout fixture. The local Docker development stack is healthy;
terminal HTTP checks confirmed both web-proxied and direct checkout capability
are disabled, anonymous owner routes return 401, and public order creation
returns 503. See the linked report and JSON evidence for commands and limits.

No browser was used at the owner's request. Desktop/mobile behavior, Console and
Network traces, visual interaction, reload persistence, and complete browser
journeys remain unverified. Real production domain, credentials, bank details,
support contacts and recovery-channel configuration are still required. The
application is not certified for public checkout or production launch.










