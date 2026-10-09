# AlphaZee — System Architecture & Contracts

Owner: Syed Najam. Milestone: Catalog Foundation & Frontend Integration.

---

## 1. System Overview

```
                      +-----------------------------+
                      |   Browser / Customer Device  |
                      +--------------+--------------+
                                     |
               HTTP (Port 3000)      | Same-Origin /api
                                     v
                      +-----------------------------+
                      |    Frontend (Vite Server)   |
                      |   Vanilla JS + Vanilla CSS  |
                      +--------------+--------------+
                                     |
                Vite Proxy           | /api/v1/* -> :8000
                                     v
                      +-----------------------------+
                      |    Backend (FastAPI / Uvicorn) |
                      |    Python 3.13, Sync SQLA 2.0|
                      +--------------+--------------+
                                     |
                TCP 5433             | Connection Pool (Pre-ping)
                                     v
                      +-----------------------------+
                      |  PostgreSQL 16 (Docker DB)  |
                      |   alphazee_dev / test       |
                      +-----------------------------+
```

---

## 2. API Contracts (`/api/v1`)

All endpoints return JSON responses. Errors follow standard FastAPI `{"detail": "..."}` format.

### 2.1 Catalog Endpoints
| Endpoint | Method | Query Parameters | Response Model | Description |
|---|---|---|---|---|
| `/collections` | `GET` | — | `list[CollectionSchema]` | Active collections ordered by `display_order ASC`, `name ASC`. |
| `/products` | `GET` | `collection_id: str?`<br>`page: int = 1`<br>`page_size: int = 20` | `ProductListResponse` | Paginated active products whose parent collections are active. Ordered by `created_at DESC`, `id ASC`. |
| `/products/hero` | `GET` | — | `list[ProductSummarySchema]` | Active hero products with active collections. Ordered by `hero_order ASC NULLS LAST`, `id ASC`. |
| `/products/{slug}` | `GET` | — | `ProductDetailSchema` | Full product detail with active variants. Returns 404 if product or collection is inactive. |

### 2.2 Health & Diagnostic Endpoints
| Endpoint | Method | Status Codes | Description |
|---|---|---|---|
| `/health` | `GET` | `200` | Process liveness probe. Never contacts database. Never leaks secrets. |
| `/ready` | `GET` | `200`, `503` | Readiness probe. Executes `SELECT 1`. Returns 503 if unreachable without surfacing internal exceptions or credentials. |

---

## 3. Data Representation & Invariants

### 3.1 Currency & Money Representation
- **Authoritative Unit**: Integer minor units (paisas).
- **Rule**: PKR 3,450 is stored as `345000` paisas. No fractional rupees are truncated in storage.
- **Display Helper**: `formatPkr(minorUnits)` divides integer paisas by 100 and formats as `"PKR 3,450"`. Float arithmetic is strictly prohibited for money math.

### 3.2 Variant Uniqueness (PostgreSQL 16 `NULLS NOT DISTINCT`)
- Catalog uniqueness is enforced on `(product_id, size, color)`.
- Using `postgresql_nulls_not_distinct=True`, variants with `NULL` sizes or colors (e.g., products with no size option, or products with only size) are prevented from duplication at the database level.
- Whitespace is stripped and empty strings are coerced to `None` prior to insertion via `Variant.normalize_option()`.

### 3.3 Foreign Key & Cascade Alignment
- `Collection` $\rightarrow$ `Product`: Foreign key specifies `ON DELETE RESTRICT`. ORM relationship uses `cascade="save-update, merge", passive_deletes=True` so deleting a collection cannot delete its products. Catalog removal uses `is_active=False`.
- `Product` $\rightarrow$ `Variant`: Foreign key specifies `ON DELETE CASCADE`. Variants do not exist independently of their owning product.
- **Purchase Immutability**: Historical orders must snapshot variant titles, SKUs, option selections, and agreed prices. Foreign keys on catalog variants are not relied upon for order history preservation.

---

## 4. Frontend Client Architecture

### 4.1 Storage & Cart Store (`alphazee_cart_v2`)
- **Keying**: Items are keyed strictly by integer `variant_id`.
- **Validation**: Raw localStorage data is inspected and validated before use. Malformed objects, corrupt JSON, or missing `variant_id` are discarded without throwing errors.
- **Reconciliation**: When the cart drawer opens, `cart.reconcileWithApi()` queries the live API in the background. Items whose availability changed to `unavailable` or `unknown` are flagged with a warning banner, and checkout is disabled.
- **Network Conservation**: Quantity increments and decrements do not trigger redundant network requests; totals are recomputed locally in paisas.

### 4.2 Security & Credential Isolation
- Database credentials and secrets are kept server-side only.
- In development, the Vite proxy forwards `/api` requests to `http://localhost:8000`, matching production same-origin deployment expectations.
- All dynamic text values rendered in the DOM are escaped via `escapeHtml()`, and media URLs are validated before insertion into `src` attributes.
