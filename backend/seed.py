"""
seed.py — Development data seed script for AlphaZee.

Seeds the database with the sample catalog that was previously maintained as
static JavaScript mock data (frontend/src/data/products.js and collections.js).

Rules enforced:
- Refuses to run against a production database (APP_ENV=production).
- Idempotent: running repeatedly does NOT duplicate records.
- Does NOT overwrite edited product data on subsequent runs (checks existence
  before inserting; skips if the record already exists).
- Creates only valid sample variants that represent actual combinations.
- Refuses to seed if the database schema (tables) does not exist — run
  `alembic upgrade head` first.

Usage (from backend/ directory, with .venv active):
    python seed.py

Price encoding:
    All prices are stored in PKR minor units (paisas).
    PKR 3,450  →  345000 paisas
    PKR 6,800  →  680000 paisas
    etc.
"""

from __future__ import annotations

import sys

from sqlalchemy import inspect as sa_inspect, text

from app.config import settings
from app.database import SessionLocal
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant


# ── Helpers ────────────────────────────────────────────────────────────────────


def pkr(amount: int) -> int:
    """Convert whole PKR to minor units (paisas). PKR 3,450 → 345000."""
    return amount * 100


def make_sku(product_id: str, size: str | None, color: str | None) -> str:
    """Generate a deterministic SKU from product + size + color."""
    parts = [product_id]
    if size:
        parts.append(size.upper().replace(" ", "-"))
    if color:
        parts.append(color.upper().replace(" ", "-"))
    return "-".join(parts)


def upsert_collection(db, data: dict) -> None:
    """Insert a collection if it doesn't exist. Skip (don't overwrite) if it does."""
    existing = db.get(Collection, data["id"])
    if existing:
        print(f"  [skip] Collection {data['id']!r} already exists.")
        return
    db.add(Collection(**data))
    print(f"  [insert] Collection {data['id']!r}")


def upsert_product(db, data: dict) -> None:
    """Insert a product if it doesn't exist. Skip (don't overwrite) if it does."""
    existing = db.get(Product, data["id"])
    if existing:
        print(f"  [skip] Product {data['id']!r} already exists.")
        return
    db.add(Product(**data))
    print(f"  [insert] Product {data['id']!r}")


def upsert_variant(db, data: dict) -> None:
    """Insert a variant by SKU if it doesn't exist."""
    from sqlalchemy import select

    existing = db.scalars(
        select(Variant).where(Variant.sku == data["sku"])
    ).first()
    if existing:
        print(f"    [skip] Variant {data['sku']!r} already exists.")
        return
    db.add(Variant(**data))
    print(f"    [insert] Variant {data['sku']!r}")


# ── Seed data ──────────────────────────────────────────────────────────────────

COLLECTIONS = [
    {
        "id": "essentials",
        "slug": "essentials",
        "name": "Minimalist Essentials",
        "description": "Everyday premium tees, heavyweight hoodies, and structured basics.",
        "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80",
        "is_active": True,
        "display_order": 0,
    },
    {
        "id": "streetwear",
        "slug": "streetwear",
        "name": "Urban Streetwear",
        "description": "Relaxed silhouettes, drop-shoulder cuts, and contemporary fits.",
        "image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80",
        "is_active": True,
        "display_order": 1,
    },
    {
        "id": "accessories",
        "slug": "accessories",
        "name": "Curated Accessories",
        "description": "Minimal caps, canvas totes, and functional everyday carry.",
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80",
        "is_active": True,
        "display_order": 2,
    },
]

# Each product entry: (product_dict, variants_list)
# Variants use (size, color, price_pkr) tuples.
PRODUCTS: list[tuple[dict, list[tuple[str | None, str | None, int]]]] = [
    (
        {
            "id": "prod-heavyweight-tee",
            "slug": "heavyweight-boxy-tee",
            "title": "Heavyweight Boxy Tee",
            "description": "Custom relaxed fit, 280 GSM 100% combed cotton, reinforced collar stitch that maintains shape after washing.",
            "collection_id": "essentials",
            "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80",
            "badge": "Core Basic",
            "is_active": True,
            "is_hero": True,
            "hero_order": 0,
            "hero_benefit": "Crafted from 280 GSM combed cotton with an architectural, structured drape.",
            "hero_image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=1000&q=85",
            "hero_poster_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=1200&q=80",
            "hero_video_url": "https://assets.mixkit.co/videos/preview/mixkit-young-man-in-a-white-t-shirt-smiling-41477-large.mp4",
        },
        [
            ("S",  "Chalk White",  3450),
            ("M",  "Chalk White",  3450),
            ("L",  "Chalk White",  3450),
            ("XL", "Chalk White",  3450),
            ("S",  "Washed Black", 3450),
            ("M",  "Washed Black", 3450),
            ("L",  "Washed Black", 3450),
            ("XL", "Washed Black", 3450),
            ("S",  "Pine Green",   3450),
            ("M",  "Pine Green",   3450),
            ("L",  "Pine Green",   3450),
            ("XL", "Pine Green",   3450),
        ],
    ),
    (
        {
            "id": "prod-hoodie-stone",
            "slug": "relaxed-fleece-hoodie",
            "title": "Relaxed Fleece Hoodie",
            "description": "420 GSM custom milled French Terry, oversized drop shoulder cut, kangaroo pocket with hidden stash slot.",
            "collection_id": "streetwear",
            "image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80",
            "badge": "Heavyweight",
            "is_active": True,
            "is_hero": True,
            "hero_order": 1,
            "hero_benefit": "Double-layered hood with brushed 420 GSM French Terry for effortless warmth.",
            "hero_image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1000&q=85",
            "hero_poster_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=80",
            "hero_video_url": "https://assets.mixkit.co/videos/preview/mixkit-man-dancing-under-the-sun-42861-large.mp4",
        },
        [
            ("S",  "Stone Grey", 6800),
            ("M",  "Stone Grey", 6800),
            ("L",  "Stone Grey", 6800),
            ("XL", "Stone Grey", 6800),
            ("S",  "Midnight",   6800),
            ("M",  "Midnight",   6800),
            ("L",  "Midnight",   6800),
            ("XL", "Midnight",   6800),
            ("S",  "Olive",      6800),
            ("M",  "Olive",      6800),
            ("L",  "Olive",      6800),
            ("XL", "Olive",      6800),
        ],
    ),
    (
        {
            "id": "prod-oversized-sweatshirt",
            "slug": "minimalist-crewneck",
            "title": "Minimalist Crewneck",
            "description": "Ultra-soft interior, relaxed silhouette, reinforced rib knit hem and collar.",
            "collection_id": "essentials",
            "image_url": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80",
            "badge": "Essential",
            "is_active": True,
            "is_hero": True,
            "hero_order": 2,
            "hero_benefit": "Refined raglan sleeves and ribbed cuffs designed for clean, tailored layering.",
            "hero_image_url": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=1000&q=85",
            "hero_poster_url": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=1200&q=80",
            "hero_video_url": "https://assets.mixkit.co/videos/preview/mixkit-close-up-of-a-man-wearing-a-dark-sweater-42845-large.mp4",
        },
        [
            ("S", "Forest Green", 5200),
            ("M", "Forest Green", 5200),
            ("L", "Forest Green", 5200),
            ("S", "Oatmeal",      5200),
            ("M", "Oatmeal",      5200),
            ("L", "Oatmeal",      5200),
        ],
    ),
    (
        {
            "id": "prod-canvas-tote",
            "slug": "heavy-duck-canvas-tote",
            "title": "Heavy Duck Canvas Tote",
            "description": "16 oz industrial cotton duck canvas, interior organizer pocket, reinforced cross-stitched handles.",
            "collection_id": "accessories",
            "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80",
            "badge": "Utility",
            "is_active": True,
            "is_hero": False,
        },
        # Single "no option" variant — one size, one color
        [(None, None, 2400)],
    ),
    (
        {
            "id": "prod-cargo-pants",
            "slug": "structured-ripstop-trousers",
            "title": "Structured Ripstop Trousers",
            "description": "Military-grade ripstop fabric with adjustable ankle cinches and ergonomic knee articulation.",
            "collection_id": "streetwear",
            "image_url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=800&q=80",
            "badge": "Durable",
            "is_active": True,
            "is_hero": False,
        },
        [
            ("30", "Tactical Black", 5900),
            ("32", "Tactical Black", 5900),
            ("34", "Tactical Black", 5900),
            ("36", "Tactical Black", 5900),
            ("30", "Desert Sage",    5900),
            ("32", "Desert Sage",    5900),
            ("34", "Desert Sage",    5900),
            ("36", "Desert Sage",    5900),
        ],
    ),
    (
        {
            "id": "prod-structured-cap",
            "slug": "unstructured-6-panel-cap",
            "title": "Unstructured 6-Panel Cap",
            "description": "Low-profile washed cotton twill with brass buckle strapback adjustment.",
            "collection_id": "accessories",
            "image_url": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=800&q=80",
            "badge": "Classic",
            "is_active": True,
            "is_hero": False,
        },
        # Cap: color only, no size
        [(None, "Washed Black", 1850),
         (None, "Olive Green",  1850),
         (None, "Sand",         1850)],
    ),
    (
        {
            "id": "prod-waffle-knit-longsleeve",
            "slug": "thermal-waffle-knit-longsleeve",
            "title": "Thermal Waffle Knit Longsleeve",
            "description": "300 GSM breathable textured thermal knit. Engineered for comfortable insulation.",
            "collection_id": "essentials",
            "image_url": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=800&q=80",
            "badge": "Layering",
            "is_active": True,
            "is_hero": False,
        },
        [
            ("S",  "Off-White", 4200),
            ("M",  "Off-White", 4200),
            ("L",  "Off-White", 4200),
            ("XL", "Off-White", 4200),
            ("S",  "Charcoal",  4200),
            ("M",  "Charcoal",  4200),
            ("L",  "Charcoal",  4200),
            ("XL", "Charcoal",  4200),
        ],
    ),
    (
        {
            "id": "prod-everyday-socks",
            "slug": "cushioned-ribbed-crew-socks-3-pack",
            "title": "Cushioned Ribbed Crew Socks (3-Pack)",
            "description": "Arch compression support, reinforced heel/toe padding, combed organic cotton blend.",
            "collection_id": "accessories",
            "image_url": "https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=800&q=80",
            "badge": "Essentials",
            "is_active": True,
            "is_hero": False,
        },
        # One size, no color option
        [(None, None, 1450)],
    ),
]


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    # ── Production guard ──────────────────────────────────────────────────────
    if settings.is_production:
        print(
            "ERROR: Refusing to seed a production database.\n"
            "       Set APP_ENV=development to run the seed script."
        )
        sys.exit(1)

    db_host = settings.database_url.split("@")[-1]
    print(f"[seed] Environment : {settings.app_env}")
    print(f"[seed] Database    : {db_host}")

    db = SessionLocal()
    try:
        # ── Schema check ──────────────────────────────────────────────────────
        inspector = sa_inspect(db.bind)
        required_tables = {"collections", "products", "variants"}
        existing_tables = set(inspector.get_table_names())
        missing = required_tables - existing_tables
        if missing:
            print(
                f"\nERROR: Required tables missing: {missing}\n"
                "       Run `alembic upgrade head` before seeding."
            )
            sys.exit(1)

        print("\n── Collections ──────────────────────────────────────────────")
        for col_data in COLLECTIONS:
            upsert_collection(db, col_data)
        db.flush()

        print("\n── Products & Variants ──────────────────────────────────────")
        for prod_data, variant_specs in PRODUCTS:
            upsert_product(db, prod_data)
            db.flush()

            for size, color, price_pkr_val in variant_specs:
                sku = make_sku(prod_data["id"], size, color)
                upsert_variant(
                    db,
                    {
                        "sku": sku,
                        "product_id": prod_data["id"],
                        "size": size,
                        "color": color,
                        "price_minor": pkr(price_pkr_val),
                        "is_active": True,
                        "availability": AvailabilityStatus.AVAILABLE,
                    },
                )

        db.commit()
        print("\n[seed] Done — all records committed.")

    except Exception as exc:
        db.rollback()
        print(f"\n[seed] ERROR — rolling back: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
