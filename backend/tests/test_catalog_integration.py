"""
test_catalog_integration.py — Disposable PostgreSQL integration tests for AlphaZee catalog.

Tests database engine-level constraints, indexes, enums, and foreign key rules:
1. Enum handling: availability_status PostgreSQL enum values.
2. PostgreSQL 16+ NULLS NOT DISTINCT unique constraint on variants(product_id, size, color).
3. Non-negative price CHECK constraint (price_minor >= 0).
4. Foreign key restrictions: Collection -> Product (ON DELETE RESTRICT).
5. Foreign key cascades: Product -> Variant (ON DELETE CASCADE).
6. Unique constraints on slugs and SKUs.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant


def _create_collection(db, id_slug: str = "test-col") -> Collection:
    col = Collection(
        id=id_slug,
        slug=id_slug,
        name=f"Collection {id_slug}",
        description="Test description",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()
    return col


def _create_product(db, col_id: str, id_slug: str = "test-prod") -> Product:
    prod = Product(
        id=id_slug,
        slug=id_slug,
        title=f"Product {id_slug}",
        collection_id=col_id,
        is_active=True,
        is_hero=False,
    )
    db.add(prod)
    db.flush()
    return prod


class TestCatalogDatabaseConstraints:
    def test_nulls_not_distinct_unique_constraint(self, db_session):
        """PostgreSQL 16+ NULLS NOT DISTINCT must prevent duplicate (prod, NULL, NULL) variants."""
        col = _create_collection(db_session, "col-nulls")
        prod = _create_product(db_session, col.id, "prod-nulls")

        v1 = Variant(
            sku="SKU-NULL-1",
            product_id=prod.id,
            size=None,
            color=None,
            price_minor=345000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v1)
        db_session.flush()

        v2 = Variant(
            sku="SKU-NULL-2",
            product_id=prod.id,
            size=None,
            color=None,
            price_minor=345000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()

        assert "uq_variant_product_size_color" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()

    def test_distinct_options_permitted(self, db_session):
        """Variants with different size/color combinations are permitted."""
        col = _create_collection(db_session, "col-opts")
        prod = _create_product(db_session, col.id, "prod-opts")

        v_s = Variant(
            sku="SKU-OPT-S",
            product_id=prod.id,
            size="S",
            color="Black",
            price_minor=345000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        v_m = Variant(
            sku="SKU-OPT-M",
            product_id=prod.id,
            size="M",
            color="Black",
            price_minor=345000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add_all([v_s, v_m])
        db_session.flush()

        assert v_s.id is not None
        assert v_m.id is not None

    def test_price_minor_nonnegative_constraint(self, db_session):
        """CHECK constraint ck_variant_price_nonnegative rejects negative prices."""
        col = _create_collection(db_session, "col-price")
        prod = _create_product(db_session, col.id, "prod-price")

        v_neg = Variant(
            sku="SKU-PRICE-NEG",
            product_id=prod.id,
            size=None,
            color=None,
            price_minor=-500,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v_neg)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()

        assert "ck_variant_price_nonnegative" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    def test_price_minor_zero_permitted(self, db_session):
        """Zero price is non-negative and permitted."""
        col = _create_collection(db_session, "col-zero")
        prod = _create_product(db_session, col.id, "prod-zero")

        v_zero = Variant(
            sku="SKU-PRICE-ZERO",
            product_id=prod.id,
            size=None,
            color=None,
            price_minor=0,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v_zero)
        db_session.flush()
        assert v_zero.id is not None

    def test_collection_fk_on_delete_restrict(self, db_session):
        """Deleting a collection with existing products is rejected by ON DELETE RESTRICT."""
        col = _create_collection(db_session, "col-restrict")
        _create_product(db_session, col.id, "prod-restrict")
        assert col.products  # Even loaded children must not be silently orphaned.

        db_session.delete(col)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_product_fk_on_delete_restrict(self, db_session):
        """Catalog lifecycle retains variants instead of destructive product cascades."""
        col = _create_collection(db_session, "col-cascade")
        prod = _create_product(db_session, col.id, "prod-cascade")

        v = Variant(
            sku="SKU-CASCADE",
            product_id=prod.id,
            size="L",
            color="Navy",
            price_minor=450000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v)
        db_session.flush()
        v_id = v.id

        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                db_session.delete(prod)
                db_session.flush()

        loaded_variant = db_session.get(Variant, v_id)
        assert loaded_variant is not None

    def test_duplicate_sku_rejected(self, db_session):
        """Variant SKU uniqueness is enforced across all products."""
        col = _create_collection(db_session, "col-sku")
        p1 = _create_product(db_session, col.id, "prod-sku-1")
        p2 = _create_product(db_session, col.id, "prod-sku-2")

        v1 = Variant(
            sku="GLOBAL-UNIQUE-SKU",
            product_id=p1.id,
            size="S",
            color=None,
            price_minor=300000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v1)
        db_session.flush()

        v2 = Variant(
            sku="GLOBAL-UNIQUE-SKU",
            product_id=p2.id,
            size="M",
            color=None,
            price_minor=300000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(v2)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_availability_enum_persists_correctly(self, db_session):
        """Enum values AVAILABLE, UNAVAILABLE, and UNKNOWN are stored and loaded accurately."""
        col = _create_collection(db_session, "col-enum")
        prod = _create_product(db_session, col.id, "prod-enum")

        v_avail = Variant(
            sku="SKU-AVAIL-TEST",
            product_id=prod.id,
            size="S",
            color=None,
            price_minor=100000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        v_unavail = Variant(
            sku="SKU-UNAVAIL-TEST",
            product_id=prod.id,
            size="M",
            color=None,
            price_minor=100000,
            is_active=True,
            availability=AvailabilityStatus.UNAVAILABLE,
        )
        v_unknown = Variant(
            sku="SKU-UNKNOWN-TEST",
            product_id=prod.id,
            size="L",
            color=None,
            price_minor=100000,
            is_active=True,
            availability=AvailabilityStatus.UNKNOWN,
        )
        db_session.add_all([v_avail, v_unavail, v_unknown])
        db_session.flush()

        db_session.expire_all()

        loaded_a = db_session.scalars(select(Variant).where(Variant.sku == "SKU-AVAIL-TEST")).one()
        loaded_u = db_session.scalars(select(Variant).where(Variant.sku == "SKU-UNAVAIL-TEST")).one()
        loaded_k = db_session.scalars(select(Variant).where(Variant.sku == "SKU-UNKNOWN-TEST")).one()

        assert loaded_a.availability == AvailabilityStatus.AVAILABLE
        assert loaded_u.availability == AvailabilityStatus.UNAVAILABLE
        assert loaded_k.availability == AvailabilityStatus.UNKNOWN
