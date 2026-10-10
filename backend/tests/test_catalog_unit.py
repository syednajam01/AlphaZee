"""
Unit tests for catalog query compilation, model invariants, and price helpers.

Runs entirely in-memory with NO database connection required.
Validates the requirements from next_target.txt §3, §4, and §6.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from sqlalchemy.dialects import postgresql
from sqlalchemy import Index

from app.models.catalog import Collection, Product, Variant
from app.schemas.catalog import CurrencyAmount
from app.queries.catalog import (
    get_active_products,
    get_hero_products,
    get_product_by_slug,
    get_min_price_minor,
)


def test_get_active_products_compilation():
    """Verify get_active_products compiles with collection join, active filters, and stable sort."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = 10
    mock_db.scalars.return_value.all.return_value = []

    products, total = get_active_products(mock_db, collection_id="essentials", page=2, page_size=15)

    assert total == 10
    assert products == []

    # 1. Inspect data query
    data_stmt = mock_db.scalars.call_args[0][0]
    sql_data = str(data_stmt.compile(dialect=postgresql.dialect()))

    assert "JOIN collections ON products.collection_id = collections.id" in sql_data
    assert "collections.is_active IS true" in sql_data
    assert "products.is_active IS true" in sql_data
    assert "products.collection_id = %(collection_id_1)s" in sql_data
    assert "ORDER BY products.created_at DESC, products.id ASC" in sql_data
    assert "LIMIT %(param_1)s OFFSET %(param_2)s" in sql_data

    # 2. Inspect count query
    count_stmt = mock_db.scalar.call_args[0][0]
    sql_count = str(count_stmt.compile(dialect=postgresql.dialect()))

    assert "count(*)" in sql_count
    assert "JOIN collections ON products.collection_id = collections.id" in sql_count
    assert "collections.is_active IS true" in sql_count
    assert "products.is_active IS true" in sql_count


def test_get_hero_products_compilation():
    """Verify get_hero_products compiles with collection join, is_hero filter, and nulls-last ordering."""
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    get_hero_products(mock_db)

    hero_stmt = mock_db.scalars.call_args[0][0]
    sql_hero = str(hero_stmt.compile(dialect=postgresql.dialect()))

    assert "JOIN collections ON products.collection_id = collections.id" in sql_hero
    assert "products.is_hero IS true" in sql_hero
    assert "collections.is_active IS true" in sql_hero
    assert "ORDER BY products.hero_order ASC NULLS LAST, products.id ASC" in sql_hero


def test_get_product_by_slug_compilation():
    """Verify get_product_by_slug compiles with collection join and slug filter."""
    mock_db = MagicMock()
    mock_db.scalars.return_value.first.return_value = None

    get_product_by_slug(mock_db, slug="heavyweight-tee")

    slug_stmt = mock_db.scalars.call_args[0][0]
    sql_slug = str(slug_stmt.compile(dialect=postgresql.dialect()))

    assert "JOIN collections ON products.collection_id = collections.id" in sql_slug
    assert "products.slug = %(slug_1)s" in sql_slug
    assert "collections.is_active IS true" in sql_slug
    assert "products.is_active IS true" in sql_slug


def test_variant_uniqueness_index_definition():
    """Verify Variant has NULLS NOT DISTINCT unique index on (product_id, size, color)."""
    indices = [arg for arg in Variant.__table_args__ if isinstance(arg, Index)]
    target_idx = next((idx for idx in indices if idx.name == "uq_variant_product_size_color"), None)

    assert target_idx is not None, "uq_variant_product_size_color Index not found"
    assert target_idx.unique is True
    assert target_idx.dialect_options["postgresql"]["nulls_not_distinct"] is True


def test_collection_cascade_alignment():
    """Verify Collection.products does not cascade deletes to Products (aligns with RESTRICT FK)."""
    cascade = Collection.products.property.cascade
    assert cascade.delete_orphan is False
    assert Collection.products.property.passive_deletes is True


def test_variant_option_normalization():
    """Verify Variant.normalize_option trims whitespace and converts empty strings to None."""
    assert Variant.normalize_option(None) is None
    assert Variant.normalize_option("") is None
    assert Variant.normalize_option("   ") is None
    assert Variant.normalize_option("  Large  ") == "Large"
    assert Variant.normalize_option("\tOatmeal\n") == "Oatmeal"

    # Test automatic normalization via SQLAlchemy @validates on init and assignment
    v = Variant(size="  M  ", color="   ")
    assert v.size == "M"
    assert v.color is None

    v.size = "   "
    v.color = "  Chalk White  "
    assert v.size is None
    assert v.color == "Chalk White"


def test_variant_price_helpers():
    """Verify price_pkr integer division and get_min_price_minor."""
    v1 = Variant(price_minor=345000, is_active=True)
    assert v1.price_pkr == 3450

    # Documented truncation limitation
    v2 = Variant(price_minor=345099, is_active=True)
    assert v2.price_pkr == 3450

    prod = Product(variants=[v1, v2])
    assert get_min_price_minor(prod) == 345000


def test_currency_amount_formatting():
    """Verify CurrencyAmount.from_minor formats whole rupees and fractional rupees properly."""
    # Whole rupees without decimal suffix
    ca_whole = CurrencyAmount.from_minor(345000)
    assert ca_whole.minor == 345000
    assert ca_whole.pkr == 3450
    assert ca_whole.formatted == "PKR 3,450"

    # Fractional rupees with exact 2-decimal precision
    ca_fraction = CurrencyAmount.from_minor(345050)
    assert ca_fraction.minor == 345050
    assert ca_fraction.pkr == 3450
    assert ca_fraction.formatted == "PKR 3,450.50"

    ca_small = CurrencyAmount.from_minor(50)
    assert ca_small.minor == 50
    assert ca_small.pkr == 0
    assert ca_small.formatted == "PKR 0.50"

    ca_zero = CurrencyAmount.from_minor(0)
    assert ca_zero.minor == 0
    assert ca_zero.pkr == 0
    assert ca_zero.formatted == "PKR 0"


def test_hero_product_schema_and_builder():
    """Verify HeroProductSchema serialization and _build_hero_product preserves presentation media & price."""
    from app.schemas.catalog import HeroProductSchema
    from app.api.v1.catalog import _build_hero_product

    v = Variant(id="var_hero_1", sku="AZ-OVS-M-BLK", price_minor=395000, is_active=True)
    prod = Product(
        id="prod_hero_1",
        slug="oversized-heavyweight-tee",
        title="Oversized Heavyweight Tee",
        description="Premium 280 GSM cotton.",
        collection_id="essentials",
        image_url="https://cdn.alphazee.pk/tee-thumb.jpg",
        badge="Best Seller",
        is_hero=True,
        hero_order=1,
        hero_benefit="Engineered heavyweight drape",
        hero_image_url="https://cdn.alphazee.pk/tee-hero.jpg",
        hero_poster_url="https://cdn.alphazee.pk/tee-poster.jpg",
        hero_video_url="https://cdn.alphazee.pk/tee-video.mp4",
        variants=[v],
    )

    schema = _build_hero_product(prod)
    assert isinstance(schema, HeroProductSchema)
    assert schema.id == "prod_hero_1"
    assert schema.slug == "oversized-heavyweight-tee"
    assert schema.is_hero is True
    assert schema.hero_order == 1
    assert schema.hero_benefit == "Engineered heavyweight drape"
    assert schema.hero_poster_url == "https://cdn.alphazee.pk/tee-poster.jpg"
    assert schema.hero_video_url == "https://cdn.alphazee.pk/tee-video.mp4"
    assert schema.min_price is not None
    assert schema.min_price.minor == 395000
    assert schema.min_price.formatted == "PKR 3,950"
