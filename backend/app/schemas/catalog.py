"""
Pydantic response schemas for the AlphaZee catalog API (v1).

Design rules:
- Prices are exposed as both `price_pkr` (integer whole rupees) and
  `price_minor` (raw paisas) so callers can use either without ambiguity.
- Currency is always documented — no naked numbers.
- Inactive records are never included in list responses (filtered at query layer).
- Hero fields only present on products where is_hero=True.
- Variant availability is always a string enum value: available / unavailable / unknown.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared helpers ─────────────────────────────────────────────────────────────


class CurrencyAmount(BaseModel):
    """Structured price value with explicit currency."""

    minor: int = Field(
        description="Price in PKR minor units (paisas). 1 PKR = 100 paisas."
    )
    pkr: int = Field(description="Price in whole PKR (minor // 100).")
    currency: str = Field(default="PKR", description="ISO 4217 currency code.")
    formatted: str = Field(description="Human-readable price string, e.g. 'PKR 3,450'.")

    @classmethod
    def from_minor(cls, minor: int) -> "CurrencyAmount":
        pkr = minor // 100
        return cls(
            minor=minor,
            pkr=pkr,
            currency="PKR",
            formatted=f"PKR {pkr:,}",
        )


# ── Variant ────────────────────────────────────────────────────────────────────


class VariantSchema(BaseModel):
    """A single purchasable variant (size + color combination)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    price: CurrencyAmount
    availability: str = Field(
        description="One of: available, unavailable, unknown."
    )

    @classmethod
    def from_orm_model(cls, variant) -> "VariantSchema":  # type: ignore[override]
        return cls(
            id=variant.id,
            sku=variant.sku,
            size=variant.size,
            color=variant.color,
            price=CurrencyAmount.from_minor(variant.price_minor),
            availability=variant.availability.value,
        )


# ── Collection ─────────────────────────────────────────────────────────────────


class CollectionSchema(BaseModel):
    """A product collection shown in the storefront filter bar."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int


class CollectionListResponse(BaseModel):
    collections: list[CollectionSchema]
    total: int


# ── Product (list item) ────────────────────────────────────────────────────────


class ProductSummarySchema(BaseModel):
    """
    Condensed product representation used in listing responses.

    Includes only the lowest active variant price for display — the full
    variant list is available via the product detail endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    description: Optional[str] = None
    collection_id: str
    image_url: Optional[str] = None
    badge: Optional[str] = None
    is_hero: bool

    # Lowest active variant price (for card display)
    min_price: Optional[CurrencyAmount] = Field(
        default=None,
        description=(
            "Lowest price across all active variants. "
            "Null if the product has no active variants."
        ),
    )


class ProductListResponse(BaseModel):
    products: list[ProductSummarySchema]
    total: int
    page: int
    page_size: int
    collection_id: Optional[str] = None


# ── Product (detail) ──────────────────────────────────────────────────────────


class HeroMetaSchema(BaseModel):
    """Hero carousel presentation data — only present when is_hero=True."""

    order: Optional[int] = None
    benefit: Optional[str] = None
    image_url: Optional[str] = None
    poster_url: Optional[str] = None
    video_url: Optional[str] = None


class ProductDetailSchema(BaseModel):
    """
    Full product detail including all active variants.

    Hero fields are bundled under `hero` and only present when is_hero=True.
    Variant availability is explicitly stated — never inferred.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    description: Optional[str] = None
    collection_id: str
    image_url: Optional[str] = None
    badge: Optional[str] = None
    is_hero: bool
    hero: Optional[HeroMetaSchema] = None
    variants: list[VariantSchema]
