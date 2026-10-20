"""
test_api_admin.py — Integration tests for Owner Administration API endpoints.

Tests:
- GET /api/v1/admin/inventory/summary: Real-time Physical | Held | Available triple calculation.
- POST /api/v1/admin/inventory/adjust: Concurrency-guarded adjustment and 409 Conflict on stale version.
- GET /api/v1/admin/orders: Order listing and status filtering.
- POST /api/v1/admin/orders/{id}/verify-payment: Owner bank fund verification.
- POST /api/v1/admin/orders/{id}/deliver: Delivery completion with inventory decrement.
- POST /api/v1/admin/orders/{id}/cancel: Order cancellation releasing held reservations.
"""

from __future__ import annotations

import uuid
import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from sqlalchemy.orm import Session

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.suppliers import Supplier, UserAccount


def _post_checkout(admin_client, payload):
    from app.services.checkout_attempts import checkout_cookie_name
    assert admin_client.get('/api/v1/orders/checkout-session').status_code == 200
    checkout_cookie = admin_client.cookies.get(checkout_cookie_name())
    assert checkout_cookie
    return admin_client.post('/api/v1/orders', json=payload,
                             headers={'Idempotency-Key': f'chk_{uuid.uuid4().hex}',
                                      'Cookie': f"{admin_client.headers['Cookie']}; {checkout_cookie_name()}={checkout_cookie}"})


def _create_admin_setup(db: Session, on_hand: int = 10):
    unique_suffix = uuid.uuid4().hex[:6]

    # Owner user account
    owner = UserAccount(
        auth_subject=f"auth0|owner-{unique_suffix}",
        display_name="Syed Najam",
        is_active=True,
    )
    db.add(owner)
    db.flush()

    col = Collection(
        id=f"col-adm-{unique_suffix}",
        slug=f"col-adm-{unique_suffix}",
        name="Admin Test Collection",
        is_active=True,
        display_order=1,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-adm-{unique_suffix}",
        slug=f"prod-adm-{unique_suffix}",
        title="Admin Test Tee",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-ADM-{unique_suffix}",
        product_id=prod.id,
        size="XL",
        color="Olive Green",
        price_minor=320000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    supplier = Supplier(
        name=f"Admin Supplier {unique_suffix}",
        slug=f"admin-supplier-{unique_suffix}",
        status="active",
        notes="0300-2222222",
    )
    db.add(supplier)
    db.flush()
    prod.stock_management_source = 'vendor_managed'
    prod.vendor_id = supplier.id

    sv = SupplierVariant(
        supplier_id=supplier.id,
        variant_id=var.id,
        supplier_cost_minor=180000,
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

    return {
        "owner": owner,
        "collection": col,
        "product": prod,
        "variant": var,
        "sv": sv,
        "balance": balance,
    }


def test_admin_inventory_summary_and_adjust(admin_client, db_session):
    setup = _create_admin_setup(db_session, on_hand=10)
    sv_id = setup["sv"].id

    # 1. Fetch summary
    res = admin_client.get("/api/v1/admin/inventory/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_variants"] >= 1
    match = next((item for item in data["items"] if item["supplier_variant_id"] == str(sv_id)), None)
    assert match is not None
    assert match["physical_on_hand"] == 10
    assert match["held_reservations"] == 0
    assert match["available_to_sell"] == 10
    assert match["version"] == 1
    assert match['supplier_id'] == str(setup['sv'].supplier_id)
    assert match['supplier_name'] == setup['sv'].supplier.name

    variants = admin_client.get('/api/v1/admin/catalog/variants')
    assert variants.status_code == 200
    mapped = next(item for item in variants.json() if item['id'] == setup['variant'].id)
    assert mapped['active_supplier_id'] == str(setup['sv'].supplier_id)
    assert mapped['supplier_cost_minor'] == 180000

    # 2. Adjust physical stock (+5 units)
    adjust_payload = {
        "supplier_variant_id": str(sv_id),
        "quantity_delta": 5,
        "expected_version": 1,
        "reason": "supplier_receipt",
        "reference_id": "PO-2026-001",
    }
    adj_res = admin_client.post("/api/v1/admin/inventory/adjust", json=adjust_payload)
    assert adj_res.status_code == 200
    adj_data = adj_res.json()
    assert adj_data["physical_on_hand"] == 15
    assert adj_data["available_to_sell"] == 15
    assert adj_data["version"] == 2

    # 3. Conflict on stale version
    stale_payload = {
        "supplier_variant_id": str(sv_id),
        "quantity_delta": 2,
        "expected_version": 1,  # Stale! Expected is now 2
        "reason": "manual_count",
    }
    stale_res = admin_client.post("/api/v1/admin/inventory/adjust", json=stale_payload)
    assert stale_res.status_code == 409
    assert "modified concurrently" in stale_res.json()["detail"]


def test_admin_order_lifecycle_payment_and_delivery(admin_client, db_session):
    setup = _create_admin_setup(db_session, on_hand=10)
    var = setup["variant"]
    sv_id = setup["sv"].id

    # 1. Place Bank Transfer order for 2 units
    order_payload = {
        "customer_name": "Taimur Ali",
        "customer_phone": "0312-3456789",
        "shipping_address_line1": "Street 9, Sector H-12",
        "shipping_city": "Islamabad",
        "shipping_province": "Islamabad Capital Territory",
        "payment_method": "bank_transfer",
        "items": [{"variant_id": var.id, "quantity": 2}],
    }
    order_res = _post_checkout(admin_client, order_payload)
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 2. Check stock metrics: Physical 10 | Held 2 | Available 8
    sum_res = admin_client.get("/api/v1/admin/inventory/summary")
    match = next(item for item in sum_res.json()["items"] if item["supplier_variant_id"] == str(sv_id))
    assert match["physical_on_hand"] == 10
    assert match["held_reservations"] == 2
    assert match["available_to_sell"] == 8

    # 3. Owner verifies payment
    vp_res = admin_client.post(f"/api/v1/admin/orders/{order_id}/verify-payment")
    assert vp_res.status_code == 200
    assert vp_res.json()["payment_status"] == "verified"
    assert vp_res.json()["order_status"] == "placed"

    # 3b. Confirm supplier acceptance
    conf_res = admin_client.post(
        f"/api/v1/admin/orders/{order_id}/confirm-supplier",
        json={"notes": "Packed and ready"},
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["order_status"] == "confirmed"
    assert conf_res.json()["supplier_notes"] == "Packed and ready"

    # 4. Dispatch deducts physical stock; delivery only closes allocations.
    dispatched = admin_client.post(f"/api/v1/admin/orders/{order_id}/dispatch",
                                   json={"courier_code": "manual", "tracking_number": "ADMIN-LIFE-001"})
    assert dispatched.status_code == 201
    del_res = admin_client.post(f"/api/v1/admin/orders/{order_id}/deliver")
    assert del_res.status_code == 200
    assert del_res.json()["order_status"] == "delivered"

    # 5. Check stock metrics after delivery: Physical 8 | Held 0 | Available 8
    sum_res2 = admin_client.get("/api/v1/admin/inventory/summary")
    match2 = next(item for item in sum_res2.json()["items"] if item["supplier_variant_id"] == str(sv_id))
    assert match2["physical_on_hand"] == 8
    assert match2["held_reservations"] == 0
    assert match2["available_to_sell"] == 8


def test_admin_order_cancellation_releases_held_stock(admin_client, db_session):
    setup = _create_admin_setup(db_session, on_hand=10)
    var = setup["variant"]
    sv_id = setup["sv"].id

    # 1. Place COD order for 3 units
    order_payload = {
        "customer_name": "Nabeel Khan",
        "customer_phone": "0301-7654321",
        "shipping_address_line1": "Mall Road",
        "shipping_city": "Rawalpindi",
        "shipping_province": "Punjab",
        "payment_method": "cod",
        "items": [{"variant_id": var.id, "quantity": 3}],
    }
    order_res = _post_checkout(admin_client, order_payload)
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 2. Stock metrics: Physical 10 | Held 3 | Available 7
    sum_res = admin_client.get("/api/v1/admin/inventory/summary")
    match = next(item for item in sum_res.json()["items"] if item["supplier_variant_id"] == str(sv_id))
    assert match["physical_on_hand"] == 10
    assert match["held_reservations"] == 3
    assert match["available_to_sell"] == 7

    # 3. Owner cancels order
    cancel_res = admin_client.post(f"/api/v1/admin/orders/{order_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["order_status"] == "cancelled"

    # 4. Stock metrics immediately released: Physical 10 | Held 0 | Available 10
    sum_res2 = admin_client.get("/api/v1/admin/inventory/summary")
    match2 = next(item for item in sum_res2.json()["items"] if item["supplier_variant_id"] == str(sv_id))
    assert match2["physical_on_hand"] == 10
    assert match2["held_reservations"] == 0
    assert match2["available_to_sell"] == 10


def test_admin_overview_metrics(admin_client, db_session):
    setup = _create_admin_setup(db_session, on_hand=1)  # Low stock (1 <= 2)
    var = setup["variant"]

    # 1. Overview initially
    ov_res = admin_client.get("/api/v1/admin/overview")
    assert ov_res.status_code == 200
    ov_data = ov_res.json()
    assert ov_data["total_skus"] >= 1
    assert ov_data["low_stock_skus"] >= 1

    # 2. Place and verify an order
    order_payload = {
        "customer_name": "Overview Test Customer",
        "customer_phone": "0300-4444444",
        "shipping_address_line1": "Street 5, G-9",
        "shipping_city": "Islamabad",
        "shipping_province": "ICT",
        "payment_method": "bank_transfer",
        "items": [{"variant_id": var.id, "quantity": 1}],
    }
    ord_res = _post_checkout(admin_client, order_payload)
    assert ord_res.status_code == 201
    ord_id = ord_res.json()["id"]

    # Verify payment -> turns payment_status to 'verified'
    admin_client.post(f"/api/v1/admin/orders/{ord_id}/verify-payment")
    admin_client.post(f"/api/v1/admin/orders/{ord_id}/confirm-supplier")

    # 3. Check updated overview
    ov_res2 = admin_client.get("/api/v1/admin/overview")
    assert ov_res2.status_code == 200
    ov_data2 = ov_res2.json()
    assert ov_data2["gross_revenue_minor"] == 0
    assert "PKR" in ov_data2["formatted_gross_revenue"]
    assert ov_data2["total_orders"] >= 1
    assert ov_data2["confirmed_orders"] >= 1
    dispatched = admin_client.post(f'/api/v1/admin/orders/{ord_id}/dispatch', json={
        'courier_code': 'manual', 'tracking_number': 'OVERVIEW-TEST-01',
    })
    assert dispatched.status_code == 201
    assert admin_client.post(f'/api/v1/admin/shipments/{dispatched.json()["id"]}/status',
                             json={'status': 'delivered'}).status_code == 200
    assert admin_client.get('/api/v1/admin/overview').json()['gross_revenue_minor'] >= 320000


def test_admin_supplier_crud_and_variant_cost_assignment(admin_client, db_session):
    unique_suffix = uuid.uuid4().hex[:6]
    setup = _create_admin_setup(db_session, on_hand=5)
    var_id = setup["variant"].id

    # 1. Create supplier
    sup_payload = {
        "name": f"Textile Hub {unique_suffix}",
        "slug": f"textile-hub-{unique_suffix}",
        "status": "active",
        "notes": "Net 15 days credit terms",
    }
    create_res = admin_client.post("/api/v1/admin/suppliers", json=sup_payload)
    assert create_res.status_code == 201
    sup_data = create_res.json()
    sup_id = sup_data["id"]
    assert sup_data["name"] == f"Textile Hub {unique_suffix}"

    # Duplicate slug returns 409
    dup_res = admin_client.post("/api/v1/admin/suppliers", json=sup_payload)
    assert dup_res.status_code == 409

    # 2. List suppliers
    list_res = admin_client.get("/api/v1/admin/suppliers")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert any(s["id"] == sup_id for s in list_res.json()["suppliers"])

    # 3. Assign variant with agreed cost
    assign_payload = {
        "variant_id": var_id,
        "supplier_cost_minor": 175000,
        "active": True,
    }
    assign_res = admin_client.post(f"/api/v1/admin/suppliers/{sup_id}/variants", json=assign_payload)
    assert assign_res.status_code == 409  # Variant controls cannot bypass product responsibility.
    stock = admin_client.post('/api/v1/admin/inventory/adjust', json={
        'supplier_variant_id': str(setup['sv'].id), 'quantity_delta': -5,
        'expected_version': setup['balance'].version, 'reason': 'manual_count'})
    assert stock.status_code == 200, stock.text
    product = admin_client.get(f"/api/v1/admin/products/{setup['product'].id}").json()
    reassigned = admin_client.post(f"/api/v1/admin/products/{setup['product'].id}", json={
        'expected_version': product['edit_version'], 'stock_management_source': 'vendor_managed', 'vendor_id': sup_id})
    assert reassigned.status_code == 200, reassigned.text
    assign_res = admin_client.post(f"/api/v1/admin/suppliers/{sup_id}/variants", json=assign_payload)
    assert assign_res.status_code == 200
    assign_data = assign_res.json()
    assert assign_data["supplier_id"] == sup_id
    assert assign_data["variant_id"] == var_id
    assert assign_data["supplier_cost_minor"] == 175000
    assert assign_data["active"] is True
    persisted = admin_client.get('/api/v1/admin/catalog/variants')
    assert persisted.status_code == 200
    mapped = next(item for item in persisted.json() if item['id'] == var_id)
    assert mapped['active_supplier_id'] == sup_id
    assert mapped['supplier_cost_minor'] == 175000

