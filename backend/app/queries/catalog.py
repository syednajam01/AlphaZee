"""
Catalog query functions for AlphaZee.

All functions accept a SQLAlchemy Session and return ORM objects or None.
They never raise HTTP exceptions — that is the route layer's responsibility.

Rules:
- Public queries always filter is_active=True on collections, products,
  and variants. Inactive records are invisible to API consumers.
- Pagination uses LIMIT/OFFSET with a capped maximum page size.
- Hero products are selected by is_hero=True, ordered by hero_order ASC.
- The catalog is the single source of truth for prices; no price logic
  belongs in route handlers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import Collection, Product, Variant

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


# ── Collections ────────────────────────────────────────────────────────────────


def get_active_collections(db: Session) -> list[Collection]:
    """Return all active collections ordered by display_order ASC, then name."""
    stmt = (
        select(Collection)
        .where(Collection.is_active.is_(True))
        .order_by(Collection.display_order.asc(), Collection.name.asc())
    )
    return list(db.scalars(stmt).all())


# ── Products ───────────────────────────────────────────────────────────────────


def get_active_products(
    db: Session,
    *,
    collection_id: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Product], int]:
    """
    Return a paginated list of active products with their active variants
    eager-loaded.

    Returns (products, total_count) where total_count is the un-paginated count
    for the given filter (used to build pagination metadata).
    """
    page_size = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    # Base filter
    base_stmt = select(Product).where(Product.is_active.is_(True))
    if collection_id:
        base_stmt = base_stmt.where(Product.collection_id == collection_id)

    # Count query (no load options, no limit/offset)
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Data query — eager-load only active variants
    data_stmt = (
        base_stmt
        .options(
            selectinload(Product.variants).where(Variant.is_active.is_(True))
        )
        .order_by(Product.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    products = list(db.scalars(data_stmt).all())

    return products, total


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    """
    Return a single active product by slug with active variants eager-loaded.

    Returns None if the product does not exist or is inactive — the route
    layer translates None to a 404 response.
    """
    stmt = (
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(
            selectinload(Product.variants).where(Variant.is_active.is_(True))
        )
    )
    return db.scalars(stmt).first()


def get_hero_products(db: Session) -> list[Product]:
    """
    Return active hero products ordered by hero_order ASC.

    Used by the homepage hero carousel. Returns an empty list if no hero
    products exist — the frontend must handle this case gracefully.
    """
    stmt = (
        select(Product)
        .where(Product.is_active.is_(True), Product.is_hero.is_(True))
        .options(
            selectinload(Product.variants).where(Variant.is_active.is_(True))
        )
        .order_by(Product.hero_order.asc().nullslast())
    )
    return list(db.scalars(stmt).all())


# ── Price helpers ─────────────────────────────────────────────────────────────


def get_min_price_minor(product: Product) -> int | None:
    """
    Return the lowest price_minor across all active variants, or None.

    Used to populate the `min_price` field on list responses.
    """
    active_prices = [v.price_minor for v in product.variants if v.is_active]
    return min(active_prices) if active_prices else None
