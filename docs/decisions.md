# AlphaZee — Architectural & Commerce Decisions

Owner: Syed Najam. Milestone: Catalog Foundation & Frontend Integration.

---

## 1. Confirmed Decisions

These decisions have been explicitly approved by the business owner and are binding on all current implementation work.

### 1.1 Commercial & Geographic Scope
- **Launch Country**: Pakistan.
- **Currency**: Pakistani Rupee (PKR).
- **Payment Methods**:
  - Cash on Delivery (COD).
  - Manual Bank Transfer (owner verifies cleared funds in bank account before shipping; a customer receipt screenshot alone is not payment confirmation).
- **Fulfillment Model**: Initially manual supplier handoff. AlphaZee lists products from approved local suppliers and manually coordinates order fulfillment. Automated supplier integration is out of current scope.

### 1.2 Technology & Runtime
- **Backend**: Python 3.13, FastAPI, synchronous SQLAlchemy 2.0, Alembic, PostgreSQL 16.
  - *Rationale for Python 3.13*: Python 3.14 (pre-release) causes internal typing inspection errors in SQLAlchemy 2.0 declarative mapper when scanning `Mapped[Optional[...]]` annotations. Python 3.13 is the stable release with full ecosystem support.
- **Frontend**: Vite SPA with Vanilla JavaScript and custom Vanilla CSS.
  - *Rationale*: Maximum control, zero heavy UI framework overhead, fast initial load on Pakistan mobile networks.
- **Network Architecture**: Same-origin `/api/v1` routing via Vite proxy in development; configurable API client in frontend.

### 1.3 Data Representation & Safety
- **Money**: Authoritative values stored as integer minor units (paisas, where PKR 3,450 = `345000`). Display helpers use integer division and format with thousands separators. Float arithmetic for currency math is prohibited.
- **Variant Uniqueness**: Enforced in PostgreSQL using `postgresql_nulls_not_distinct=True` on `(product_id, size, color)` to safely handle products with null sizes or colors.
- **Foreign Keys**: `Collection` $\rightarrow$ `Product` uses `ON DELETE RESTRICT` (products cannot be silently orphaned or deleted by deleting a collection). `Product` $\rightarrow$ `Variant` uses `ON DELETE CASCADE`.
- **Cart Keying**: Purchasable selections are identified strictly by database `variant_id`.
- **Checkout Boundary**: Real order placement is disabled during the catalog milestone. Checkout is clearly labeled as a preview; the cart is preserved; no fictitious orders or receipts are stored.

---

## 2. Proposed Decisions

These choices are recorded as proposals and remain open for discussion with the business owner before implementation.

### 2.1 Proposed: Guest Checkout First
- **Proposal**: Permit customers to place orders using name, phone number, and delivery address without requiring upfront password creation or account registration.
- **Rationale**: Reduces checkout friction and drop-off on mobile devices in the Pakistan market. Customer accounts can be introduced later by linking past phone numbers.

### 2.2 Proposed: Purchase-Time Immutable Snapshots
- **Proposal**: When orders are introduced, store an immutable snapshot of variant title, SKU, size, color, agreed customer price, and supplier cost at the moment of order placement.
- **Rationale**: Protects order history and financial reporting from subsequent changes or deletions in the catalog.

### 2.3 Proposed: Flat Shipping Rate per Order
- **Proposal**: Standard flat-rate shipping (e.g. PKR 200–250) for orders across Pakistan, with free shipping threshold (e.g. PKR 5,000+).
- **Rationale**: Simple for customers to understand. Actual courier weight charges will be compared during the pilot phase.
