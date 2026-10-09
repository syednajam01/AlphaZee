"""
Tests for catalog API endpoints — collections, products, product detail.

Covers spec §10 verification requirements:
- Listing, filtering, pagination, and detail endpoints work.
- Inactive records are excluded.
- Unknown products return 404.
- Invalid prices and duplicate variants are rejected (model constraint tests).
"""

from __future__ import annotations

import pytest

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant


# ── Fixtures ───────────────────────────────────────────────────────────────────


def make_collection(db, **kwargs) -> Collection:
    defaults = {
        "id": "test-col",
        "slug": "test-col",
        "name": "Test Collection",
        "is_active": True,
        "display_order": 0,
    }
    defaults.update(kwargs)
    c = Collection(**defaults)
    db.add(c)
    db.flush()
    return c


def make_product(db, collection_id: str, **kwargs) -> Product:
    defaults = {
        "id": "test-prod",
        "slug": "test-prod",
        "title": "Test Product",
        "collection_id": collection_id,
        "is_active": True,
        "is_hero": False,
    }
    defaults.update(kwargs)
    p = Product(**defaults)
    db.add(p)
    db.flush()
    return p


def make_variant(db, product_id: str, sku: str, price_minor: int = 345000, **kwargs) -> Variant:
    defaults = {
        "sku": sku,
        "product_id": product_id,
        "price_minor": price_minor,
        "is_active": True,
        "availability": AvailabilityStatus.AVAILABLE,
    }
    defaults.update(kwargs)
    v = Variant(**defaults)
    db.add(v)
    db.flush()
    return v


# ── Collection tests ───────────────────────────────────────────────────────────


class TestCollections:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/v1/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["collections"] == []
        assert data["total"] == 0

    def test_active_collection_returned(self, client, db_session):
        make_collection(db_session)
        resp = client.get("/api/v1/collections")
        assert resp.status_code == 200
        cols = resp.json()["collections"]
        assert len(cols) == 1
        assert cols[0]["slug"] == "test-col"

    def test_inactive_collection_excluded(self, client, db_session):
        make_collection(db_session, id="inactive", slug="inactive", is_active=False)
        resp = client.get("/api/v1/collections")
        assert resp.json()["total"] == 0

    def test_ordered_by_display_order(self, client, db_session):
        make_collection(db_session, id="b", slug="b", name="B", display_order=2)
        make_collection(db_session, id="a", slug="a", name="A", display_order=1)
        cols = client.get("/api/v1/collections").json()["collections"]
        assert cols[0]["id"] == "a"
        assert cols[1]["id"] == "b"


# ── Product listing tests ──────────────────────────────────────────────────────


class TestProductList:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/v1/products")
        assert resp.status_code == 200
        data = resp.json()
        assert data["products"] == []
        assert data["total"] == 0

    def test_active_product_returned(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id)
        make_variant(db_session, prod.id, sku="SKU-001")
        resp = client.get("/api/v1/products")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_inactive_product_excluded(self, client, db_session):
        col = make_collection(db_session)
        make_product(db_session, col.id, id="inactive-p", slug="inactive-p", is_active=False)
        assert client.get("/api/v1/products").json()["total"] == 0

    def test_collection_filter(self, client, db_session):
        col_a = make_collection(db_session, id="col-a", slug="col-a", name="A")
        col_b = make_collection(db_session, id="col-b", slug="col-b", name="B")
        prod_a = make_product(db_session, col_a.id, id="p-a", slug="p-a", title="A")
        make_variant(db_session, prod_a.id, sku="SKU-A")
        prod_b = make_product(db_session, col_b.id, id="p-b", slug="p-b", title="B")
        make_variant(db_session, prod_b.id, sku="SKU-B")

        resp = client.get("/api/v1/products?collection_id=col-a")
        data = resp.json()
        assert data["total"] == 1
        assert data["products"][0]["id"] == "p-a"

    def test_price_in_response(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id)
        make_variant(db_session, prod.id, sku="SKU-PRICE", price_minor=345000)
        products = client.get("/api/v1/products").json()["products"]
        price = products[0]["min_price"]
        assert price["pkr"] == 3450
        assert price["minor"] == 345000
        assert price["currency"] == "PKR"
        assert "3,450" in price["formatted"]

    def test_pagination(self, client, db_session):
        col = make_collection(db_session)
        for i in range(5):
            prod = make_product(
                db_session, col.id,
                id=f"p-{i}", slug=f"p-{i}", title=f"Product {i}"
            )
            make_variant(db_session, prod.id, sku=f"SKU-{i}")

        resp = client.get("/api/v1/products?page=1&page_size=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["products"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


# ── Product detail tests ───────────────────────────────────────────────────────


class TestProductDetail:
    def test_returns_product_by_slug(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id, slug="my-slug")
        make_variant(db_session, prod.id, sku="SKU-DET")
        resp = client.get("/api/v1/products/my-slug")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "my-slug"

    def test_unknown_slug_returns_404(self, client):
        resp = client.get("/api/v1/products/does-not-exist")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Product not found"

    def test_inactive_product_returns_404(self, client, db_session):
        col = make_collection(db_session)
        make_product(db_session, col.id, slug="inactive-slug", is_active=False)
        resp = client.get("/api/v1/products/inactive-slug")
        assert resp.status_code == 404

    def test_inactive_variant_excluded(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id, slug="var-test")
        make_variant(db_session, prod.id, sku="ACTIVE-V", is_active=True)
        make_variant(db_session, prod.id, sku="INACTIVE-V", is_active=False, size="XL")
        resp = client.get("/api/v1/products/var-test")
        variants = resp.json()["variants"]
        assert len(variants) == 1
        assert variants[0]["sku"] == "ACTIVE-V"

    def test_variant_has_availability(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id, slug="avail-test")
        make_variant(
            db_session, prod.id, sku="SKU-AVAIL",
            availability=AvailabilityStatus.AVAILABLE
        )
        variants = client.get("/api/v1/products/avail-test").json()["variants"]
        assert variants[0]["availability"] == "available"

    def test_hero_product_includes_hero_meta(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(
            db_session, col.id,
            id="hero-p", slug="hero-slug",
            is_hero=True,
            hero_order=0,
            hero_benefit="Great benefit",
            hero_video_url="https://example.com/video.mp4",
        )
        make_variant(db_session, prod.id, sku="SKU-HERO")
        detail = client.get("/api/v1/products/hero-slug").json()
        assert detail["is_hero"] is True
        assert detail["hero"]["benefit"] == "Great benefit"
        assert detail["hero"]["video_url"] == "https://example.com/video.mp4"

    def test_non_hero_has_null_hero_meta(self, client, db_session):
        col = make_collection(db_session)
        prod = make_product(db_session, col.id, slug="no-hero", is_hero=False)
        make_variant(db_session, prod.id, sku="SKU-NH")
        detail = client.get("/api/v1/products/no-hero").json()
        assert detail["is_hero"] is False
        assert detail["hero"] is None


# ── Hero endpoint tests ────────────────────────────────────────────────────────


class TestHeroProducts:
    def test_empty_hero_returns_empty_list(self, client):
        resp = client.get("/api/v1/products/hero")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_hero_products_ordered(self, client, db_session):
        col = make_collection(db_session)
        for i in [2, 0, 1]:
            prod = make_product(
                db_session, col.id,
                id=f"hero-{i}", slug=f"hero-{i}",
                is_hero=True, hero_order=i,
            )
            make_variant(db_session, prod.id, sku=f"SKU-H{i}")

        heroes = client.get("/api/v1/products/hero").json()
        orders = [h["slug"].split("-")[-1] for h in heroes]
        assert orders == ["0", "1", "2"]


# ── Constraint tests ───────────────────────────────────────────────────────────


class TestModelConstraints:
    def test_negative_price_rejected(self, db_session):
        col = make_collection(db_session, id="c-neg", slug="c-neg")
        prod = make_product(db_session, col.id, id="p-neg", slug="p-neg")
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            v = Variant(
                sku="BAD-SKU",
                product_id=prod.id,
                price_minor=-1,  # invalid
                is_active=True,
                availability=AvailabilityStatus.AVAILABLE,
            )
            db_session.add(v)
            db_session.flush()

    def test_duplicate_sku_rejected(self, db_session):
        col = make_collection(db_session, id="c-dup", slug="c-dup")
        prod = make_product(db_session, col.id, id="p-dup", slug="p-dup")
        make_variant(db_session, prod.id, sku="DUPE-SKU")

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            make_variant(db_session, prod.id, sku="DUPE-SKU", size="M")

    def test_duplicate_variant_null_options_rejected(self, db_session):
        col = make_collection(db_session, id="c-null", slug="c-null")
        prod = make_product(db_session, col.id, id="p-null", slug="p-null")
        make_variant(db_session, prod.id, sku="SKU-1", size=None, color=None)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            make_variant(db_session, prod.id, sku="SKU-2", size=None, color=None)


def test_variant_normalize_option():
    assert Variant.normalize_option(None) is None
    assert Variant.normalize_option("") is None
    assert Variant.normalize_option("   ") is None
    assert Variant.normalize_option("  Large  ") == "Large"
    assert Variant.normalize_option("Chalk White") == "Chalk White"

