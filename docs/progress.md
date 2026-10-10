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

---

## 2. Checks Executed & Results

1. **Backend Unit Suite (Python 3.13)**:
   - Command: `pytest tests/test_catalog_unit.py tests/test_config.py -v`
   - **Result**: `13 passed, 0 failed` in 0.17s.
   - Covers: `CurrencyAmount.from_minor` fractional formatting, CORS origins parser, whitespace trimming, environment helpers, query compilation (`JOIN collections`, active filters, deterministic pagination, and hero ordering), model constraint inspection (`NULLS NOT DISTINCT`, aligned cascades, automated option normalization with `@validates`, and price helpers).
2. **Backend Standalone Health Probe**:
   - Command: `pytest tests/test_health.py -k test_health -v`
   - **Result**: `2 passed, 1 deselected` in 0.08s (requires no database connection).
3. **Frontend Unit Suite (Node.js 25 built-in runner)**:
   - Command: `npm test` (executes `node --test tests/*.test.js`)
   - **Result**: `19 passed, 0 failed` in 393ms.
   - Covers: `formatPkr` integer/fractional precision, `pkrToMinor`, `CartStore` `alphazee_cart_v2` storage, safe-integer `variant_id` validation, fractional quantity/delta rejection, negative nested price rejection, offline unverified availability preservation, 404 deactivation, item removal, and quantity clamping.
4. **Frontend Production Build**:
   - Command: `npm run build` in `frontend/`
   - **Result**: `✓ built in 1.67s`, 20 modules transformed, zero errors.
5. **Import & Syntax Verification**:
   - `python -c "import app.queries.catalog, app.models.catalog, seed; print('OK')"`
   - **Result**: Clean execution, all modules import without errors.

---

## 3. Checks Deferred Due to Database Pause

- Full database-backed integration tests in `backend/tests/test_catalog.py` (which invoke `conftest.py`'s `create_all()`).
- Database seed script execution (`seed.py`).
- Alembic migration generation (`alembic revision --autogenerate`).
- Alembic migration execution (`alembic upgrade head`).

---

## 4. Safety Confirmation

**No migrations were generated or applied. No database schemas were altered. No databases were dropped or reset. No seed commands were run.**
