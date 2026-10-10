"""
Read-only catalog API endpoints — GET /api/v1/collections and /api/v1/products.

Rules:
- All responses exclude inactive collections, products, and variants.
- Product listing supports optional collection_id filter and bounded pagination.
- Hero products are a sub-set of products (is_hero=True) returned on demand.
- Prices are always structured with explicit PKR currency.
- Unknown or inactive slugs return 404 — no details about why are leaked.
- No write endpoints are defined in this file.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.queries.catalog import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    get_active_collections,
    get_active_products,
    get_hero_products,
    get_min_price_minor,
    get_product_by_slug,
)
from app.schemas.catalog import (
    CollectionListResponse,
    CollectionSchema,
    CurrencyAmount,
    HeroMetaSchema,
    HeroProductSchema,
    ProductDetailSchema,
    ProductListResponse,
    ProductSummarySchema,
    VariantSchema,
)

router = APIRouter(tags=["catalog"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _build_product_summary(product) -> ProductSummarySchema:
    min_minor = get_min_price_minor(product)
    return ProductSummarySchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=product.image_url,
        badge=product.badge,
        is_hero=product.is_hero,
        min_price=CurrencyAmount.from_minor(min_minor) if min_minor is not None else None,
    )


def _build_hero_product(product) -> HeroProductSchema:
    min_minor = get_min_price_minor(product)
    return HeroProductSchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=product.image_url,
        badge=product.badge,
        is_hero=product.is_hero,
        hero_order=product.hero_order,
        hero_benefit=product.hero_benefit,
        hero_image_url=product.hero_image_url,
        hero_poster_url=product.hero_poster_url,
        hero_video_url=product.hero_video_url,
        min_price=CurrencyAmount.from_minor(min_minor) if min_minor is not None else None,
    )


def _build_product_detail(product) -> ProductDetailSchema:
    hero = None
    if product.is_hero:
        hero = HeroMetaSchema(
            order=product.hero_order,
            benefit=product.hero_benefit,
            image_url=product.hero_image_url,
            poster_url=product.hero_poster_url,
            video_url=product.hero_video_url,
        )

    variants = [VariantSchema.from_orm_model(v) for v in product.variants]

    return ProductDetailSchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=product.image_url,
        badge=product.badge,
        is_hero=product.is_hero,
        hero=hero,
        variants=variants,
    )


# ── Collections ────────────────────────────────────────────────────────────────


@router.get(
    "/collections",
    response_model=CollectionListResponse,
    summary="List active collections",
    description=(
        "Returns all active collections ordered by display_order. "
        "Inactive collections are excluded."
    ),
)
def list_collections(db: Session = Depends(get_db)) -> CollectionListResponse:
    collections = get_active_collections(db)
    return CollectionListResponse(
        collections=[
            CollectionSchema(
                id=c.id,
                slug=c.slug,
                name=c.name,
                description=c.description,
                image_url=c.image_url,
                display_order=c.display_order,
            )
            for c in collections
        ],
        total=len(collections),
    )


# ── Products ───────────────────────────────────────────────────────────────────


@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="List active products",
    description=(
        "Returns paginated active products. "
        "Filter by collection_id to get products for a specific collection. "
        "Inactive products and variants are excluded. "
        "Prices reflect the lowest active variant price."
    ),
)
def list_products(
    db: Session = Depends(get_db),
    collection_id: Optional[str] = Query(
        default=None,
        description="Filter by collection ID (e.g. 'essentials').",
    ),
    page: int = Query(default=1, ge=1, description="Page number, 1-indexed."),
    page_size: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Results per page. Maximum {MAX_PAGE_SIZE}.",
    ),
) -> ProductListResponse:
    products, total = get_active_products(
        db, collection_id=collection_id, page=page, page_size=page_size
    )
    return ProductListResponse(
        products=[_build_product_summary(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        collection_id=collection_id,
    )


@router.get(
    "/products/hero",
    response_model=list[HeroProductSchema],
    summary="List hero products",
    description=(
        "Returns active products flagged for the homepage hero carousel, "
        "ordered by hero_order. Returns an empty list if none are configured. "
        "The frontend must handle the empty-hero case gracefully."
    ),
)
def list_hero_products(db: Session = Depends(get_db)) -> list[HeroProductSchema]:
    products = get_hero_products(db)
    return [_build_hero_product(p) for p in products]


@router.get(
    "/products/{slug}",
    response_model=ProductDetailSchema,
    summary="Get product detail",
    description=(
        "Returns full product detail including all active variants with "
        "availability and price. "
        "Returns 404 for unknown or inactive slugs."
    ),
    responses={
        404: {"description": "Product not found or inactive."},
    },
)
def get_product(slug: str, db: Session = Depends(get_db)) -> ProductDetailSchema:
    product = get_product_by_slug(db, slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _build_product_detail(product)
