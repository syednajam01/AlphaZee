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

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
    get_product_by_id,
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

from app.queries.public_media import product_media, primary_alt, storefront_urls
from app.queries.catalog_stock import public_availability


def uncached_catalog(response: Response):
    response.headers['Cache-Control'] = 'no-store'


router = APIRouter(tags=["catalog"], dependencies=[Depends(uncached_catalog)])


def purchase_state(product, availability):
    states = [availability.get(v.id, 'unknown') for v in product.variants if v.is_active]
    return 'available' if 'available' in states else ('unknown' if 'unknown' in states else 'unavailable')


# ── Helpers ────────────────────────────────────────────────────────────────────


def _build_product_summary(product, availability=None) -> ProductSummarySchema:
    min_minor = get_min_price_minor(product)
    return ProductSummarySchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=storefront_urls(product)['image_url'],
        badge=product.badge,
        is_hero=product.is_hero,
        min_price=CurrencyAmount.from_minor(min_minor) if min_minor is not None else None,
        image_alt=primary_alt(product),
        availability=purchase_state(product, availability or {}),
    )


def _build_hero_product(product, availability=None) -> HeroProductSchema:
    min_minor = get_min_price_minor(product)
    return HeroProductSchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=storefront_urls(product)['image_url'],
        badge=product.badge,
        is_hero=product.is_hero,
        hero_order=product.hero_order,
        hero_benefit=product.hero_benefit,
        hero_image_url=storefront_urls(product)['hero_image_url'],
        hero_poster_url=storefront_urls(product)['hero_poster_url'],
        hero_video_url=storefront_urls(product)['hero_video_url'],
        min_price=CurrencyAmount.from_minor(min_minor) if min_minor is not None else None,
        image_alt=primary_alt(product),
        availability=purchase_state(product, availability or {}),
    )


def _build_product_detail(product, db=None) -> ProductDetailSchema:
    hero = None
    if product.is_hero:
        hero = HeroMetaSchema(
            order=product.hero_order,
            benefit=product.hero_benefit,
            image_url=storefront_urls(product)['hero_image_url'],
            poster_url=storefront_urls(product)['hero_poster_url'],
            video_url=storefront_urls(product)['hero_video_url'],
        )

    variants = [VariantSchema.from_orm_model(v) for v in sorted(product.variants, key=lambda row: row.id) if v.is_active]
    if db is not None:
        from app.queries.catalog_stock import public_availability
        availability = public_availability(db, product.variants)
        for variant in variants: variant.availability = availability[variant.id]

    return ProductDetailSchema(
        id=product.id,
        slug=product.slug,
        title=product.title,
        description=product.description,
        collection_id=product.collection_id,
        image_url=storefront_urls(product)['image_url'],
        badge=product.badge,
        is_hero=product.is_hero,
        hero=hero,
        short_description=product.short_description,
        material=product.material,
        care=product.care,
        sizing=product.sizing,
        variants=variants,
        media=product_media(product),
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
    availability = public_availability(db, [v for p in products for v in p.variants if v.is_active])
    return ProductListResponse(
        products=[_build_product_summary(p, availability) for p in products],
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
    availability = public_availability(db, [v for p in products for v in p.variants if v.is_active])
    return [_build_hero_product(p, availability) for p in products]


@router.get('/catalog/products/{product_id}', response_model=ProductDetailSchema)
def product_by_identity(product_id: str, db: Session = Depends(get_db)):
    product = get_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(404, 'Product not found')
    return _build_product_detail(product, db)


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
    return _build_product_detail(product, db)
