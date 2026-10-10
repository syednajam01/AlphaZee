# AlphaZee — Schema Proposal (Third Revision)

> **Status**: PROPOSED — not approved, not implemented, no migrations exist.
> **Sources**: `.context/mermaid.md`, `docs/decisions.md`, `docs/database-design-pending.md`,
> `docs/architecture.md`, `.agent/AGENTS.md`, `backend/app/models/catalog.py`,
> `backend/alembic/env.py`, this conversation.
> **Revised**: 2026-10-11. Migrations paused. Privileged routes paused.

> [!IMPORTANT]
> **Authority order**: The latest approved business rules stated in this conversation are
> authoritative over older repository documents where they conflict. The rules in Part 1 below
> supersede any conflicting text in `docs/database-design-pending.md` or `.context/next_target.txt`.

---

## Corrections Applied in This Revision

Seven findings from the review that invalidated the previous draft:

| # | Finding | Correction |
|---|---|---|
| F1 | Catalog baseline used `alembic stamp` against an assumed-good database | Real initial revision that creates all catalog tables on an empty disposable DB. Stamping allowed only after verifying the live DB matches that specific revision. |
| F2 | `adjust_inventory` did a read-then-check for version, allowing a TOCTOU race | Replaced with a targeted `UPDATE … WHERE version = :expected` that returns row count; if 0 rows updated, raises `StaleDataError` without a separate read. |
| F3 | Concurrency test only said "raises conflict" — not a real two-session test | Added a genuine two-connection concurrency test specification with required assertions. |
| F4 | Owner inventory display was missing | Added `Physical N \| Held N \| Available N` display spec with order references. Marked as dependent on the reservation module. |
| F5 | "Catalog is working and fully tested" — not supported by actual verification | Corrected to accurately reflect what has and has not been verified. |
| F6 | Latest approved rules not clearly marked as authoritative over old docs | Authority order added to preamble and Part 1. |
| F7 | Foundation-only scope was blurred by premature admin route detail | Scope clarified. Admin route implementation is out of current scope. |

---

## Part 1 — Confirmed Business Rules (Authoritative)

The rules below are settled. They supersede any conflicting text elsewhere in the repository.
Any proposal that contradicts them must be rejected without escalating to owner discussion.

| Rule | Detail |
|---|---|
| **Currency** | All prices and costs stored as non-negative `INTEGER` paisas. PKR 3,450 = `345000`. Float arithmetic for money is prohibited. |
| **Catalog IDs preserved** | `collections.id` and `products.id` remain `VARCHAR(100)` slug-style. `variants.id` remains `INTEGER` autoincrement. No UUID migration of existing tables. |
| **Availability is independent of inventory** | `variants.availability` (`available` / `unavailable` / `unknown`) is set manually by the owner. It is never derived from `inventory_balances.on_hand`. The two systems are independent at the data layer. The admin UI may surface a recommendation when `on_hand` drops to zero, but it must not change `availability` automatically. |
| **Owner manages inventory** | Only the authenticated owner adjusts `inventory_balances.on_hand`. No supplier portal access in this phase. |
| **One active supplier per variant** | Exactly one `supplier_variants` row per `variant_id` may have `active = TRUE` at any time. Enforced by a partial unique index. |
| **Manual fulfillment** | AlphaZee coordinates supplier handoff manually. No automated supplier API assumed. |
| **Media outside PostgreSQL** | All image and video URLs stored as `TEXT`; files live in external storage. |
| **Archiving over deletion** | Records are deactivated via status or `is_active`, not hard-deleted. |
| **Checkout disabled** | Real order placement remains disabled. No order, payment, or shipment tables exist yet. |

---

## Part 2 — Technical Recommendations (Require Acknowledgement, Not Business Rules)

| Rec | Recommendation | Rationale |
|---|---|---|
| R1 | New table PKs use `UUID` with `gen_random_uuid()`. Existing catalog PKs unchanged. | Avoids sequential ID guessing in future admin URLs without requiring a catalog migration. |
| R2 | `supplier_variants.variant_id` is `INTEGER` (matching `variants.id`). | Preserves FK compatibility with existing catalog. No type migration. |
| R3 | `price_minor` on `variants` stays `INTEGER` (32-bit; max ~PKR 21.4M per variant). | No migration needed at current product price range. Revisit if luxury goods are added. |
| R4 | `stock_events.reason` uses `TEXT NOT NULL` with a `CHECK` constraint over a fixed value set. | Safer for reporting than free text; easier to extend than a PostgreSQL ENUM. |
| R5 | `suppliers.status` uses `TEXT NOT NULL` with a `CHECK` constraint. | Same rationale as R4. Consistent with how `AvailabilityStatus` is handled in the catalog. |
| R6 | Optimistic concurrency on `inventory_balances` via `version BIGINT`, enforced by a targeted `UPDATE … WHERE version = :expected`. | Prevents a second concurrent admin session from overwriting a count without knowing about the first write. See Part 4.6 for exact mechanism. |

---

## Part 3 — Catalog Schema Reference

> [!WARNING]
> **Verification status**: Backend unit tests (`test_catalog_unit.py`) exercise query compilation
> and model constraint inspection using mocks — they do **not** connect to a real database.
> No database-backed integration tests have been run. No migration has ever been applied.
> The `backend/alembic/versions/` directory contains only a `.gitkeep` file.
> The actual schema state of `alphazee_dev` is unknown until inspected directly.

The ORM models below describe the **intended** catalog schema as declared in
`backend/app/models/catalog.py`. This is the schema the initial catalog migration
must produce on an empty database.

### `collections`

| Column | Type | Nullable | Default | Constraints |
|---|---|---|---|---|
| `id` | `VARCHAR(100)` | NO | — | PK |
| `slug` | `VARCHAR(100)` | NO | — | UNIQUE NOT NULL |
| `name` | `VARCHAR(200)` | NO | — | NOT NULL |
| `description` | `TEXT` | YES | NULL | |
| `image_url` | `TEXT` | YES | NULL | |
| `is_active` | `BOOLEAN` | NO | `TRUE` | NOT NULL |
| `display_order` | `INTEGER` | NO | `0` | NOT NULL |

### `products`

| Column | Type | Nullable | Default | Constraints |
|---|---|---|---|---|
| `id` | `VARCHAR(100)` | NO | — | PK |
| `slug` | `VARCHAR(100)` | NO | — | UNIQUE NOT NULL |
| `title` | `VARCHAR(300)` | NO | — | NOT NULL |
| `description` | `TEXT` | YES | NULL | |
| `collection_id` | `VARCHAR(100)` | NO | — | FK → `collections(id)` ON DELETE RESTRICT |
| `image_url` | `TEXT` | YES | NULL | |
| `badge` | `VARCHAR(100)` | YES | NULL | |
| `is_active` | `BOOLEAN` | NO | `TRUE` | NOT NULL |
| `is_hero` | `BOOLEAN` | NO | `FALSE` | NOT NULL |
| `hero_order` | `INTEGER` | YES | NULL | |
| `hero_benefit` | `TEXT` | YES | NULL | |
| `hero_image_url` | `TEXT` | YES | NULL | |
| `hero_poster_url` | `TEXT` | YES | NULL | |
| `hero_video_url` | `TEXT` | YES | NULL | |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL |

### `variants`

| Column | Type | Nullable | Default | Constraints |
|---|---|---|---|---|
| `id` | `INTEGER` | NO | autoincrement | PK |
| `sku` | `VARCHAR(100)` | NO | — | UNIQUE NOT NULL |
| `product_id` | `VARCHAR(100)` | NO | — | FK → `products(id)` ON DELETE CASCADE |
| `size` | `VARCHAR(50)` | YES | NULL | |
| `color` | `VARCHAR(100)` | YES | NULL | |
| `price_minor` | `INTEGER` | NO | — | NOT NULL, CHECK (`price_minor >= 0`) |
| `is_active` | `BOOLEAN` | NO | `TRUE` | NOT NULL |
| `availability` | `TEXT` (ENUM `availability_status`) | NO | `'unknown'` | NOT NULL, values: `available`, `unavailable`, `unknown` |

**Indexes on `variants`:**
- `uq_variant_product_size_color`: UNIQUE on `(product_id, size, color)` with `NULLS NOT DISTINCT` (PostgreSQL 16+)
- Named check: `ck_variant_price_nonnegative`

---

## Part 4 — Foundation Phase Schema Proposal

> [!NOTE]
> **Scope of this phase**: `user_accounts`, `suppliers`, `supplier_memberships`,
> `supplier_variants`, `inventory_balances`, `stock_events`.
>
> `stock_reservations` is excluded and deferred. See Part 5.
> Admin API routes are excluded. See Part 7 (out of scope).
> No migrations generated or applied yet.

### 4.1 Entity Diagram

```
user_accounts ──────────────────────────────────┐
     │                                           │ actor (SET NULL)
     │ (user_id FK)                              ↓
supplier_memberships ── (supplier_id FK) ── suppliers
                                                │
                                    supplier_variants ── (variant_id FK) ── variants
                                                │
                                    inventory_balances
                                                │
                                           stock_events
```

---

### 4.2 `user_accounts`

Admin identity store. Scope in this phase: owner only.

> [!IMPORTANT]
> Customer accounts are a separate design decision (Q1). Do not add a `role` column
> or customer-specific fields until Q1 is resolved. This table must not be reused
> for customer logins without an explicit owner decision.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | Server-side generated. |
| `auth_subject` | `TEXT` | NO | — | NOT NULL, UNIQUE | External identity claim (e.g. JWT `sub`). Not a stored password; the auth provider is responsible for credential security. |
| `display_name` | `TEXT` | YES | NULL | | Optional label for audit log display (e.g. "Syed Najam"). |
| `is_active` | `BOOLEAN` | NO | `TRUE` | NOT NULL | Soft-revoke. Matches catalog convention. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | Updated on every write. |

**Indexes:**
- `uq_user_accounts_auth_subject`: UNIQUE on `(auth_subject)` — O(1) authentication lookup.

**Inbound FK from `stock_events.actor_user_id`**: `ON DELETE SET NULL` — preserves audit records when a user is removed.

---

### 4.3 `suppliers`

An approved local supplier that AlphaZee sources products from.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | |
| `name` | `TEXT` | NO | — | NOT NULL | Trade name (e.g. "Karachi Fabric Co."). Not unique — two separate registrations may share a name. |
| `slug` | `TEXT` | NO | — | NOT NULL, UNIQUE | URL-safe admin identifier (e.g. `karachi-fabric`). |
| `status` | `TEXT` | NO | `'active'` | NOT NULL, CHECK (`status IN ('active', 'inactive', 'suspended')`) | See operational meanings below. |
| `notes` | `TEXT` | YES | NULL | | Owner free-text: payment terms, contact details, WhatsApp number. Not exposed publicly. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | |

**Status meanings (application-enforced, not DB triggers):**
- `active`: supplier can fulfil orders; new `supplier_variants` may be assigned.
- `inactive`: archived; no new assignments. Existing `supplier_variants` and history preserved.
- `suspended`: temporarily blocked (Q2 — owner must confirm what the application should do: block new assignments only, or also warn on existing open items).

**Indexes:**
- `uq_suppliers_slug`: UNIQUE on `(slug)`.
- `idx_suppliers_status`: on `(status)` — supports admin listing filter.

**Cascade note:** `ON DELETE CASCADE` from `supplier_memberships` is safe (membership rows have no independent business history). `supplier_variants` uses `ON DELETE RESTRICT` — a supplier with variant assignments cannot be deleted.

---

### 4.4 `supplier_memberships`

Grants a `user_account` read/write access to a supplier in the admin portal. Composite PK; no surrogate key.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `user_id` | `UUID` | NO | — | NOT NULL, FK → `user_accounts(id)` ON DELETE CASCADE | Cascade: revoke all memberships when user is removed. |
| `supplier_id` | `UUID` | NO | — | NOT NULL, FK → `suppliers(id)` ON DELETE CASCADE | Cascade: remove membership when supplier is permanently deleted. |
| `active` | `BOOLEAN` | NO | `TRUE` | NOT NULL | Soft-revoke without deleting the row. |
| `granted_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | When membership was first created. |

**Primary key:** `(user_id, supplier_id)` — prevents duplicate grants.

**Indexes:**
- `idx_sm_supplier_id`: on `(supplier_id)` — list all members of a supplier.
- `idx_sm_user_id`: on `(user_id)` — list all suppliers accessible to a user.

**Scope note:** No `role` column in this phase. `active = TRUE / FALSE` is the only permission dimension. Role-based access is a future decision.

---

### 4.5 `supplier_variants`

Links a catalog `Variant` to the supplier that actively stocks it. At most one row per variant may be `active = TRUE` at any time.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | |
| `supplier_id` | `UUID` | NO | — | NOT NULL, FK → `suppliers(id)` ON DELETE RESTRICT | Block supplier deletion if variant assignments exist. |
| `variant_id` | `INTEGER` | NO | — | NOT NULL, FK → `variants(id)` ON DELETE RESTRICT | Block variant deletion if supplier linkages exist. Archive via `variants.is_active = FALSE`. |
| `active` | `BOOLEAN` | NO | `TRUE` | NOT NULL | Whether this is the current active supplier for this variant. |
| `supplier_cost_minor` | `INTEGER` | YES | NULL | CHECK (`supplier_cost_minor >= 0`) | Live agreed wholesale cost in paisas. `NULL` = not yet negotiated. This is the current price, not a historical snapshot; order-line snapshots are a future concern (see Part 5). |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | Updated when cost or `active` changes. |

**Indexes:**
- `idx_sv_supplier_id`: on `(supplier_id)` — list all variants for a supplier.
- `idx_sv_variant_id`: on `(variant_id)` — find supplier linkage for a given variant.
- `uq_sv_one_active_per_variant`: UNIQUE partial index on `(variant_id)` WHERE `active = TRUE`.

  This is the database enforcement for the one-active-supplier-per-variant rule. Attempting to
  insert or update a second row with `active = TRUE` for the same `variant_id` will raise a
  unique constraint violation. The application must deactivate the old row before activating
  a new one, and must do so in a single transaction.

**Cascade rationale:** Both FKs use `ON DELETE RESTRICT`. A supplier or variant with linked
`supplier_variants` rows cannot be deleted. This preserves cost history and prevents
`inventory_balances` from becoming orphaned.

---

### 4.6 `inventory_balances`

One-to-one with `supplier_variants`. Tracks the owner-maintained physical on-hand count.
Created atomically alongside its `supplier_variant` row in a single transaction.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `supplier_variant_id` | `UUID` | NO | — | PK, FK → `supplier_variants(id)` ON DELETE CASCADE | PK is also the FK. One balance per supplier-variant. |
| `on_hand` | `INTEGER` | NO | `0` | NOT NULL, CHECK (`on_hand >= 0`) | Physical count as last recorded by the owner. Never negative. |
| `version` | `BIGINT` | NO | `0` | NOT NULL | Optimistic concurrency counter. See write mechanism below. |
| `last_counted_at` | `TIMESTAMPTZ` | YES | NULL | | When the owner last physically confirmed the count. `NULL` = never counted. Stale warning threshold (e.g. > 7 days) is an application-layer decision, not a DB constraint. |

**Indexes:** None beyond the PK. `supplier_variant_id` is the only access path.

#### Atomic write mechanism (F2 correction)

The write function **must not** read the row first and then compare `version` in application
code. That is a TOCTOU race. The correct mechanism:

```sql
UPDATE inventory_balances
   SET on_hand   = :new_on_hand,
       version   = version + 1,
       last_counted_at = :last_counted_at   -- optional, when from a physical count
 WHERE supplier_variant_id = :supplier_variant_id
   AND version             = :expected_version;
```

The application checks `rowcount` after execution:
- `rowcount == 1` → success. Continue to insert the `stock_events` row and commit.
- `rowcount == 0` → the version changed between when the admin loaded the form and when they
  submitted it. Raise `StaleInventoryError` (a domain exception, not an HTTP exception).
  The route layer translates this to `HTTP 409 Conflict` with a message instructing the
  operator to reload and resubmit.

Both the `UPDATE` and the `INSERT` into `stock_events` are committed in the **same
transaction**. If either step fails, both are rolled back. There are no partial writes.

**Read-before-display is still needed:** To populate the adjustment form with the current
`on_hand` and pass `expected_version` to the form, a `SELECT` is performed at page-load time.
This is safe because the version guard at write-time detects any intervening change.

---

### 4.7 `stock_events`

Immutable append-only audit log. One row is inserted per inventory adjustment, in the same
transaction as the `UPDATE` to `inventory_balances`.

| Column | Type | Nullable | Default | Constraints | Notes |
|---|---|---|---|---|---|
| `id` | `UUID` | NO | `gen_random_uuid()` | PK | |
| `supplier_variant_id` | `UUID` | NO | — | NOT NULL, FK → `supplier_variants(id)` ON DELETE RESTRICT | Prevents deletion of a supplier_variant that has audit history. Also blocks the CASCADE from `inventory_balances` if events exist. |
| `actor_user_id` | `UUID` | YES | NULL | FK → `user_accounts(id)` ON DELETE SET NULL | Who triggered the change. `NULL` permitted for future system events. Application currently requires this to be non-null for all manual adjustments. |
| `previous_on_hand` | `INTEGER` | NO | — | NOT NULL | Snapshot of `on_hand` before the update. |
| `new_on_hand` | `INTEGER` | NO | — | NOT NULL | Snapshot of `on_hand` after the update. |
| `delta` | `INTEGER` | NO | — | NOT NULL | `new_on_hand − previous_on_hand`. Stored redundantly for query convenience. Application must compute and verify this before inserting; no DB-level constraint enforces it. |
| `reason` | `TEXT` | NO | — | NOT NULL, CHECK (`reason IN ('manual_count', 'supplier_receipt', 'reservation_fulfilled', 'reservation_cancelled', 'rto_return', 'adjustment_correction')`) | Constrained reason code. Adding new values requires extending the CHECK in a new migration. |
| `notes` | `TEXT` | YES | NULL | | Optional operator note for this event (e.g. "TCS CN-123456"). |
| `occurred_at` | `TIMESTAMPTZ` | NO | `now()` | NOT NULL | Wall-clock time of the write. Immutable after insert. |

**Indexes:**
- `idx_se_sv_occurred`: on `(supplier_variant_id, occurred_at DESC)` — fetch event log per variant in reverse chronological order.
- `idx_se_actor`: on `(actor_user_id)` — audit all adjustments by a given user.

**Append-only rule:** No `UPDATE` or `DELETE` is permitted on this table. Application code
must enforce this. No delete path should be exposed in admin tooling.

---

## Part 5 — Owner Inventory Display (Approved)

The approved display format for the owner admin panel is:

```
Physical 10  |  Held 2  |  Available 8
             Held by: Order #1042, Order #1058
```

Where:
- **Physical** = `inventory_balances.on_hand` — the last recorded count.
- **Held** = sum of `quantity` across open `stock_reservations` rows for this `supplier_variant_id` where `stage NOT IN ('fulfilled', 'cancelled', 'returned')`.
- **Available** = Physical − Held. This is a computed value; it is **not stored** in the database.
- **Order references** = list of `order_line_id` values from those open reservations, displayed as order numbers.

> [!WARNING]
> **This display is dependent on the reservation module.** `stock_reservations` is deferred
> (see Part 6). Until reservations are implemented:
> - Held = 0 (no reservations table exists).
> - Available = Physical (identical to `on_hand`).
> - No order references can be shown.
>
> The admin panel must clearly display "Reservation tracking not yet active" rather than
> showing "Held 0" in a way that implies the display is complete.

---

## Part 6 — Deferred: `stock_reservations`

`stock_reservations` is excluded from this phase.

**Reason:** The `order_line_id` column (required for the Held display above) has no FK target
because `order_lines` does not exist. Building `stock_reservations` before the order schema is
approved produces a table with no referential integrity at its most critical join.

**Prerequisites before this table can be specified:**

| Item | Why needed |
|---|---|
| `order_lines` PK type and table structure | `stock_reservations.order_line_id` must be a typed FK |
| Multi-supplier order policy (Q5) | Determines whether one order can produce reservations against multiple `supplier_variants` |
| Reservation stage transitions (Q4, Q env) | Determines the valid `stage` values and what triggers each transition |
| Pre-payment vs COD timing (Q4) | Determines whether `payment_due_at` is always present or conditional |
| Reservation cancellation and `on_hand` restoration | Determines whether a cancellation produces a `stock_event` with `reason = 'reservation_cancelled'` |

The Held and Available figures in Part 5 depend entirely on this table. Neither can be accurate
until reservations exist.

---

## Part 7 — Remaining Business Questions

Only genuine unresolved business decisions are listed here. Technical recommendations (Part 2)
are settled. Confirmed rules (Part 1) are not re-opened.

| # | Question | Why it cannot be resolved technically |
|---|---|---|
| **Q1** | Will customer accounts eventually share `user_accounts`, or will they use a separate table? | Changes whether a `role` or `type` column is needed and affects how the authentication layer is built. A wrong assumption here causes a breaking migration later. |
| **Q2** | When a supplier's `status` is set to `'suspended'`: should the application block all new `supplier_variant` assignments, block new reservations only, or only display a warning? | The application behaviour differs significantly across these options. Without an answer the `suspended` status is a label with no enforced effect. |
| **Q3** | When the owner switches a variant to a new active supplier: should the previous supplier's `inventory_balances.on_hand` be reset to 0 (with a `stock_event`), or left as-is? | Affects whether a handover creates a mandatory audit trail on the old balance. |
| **Q4** | (Reservations — deferred) Does AlphaZee pre-pay suppliers before dispatch, or only after confirmed COD remittance? | Determines whether `payment_due_at` is always populated, conditional, or absent from `stock_reservations`. |
| **Q5** | (Reservations — deferred) Can a single order span two suppliers? If yes: one consolidated shipment or two split shipments? | Determines whether `stock_reservations` has a one-to-one or one-to-many relationship with an order and how shipping fees are allocated. |
| **Q6** | Are the six proposed `stock_events.reason` codes sufficient for day-one operations, or are additional codes needed before launch? | Determines whether the initial `CHECK` constraint covers real use cases or needs an immediate extension. |

---

## Part 8 — Phased Implementation Plan (Foundation Only)

> [!IMPORTANT]
> **Migrations are paused. Privileged admin routes are not enabled.**
> This plan activates only after the database pause is explicitly lifted by the owner
> and Q1, Q2, Q3, Q6 are resolved (Q4, Q5 may remain deferred).

### Phase 0 — Prerequisites

1. Owner resolves Q1–Q3 and Q6 and records them in `docs/decisions.md`.
2. Owner explicitly lifts the database pause in `AGENTS.md §4`.
3. Verify `alphazee_test` database exists. Confirm `conftest.py` guards reject `alphazee_dev`.
4. Inspect `alphazee_dev` directly:
   - If it has no tables → proceed to Phase 1A-fresh path.
   - If it has tables → compare against the catalog revision produced in Phase 1A before stamping.

---

### Phase 1A — Initial Catalog Migration

**Goal:** Produce a real Alembic migration that creates the full catalog schema
(`availability_status` enum type, `collections`, `products`, `variants` with all indexes
and constraints) on a **fresh empty database**.

> [!CAUTION]
> Do **not** use an empty baseline revision. Do **not** use `Base.metadata.create_all()`.
> `alembic stamp` is only permitted after the live database is verified to match this revision.

**Process:**

1. Point `DATABASE_URL` at a fresh, isolated `alphazee_migration_test` database
   (not `alphazee_dev`, not `alphazee_test`).
2. Run `alembic revision --autogenerate -m "initial_catalog_schema"`.
3. **Manually inspect the generated migration file.** Verify it includes:
   - `CREATE TYPE availability_status AS ENUM ('available', 'unavailable', 'unknown')`
   - `CREATE TABLE collections` with all columns, defaults, and UNIQUE on `slug`
   - `CREATE TABLE products` with FK `ON DELETE RESTRICT` to `collections`
   - `CREATE TABLE variants` with:
     - `CHECK (price_minor >= 0)` named `ck_variant_price_nonnegative`
     - UNIQUE index `uq_variant_product_size_color` with `NULLS NOT DISTINCT` on `(product_id, size, color)`
     - FK `ON DELETE CASCADE` to `products`
   - No `DROP TABLE` or `DROP COLUMN` statements
4. Run `alembic upgrade head` on the isolated test database. Confirm it applies cleanly.
5. Run `alembic downgrade -1`. Confirm it drops all three tables and the enum type cleanly.
6. Run `alembic upgrade head` again (upgrade / downgrade / upgrade cycle).
7. Commit the migration file.

**To apply to `alphazee_dev` (separately authorized):**
- If `alphazee_dev` is empty: run `alembic upgrade head` directly.
- If `alphazee_dev` already has tables: inspect its schema against the migration's DDL.
  Only if they match exactly: run `alembic stamp <revision_id>`.
  If they do not match: do not stamp; investigate the discrepancy and report to the owner.

---

### Phase 1B — Foundation ORM Models (code only, no migration)

**Goal:** Add new SQLAlchemy model classes without touching the database.

**New files:**
- `backend/app/models/suppliers.py` — `UserAccount`, `Supplier`, `SupplierMembership`
- `backend/app/models/inventory.py` — `SupplierVariant`, `InventoryBalance`, `StockEvent`

**Edit:**
- `backend/app/models/__init__.py` — import new modules so Alembic metadata scan includes them

**Rules:**
- All models inherit from `app.database.Base`.
- All new UUIDs: `server_default=text("gen_random_uuid()")`.
- `@validates` on `suppliers.status` and `stock_events.reason` to reject unknown values.
- No `create_all()`. No `drop_all()`. Alembic owns all schema creation.
- Docstrings and layout matching `catalog.py` style.

**New unit tests — `backend/tests/test_suppliers_unit.py`**
(all pass without a database connection):

- `test_user_account_model_imports` — model can be imported and inspected.
- `test_supplier_status_validates` — `@validates` accepts `active/inactive/suspended`, rejects unknown.
- `test_supplier_variant_partial_index` — `uq_sv_one_active_per_variant` partial index is present in `__table_args__` with correct expression.
- `test_inventory_balance_check_constraint` — `CHECK (on_hand >= 0)` present in `__table_args__`.
- `test_stock_event_fk_cascade_rules` — `supplier_variant_id` FK uses `ON DELETE RESTRICT`; `actor_user_id` FK uses `ON DELETE SET NULL`.
- `test_stock_event_reason_validates` — `@validates` accepts all six approved codes, rejects unknown strings.
- `test_supplier_variant_cost_non_negative` — `CHECK (supplier_cost_minor >= 0)` present.

---

### Phase 1C — Foundation Migration (guarded test DB only)

**Pre-condition:** Phase 1A revision committed. Phase 1B code reviewed and approved.
`alphazee_test` contains the catalog tables (applied via Phase 1A migration).

**Process:**
1. Point `DATABASE_URL` at `alphazee_test`.
2. Run `alembic revision --autogenerate -m "add_supplier_inventory_foundation"`.
3. **Manually inspect** the generated SQL. Verify:
   - No `DROP TABLE`, `DROP COLUMN`, or `ALTER COLUMN` on `collections`, `products`, or `variants`.
   - No type change on `variants.id`, `products.id`, or `collections.id`.
   - `CREATE TABLE user_accounts` with UUID PK, UNIQUE on `auth_subject`.
   - `CREATE TABLE suppliers` with CHECK on `status`.
   - `CREATE TABLE supplier_memberships` with composite PK, correct cascade rules.
   - `CREATE TABLE supplier_variants` with INTEGER `variant_id` FK, UNIQUE partial index.
   - `CREATE TABLE inventory_balances` with `on_hand >= 0` CHECK, `version BIGINT`.
   - `CREATE TABLE stock_events` with `reason` CHECK, `ON DELETE RESTRICT` and `ON DELETE SET NULL` FKs.
4. `alembic upgrade head` on `alphazee_test`.
5. `alembic downgrade -1`. Confirm only foundation tables are dropped; catalog tables untouched.
6. `alembic upgrade head` again.
7. Owner approves before applying to `alphazee_dev`.

---

### Phase 2 — Query Layer

**New file:** `backend/app/queries/suppliers.py`

**Read functions** (no side effects, no DB writes):
- `get_active_suppliers(db) -> list[Supplier]`
- `get_supplier_by_id(db, supplier_id: UUID) -> Supplier | None`
- `get_active_supplier_variant(db, variant_id: int) -> SupplierVariant | None`
- `get_inventory_balance(db, supplier_variant_id: UUID) -> InventoryBalance | None`
- `get_stock_events(db, supplier_variant_id: UUID, *, limit: int = 50) -> list[StockEvent]`

**Write function** (see atomic mechanism in Part 4.6):

```python
def adjust_inventory(
    db: Session,
    *,
    supplier_variant_id: UUID,
    actor_user_id: UUID | None,
    new_on_hand: int,
    reason: str,
    expected_version: int,
    notes: str | None = None,
    last_counted_at: datetime | None = None,
) -> StockEvent:
    """
    Atomically update inventory_balances and record a stock_event.

    Uses a targeted UPDATE WHERE version = expected_version.
    Raises StaleInventoryError if 0 rows updated (concurrent modification detected).
    Raises ValueError if new_on_hand < 0.
    Both writes are committed in the same transaction.
    """
```

**Domain exception:**
```python
class StaleInventoryError(Exception):
    """Raised when the inventory version changed before the update was applied."""
```

**Rules:**
- No write logic in the public catalog query layer.
- No HTTP exceptions from the query layer — the route layer translates domain errors.
- `adjust_inventory` must not perform a `SELECT` to check version before the `UPDATE`.
  The `UPDATE WHERE version = :expected` is the check.

---

### Phase 3 — Concurrency Unit Tests

**New file:** `backend/tests/test_inventory_unit.py`
(connection-free constraint and validation tests matching Phase 1B)

**New file:** `backend/tests/test_inventory_integration.py`
(database-backed; deferred until Phase 1C migration applied to `alphazee_test`)

**Required integration test coverage:**

#### Standard path
- Create `Supplier` + `SupplierVariant` + `InventoryBalance` atomically. Verify rollback leaves nothing.
- `adjust_inventory` with correct `expected_version=0`: `on_hand` updated, `version` becomes 1, one `StockEvent` inserted with correct `delta`.
- `adjust_inventory` with `new_on_hand=-1`: raises `ValueError` before touching the DB.
- `on_hand >= 0` CHECK: direct SQL `UPDATE inventory_balances SET on_hand = -1` raises `IntegrityError`.
- Partial unique index: inserting a second `supplier_variants` row with `active=TRUE` for the same `variant_id` raises `IntegrityError`.
- `StockEvent ON DELETE RESTRICT`: attempting to delete a `supplier_variant` with events raises `IntegrityError`.
- `actor_user_id ON DELETE SET NULL`: deleting a `user_account` sets `stock_events.actor_user_id` to `NULL`; event row survives.

#### Two-session concurrency test (F3 correction)

This test must open **two real database connections** (not a mock). It must not use
`unittest.mock` or session-level isolation that prevents actual lock contention.

```
Scenario:
  Session A and Session B both read inventory_balances for the same supplier_variant_id.
  Both observe version = 0, on_hand = 10.

  Session A calls adjust_inventory(new_on_hand=8, expected_version=0).
    → UPDATE WHERE version = 0 matches 1 row.
    → version becomes 1, on_hand becomes 8.
    → StockEvent inserted with previous=10, new=8.
    → Session A commits.

  Session B calls adjust_inventory(new_on_hand=5, expected_version=0).
    → UPDATE WHERE version = 0 matches 0 rows (version is now 1).
    → rowcount == 0 → StaleInventoryError raised.
    → Session B rolls back. No StockEvent inserted.

Assertions:
  - Final on_hand == 8 (Session A's value, not Session B's).
  - Final version == 1 (incremented exactly once).
  - Exactly one StockEvent row exists for this supplier_variant_id.
  - StaleInventoryError was raised from Session B.
  - Session B's transaction was fully rolled back (no partial StockEvent).
```

Implementation note: Use two separate `SessionLocal()` instances with `autocommit=False`.
Sequence the operations in a single test using explicit `session.flush()` calls to control
the interleaving. Do not use threads unless necessary; deterministic sequencing is preferable.

---

### Phase 4 — Documentation Update

After each phase is verified:
- `docs/progress.md` — completed work, exact test results, deferred items.
- `docs/architecture.md` — new table descriptions, updated entity diagram.
- `docs/decisions.md` — record Q1–Q6 answers as CONFIRMED when resolved.
- `docs/database-design-pending.md` — mark resolved items; do not delete them.
- `AGENTS.md §4` — update database pause scope after each authorized step.

---

## Part 9 — Explicitly Out of Scope

Must not be implemented until separately authorized:

- `stock_reservations` table and all reservation lifecycle logic
- Order, payment, shipment, and courier settlement tables
- Customer accounts or guest checkout
- Purchase-time snapshot tables for order lines
- Admin authentication, session tokens, and authorization middleware
- Privileged admin API routes (paused — do not enable)
- Supplier-facing portal or login flows
- COD remittance tracking, RTO accounting, refund processing
- Frontend changes related to inventory or admin functions
- Marketing attribution (UTM) fields
- Private file storage for payment receipts
- Any `ALTER TABLE` or schema changes to `collections`, `products`, or `variants`
