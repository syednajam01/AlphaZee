"""
catalog.py — SQLAlchemy ORM models for the AlphaZee product catalog.

Schema: Collection → Product → Variant

Design rules enforced via database constraints:
- All prices stored as non-negative integer PKR minor units (paisas).
  At launch AlphaZee prices are quoted in whole PKR, so price = 3450 means
  PKR 3,450 (no subdivision currently used, but stored correctly for future).
- Slugs are unique so URLs are stable and conflict-free.
- SKUs are globally unique across all products.
- Variant (product_id, size, color) combination is unique per product (NULLS NOT DISTINCT).
- Foreign keys: Collection FK uses RESTRICT to prevent accidental orphan products; Product → Variant uses CASCADE.
- Order history must snapshot prices, titles, and variant descriptions at purchase time; variant records are not protected by FK for order history purposes.
- Hero entries reference the catalog product rather than duplicating data.
- Image / video URLs stored as text; files live outside the database.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────


class AvailabilityStatus(str, enum.Enum):
    """
    Manually maintained availability for a variant.

    - AVAILABLE   : the variant can be added to cart and proceeds to checkout.
    - UNAVAILABLE : the variant exists but is out of stock / not offered.
    - UNKNOWN     : availability has not yet been confirmed with the supplier.
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Collection ────────────────────────────────────────────────────────────────


class Collection(Base):
    """
    A product collection / category (e.g. Essentials, Streetwear).

    Products belong to exactly one collection.
    """

    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    """Stable, human-readable identifier (e.g. 'essentials')."""

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    """URL-safe slug — must be unique across all collections."""

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    """Display name shown to customers."""

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Short marketing description (optional)."""

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """URL to the collection hero image; file lives outside the database."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Inactive collections and their products are excluded from public API responses."""

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Lower numbers appear first in collection listings."""

    # Relationship
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="collection",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Collection id={self.id!r} slug={self.slug!r}>"


# ── Product ───────────────────────────────────────────────────────────────────


class Product(Base):
    """
    A single catalog product (e.g. Heavyweight Boxy Tee).

    Every purchasable product must have at least one Variant, including
    products that have no visible size/color options.
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    """Stable product identifier (e.g. 'prod-heavyweight-tee')."""

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    """URL-safe slug for product detail pages."""

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    collection_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("collections.id", ondelete="RESTRICT"), nullable=False
    )
    """Foreign key to the owning collection. Prevents accidental orphan products."""

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Primary product image URL."""

    badge: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Short badge label shown on product cards (e.g. 'Core Basic')."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Inactive products are excluded from public API responses."""

    # Hero / carousel presentation metadata
    is_hero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """True if this product appears in the homepage hero carousel."""

    hero_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Sort order within the hero carousel. Null when is_hero=False."""

    hero_benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Short marketing benefit text shown in the hero slide."""

    hero_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Hero slide background image (may differ from product card image)."""

    hero_poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Video poster image for the hero slide (shown while video loads)."""

    hero_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Background video URL for the hero slide."""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    collection: Mapped[Collection] = relationship("Collection", back_populates="products")
    variants: Mapped[list[Variant]] = relationship(
        "Variant", back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id!r} slug={self.slug!r}>"


# ── Variant ───────────────────────────────────────────────────────────────────


class Variant(Base):
    """
    A purchasable variant of a product — a specific (size, color) combination.

    Every purchasable product must have at least one Variant. Products without
    visible options have a single Variant with size=None and color=None.

    Prices are stored as non-negative integer PKR minor units (paisas).
    At the current scale, 1 PKR = 100 paisas, so PKR 3,450 → price=345000.
    The API exposes price_pkr (whole rupees) and price_minor (raw stored value)
    so the frontend can display either without losing precision.
    """

    __tablename__ = "variants"
    __table_args__ = (
        # A product cannot have two variants with the same size+color combination.
        # Uses postgresql_nulls_not_distinct=True (PostgreSQL 16+) so that NULL
        # values are treated as matching (e.g. (prod-1, NULL, NULL) cannot be duplicated).
        Index(
            "uq_variant_product_size_color",
            "product_id",
            "size",
            "color",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("price_minor >= 0", name="ck_variant_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    """Globally unique stock-keeping unit identifier."""

    product_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """Size label (e.g. 'S', 'M', '32'). Null for products with no size option."""

    color: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Color name (e.g. 'Chalk White'). Null for products with no color option."""

    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    """
    Price in PKR minor units (paisas). Non-negative.
    PKR 3,450 = 345000 paisas.
    Use price_pkr property for display; use price_minor for storage and arithmetic.
    """

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    """Inactive variants are excluded from public API responses."""

    availability: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, name="availability_status"),
        nullable=False,
        default=AvailabilityStatus.UNKNOWN,
    )
    """
    Manually maintained availability status. Never derived from supplier stock.
    - AVAILABLE   : can be purchased.
    - UNAVAILABLE : not currently purchasable.
    - UNKNOWN     : not yet confirmed.
    """

    # Relationship
    product: Mapped[Product] = relationship("Product", back_populates="variants")

    @staticmethod
    def normalize_option(value: str | None) -> str | None:
        """
        Normalize an option string (size or color).
        Strips leading/trailing whitespace and converts empty/whitespace-only strings to None.
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @property
    def price_pkr(self) -> int:
        """
        Price in whole PKR (divided by 100 via integer division). Convenience helper for display.
        Note: Any fractional rupee prices (e.g. 345050 minor units = PKR 3,450.50)
        will truncate the fractional part. Use price_minor for exact calculations and storage.
        """
        return self.price_minor // 100

    def __repr__(self) -> str:
        return (
            f"<Variant id={self.id} sku={self.sku!r} "
            f"size={self.size!r} color={self.color!r} "
            f"price=PKR{self.price_pkr}>"
        )
