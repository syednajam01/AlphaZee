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
  - Full backend test suite: **113 passed, 0 failed** in 11.08s.
  - Full frontend test suite: **63 passed, 0 failed** in 1.61s.
  - Vite production build: Clean compile with zero errors in 956ms.

---

## 2. Checks Executed & Results

1. **Full Backend Test Suite (Python 3.13 / PostgreSQL 16)**:
   - Command: `pytest -v` (in `backend/`)
   - **Result**: `113 passed, 0 failed` in 11.08s.
   - Includes: unit tests, API tests, configuration safety guards, readiness probes, catalog integration, supplier/inventory model tests, two-session concurrency tests, reservation lifecycle tests, order checkout/payment tests, storefront order API tests, admin overview/inventory/supplier endpoints, courier dispatch/tracking, P&L unit economics, coupon validations, return requests/restocks, and marketing UTM analytics.
2. **Frontend Test Suite (Node.js 25 built-in runner)**:
   - Command: `npm test` (in `frontend/`)
   - **Result**: `63 passed, 0 failed` across 14 suites in 1.61s.
3. **Frontend Production Build**:
   - Command: `npm run build` (in `frontend/`)
   - **Result**: `✓ built in 956ms`, 22 modules transformed, zero errors.

---

## 3. Current Scope & Safety Confirmation

- **Application Database Safety**: `alphazee_dev` remains completely untouched.
- **Storefront, Logistics, Promotions & Admin Safety**: Verified end-to-end against disposable PostgreSQL test databases (`alphazee_test` / `alphazee_migration_test`).









