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

---

## 2. Checks Executed & Results

1. **Backend Unit Suite (Python 3.13)**:
   - Command: `pytest tests/test_config.py tests/test_readiness.py tests/test_catalog_unit.py -v`
   - **Result**: `15 passed, 0 failed` in 0.17s.
   - Covers: CORS origins parser, whitespace trimming, environment helpers, health/readiness failure degradation, query compilation (`JOIN collections`, active filters, deterministic pagination, and hero ordering), and model constraint inspection (`NULLS NOT DISTINCT`, aligned cascades, option normalization, and price helpers).
2. **Backend Standalone Health Probe**:
   - Command: `pytest tests/test_health.py -k test_health -v`
   - **Result**: `2 passed, 1 deselected` in 0.08s (requires no database connection).
3. **Frontend Unit Suite (Node.js 25 built-in runner)**:
   - Command: `npm test` (executes `node --test tests/*.test.js`)
   - **Result**: `12 passed, 0 failed` in 308ms.
   - Covers: `formatPkr` integer formatting, edge cases, `pkrToMinor`, `CartStore` `alphazee_cart_v2` storage, `variant_id` validation, malformed item rejection, quantity clamping (1–99), and item removal.
4. **Frontend Production Build**:
   - Command: `npm run build` in `frontend/`
   - **Result**: `✓ built in 606ms`, 20 modules transformed, zero syntax or bundling errors.
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
