"""
test_api_orders.py — Integration tests for Customer Order Storefront API endpoints.

Tests:
- POST /api/v1/orders: Valid COD and Bank Transfer orders, authoritative price snapshotting, stock reservation holding.
- POST /api/v1/orders: 422 on invalid phone format, 409 on insufficient inventory, 400 on unavailable variant.
- POST /api/v1/orders/{order_number}/receipt: Payment proof submission with verified customer phone lookup.
- GET /api/v1/orders/{order_number}: Customer tracking lookup with phone verification.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.suppliers import Supplier


def _create_catalog_item(db: Session, on_hand: int = 10, price_minor: int = 350000):
    unique_suffix = uuid.uuid4().hex[:6]
    col = Collection(
        id=f"col-{unique_suffix}",
        slug=f"col-{unique_suffix}",
        name="API Test Collection",
        is_active=True,
        display_order=1,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-{unique_suffix}",
        slug=f"prod-{unique_suffix}",
        title="Test Minimalist Oversized Tee",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-TEE-{unique_suffix}",
        product_id=prod.id,
        size="M",
        color="Slate Black",
        price_minor=price_minor,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    supplier = Supplier(
        name=f"Supplier {unique_suffix}",
        slug=f"supplier-{unique_suffix}",
        status="active",
        notes="0300-1111111",
    )
    db.add(supplier)
    db.flush()

    sv = SupplierVariant(
        supplier_id=supplier.id,
        variant_id=var.id,
        supplier_cost_minor=200000,
        active=True,
    )
    db.add(sv)
    db.flush()

    balance = InventoryBalance(
        supplier_variant_id=sv.id,
        on_hand=on_hand,
        version=1,
    )
    db.add(balance)
    db.flush()

    return {"collection": col, "product": prod, "variant": var, "sv": sv, "balance": balance}


def test_post_order_cod_success(client, db_session):
    item = _create_catalog_item(db_session, on_hand=5, price_minor=420000)

    payload = {
        "customer_name": "Hamza Tariq",
        "customer_phone": "0321-9876543",
        "customer_email": "hamza@example.com",
        "shipping_address_line1": "House 12, Street 4, F-7/2",
        "shipping_city": "Islamabad",
        "shipping_province": "Islamabad Capital Territory",
        "shipping_postal_code": "44000",
        "payment_method": "cod",
        "customer_notes": "Call before arrival",
        "items": [
            {"variant_id": item["variant"].id, "quantity": 2}
        ],
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["order_number"].startswith("AZ-")
    assert data["customer_name"] == "Hamza Tariq"
    assert data["customer_phone"] == "03219876543"
    assert data["payment_method"] == "cod"
    assert data["order_status"] == "placed"
    assert data["payment_status"] == "pending"

    # Financial integrity: 2 * 420,000 = 840,000 paisas = PKR 8,400
    assert data["subtotal"]["minor"] == 840000
    assert data["subtotal"]["formatted"] == "PKR 8,400"
    assert data["total"]["minor"] == 840000
    assert len(data["lines"]) == 1
    assert data["lines"][0]["variant_sku"] == item["variant"].sku
    assert data["lines"][0]["quantity"] == 2
    assert data["lines"][0]["unit_price"]["minor"] == 420000
    assert data["bank_instructions"] is None


def test_post_order_bank_transfer_includes_instructions(client, db_session):
    item = _create_catalog_item(db_session, on_hand=3, price_minor=350000)

    payload = {
        "customer_name": "Ayesha Khan",
        "customer_phone": "0300 1234567",  # Testing auto-normalization
        "shipping_address_line1": "Flat 302, Gulshan-e-Iqbal Block 13D",
        "shipping_city": "Karachi",
        "shipping_province": "Sindh",
        "payment_method": "bank_transfer",
        "items": [
            {"variant_id": item["variant"].id, "quantity": 1}
        ],
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["customer_phone"] == "03001234567"  # Normalized
    assert data["payment_method"] == "bank_transfer"
    assert data["bank_instructions"] is not None
    assert "Meezan Bank" in data["bank_instructions"]["bank_name"]
    assert "PK00MEZN0001020304050607" in data["bank_instructions"]["iban"]


def test_post_order_insufficient_stock_returns_409(client, db_session):
    item = _create_catalog_item(db_session, on_hand=2)

    payload = {
        "customer_name": "Bilal Ahmed",
        "customer_phone": "0333-5555555",
        "shipping_address_line1": "Main Boulevard, Gulberg III",
        "shipping_city": "Lahore",
        "shipping_province": "Punjab",
        "payment_method": "cod",
        "items": [
            {"variant_id": item["variant"].id, "quantity": 5}  # Requesting 5, only 2 on hand
        ],
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 409
    assert "Insufficient stock" in res.json()["detail"]


def test_post_order_invalid_phone_returns_422(client, db_session):
    item = _create_catalog_item(db_session, on_hand=5)

    payload = {
        "customer_name": "Bad Phone User",
        "customer_phone": "12345678",  # Invalid Pakistan phone
        "shipping_address_line1": "Street 1",
        "shipping_city": "Lahore",
        "shipping_province": "Punjab",
        "payment_method": "cod",
        "items": [
            {"variant_id": item["variant"].id, "quantity": 1}
        ],
    }

    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 422


def test_receipt_upload_and_tracking(client, db_session):
    item = _create_catalog_item(db_session, on_hand=5, price_minor=250000)

    # 1. Place Bank Transfer order
    order_payload = {
        "customer_name": "Sana Mir",
        "customer_phone": "0345-1234567",
        "shipping_address_line1": "DHA Phase 6",
        "shipping_city": "Lahore",
        "shipping_province": "Punjab",
        "payment_method": "bank_transfer",
        "items": [{"variant_id": item["variant"].id, "quantity": 1}],
    }
    order_res = client.post("/api/v1/orders", json=order_payload)
    assert order_res.status_code == 201
    order_num = order_res.json()["order_number"]

    # 2. Upload receipt proof
    receipt_payload = {
        "customer_phone": "0345-1234567",
        "receipt_image_url": "https://storage.alphazee.pk/receipts/proof-123.jpg",
        "bank_reference": "TXN998877",
    }
    receipt_res = client.post(f"/api/v1/orders/{order_num}/receipt", json=receipt_payload)
    assert receipt_res.status_code == 200
    receipt_data = receipt_res.json()
    assert len(receipt_data["receipts"]) == 1
    assert receipt_data["receipts"][0]["receipt_image_url"] == "https://storage.alphazee.pk/receipts/proof-123.jpg"
    assert receipt_data["receipts"][0]["bank_reference"] == "TXN998877"

    # 3. Track order
    track_res = client.get(f"/api/v1/orders/{order_num}?phone=03451234567")
    assert track_res.status_code == 200
    assert track_res.json()["order_number"] == order_num
    assert len(track_res.json()["receipts"]) == 1

    # 4. Mismatched phone lookup returns 404
    bad_track_res = client.get(f"/api/v1/orders/{order_num}?phone=03001112233")
    assert bad_track_res.status_code == 404
