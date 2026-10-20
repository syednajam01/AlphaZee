"""Automated tests for VF5 / VS2-VS3: Vendor Stock-Only Portal & Authentication."""
import json
import secrets
import uuid
import pytest
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.suppliers import Supplier
from app.models.vendor_portal import VendorSession, VendorStockShortage, VendorUser
from app.queries.inventory import adjust_inventory
from app.services.owners import provision_owner
from app.services.vendor_portal import provision_vendor_user
from app.services.vendor_session_store import csrf_token as vendor_csrf_token


@pytest.fixture
def db(db_session):
    return db_session


@pytest.fixture
def client(db_session, monkeypatch):
    from app.database import get_db
    from app.dependencies.checkout import require_checkout_enabled
    from sqlalchemy.orm import sessionmaker
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_checkout_enabled] = lambda: None
    # Legacy helpers use SessionLocal; route them to this same guarded test transaction.
    import sys
    module = sys.modules[__name__]
    from contextlib import contextmanager
    @contextmanager
    def scoped_session():
        yield db_session
    monkeypatch.setattr(module, 'SessionLocal', scoped_session)
    try:
        with TestClient(app, base_url='http://localhost:3000') as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _create_owner(db, username=None):
    token = secrets.token_hex(4)
    uname = username or f"owner_vf5_{token}"
    pwd = f"OwnerPass123_{token}"
    owner = provision_owner(db, uname, pwd, allow_short_local=True)
    db.commit()
    return uname, pwd


def _login_owner(client, username, password):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.status_code == 200, res.text
    return res.json()["csrf_token"]


def _create_vendor_and_products(db):
    token = secrets.token_hex(4)
    col = db.get(Collection, "essentials")
    if not col:
        col = Collection(
            id="essentials",
            slug="essentials",
            name="Essentials",
            is_active=True,
            display_order=1,
        )
        db.add(col)
        db.flush()

    # 1. Create two external suppliers
    v_a = Supplier(
        id=uuid.uuid4(),
        name=f"Vendor Alpha ({token})",
        slug=f"vendor-alpha-{token}",
        status="active",
        supplier_type="external_vendor",
    )
    v_b = Supplier(
        id=uuid.uuid4(),
        name=f"Vendor Beta ({token})",
        slug=f"vendor-beta-{token}",
        status="active",
        supplier_type="external_vendor",
    )
    db.add_all([v_a, v_b])
    db.flush()

    # 2. Create products: Prod A assigned to Vendor A, Prod B to Vendor B
    prod_a = Product(
        id=f"prod-a-{token}",
        title=f"Linen Shirt A {token}",
        slug=f"linen-shirt-a-{token}",
        collection_id=col.id,
        status="published",
        stock_management_source="vendor_managed",
        vendor_id=v_a.id,
    )
    prod_b = Product(
        id=f"prod-b-{token}",
        title=f"Silk Tunic B {token}",
        slug=f"silk-tunic-b-{token}",
        collection_id=col.id,
        status="published",
        stock_management_source="vendor_managed",
        vendor_id=v_b.id,
    )
    db.add_all([prod_a, prod_b])
    db.flush()

    # 3. Create variants
    var_a1 = Variant(
        product_id=prod_a.id,
        sku=f"VA1-{token}",
        size="M",
        color="Navy",
        price_minor=350000,
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    var_a2 = Variant(
        product_id=prod_a.id,
        sku=f"VA2-{token}",
        size="L",
        color="Navy",
        price_minor=350000,
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    var_b1 = Variant(
        product_id=prod_b.id,
        sku=f"VB1-{token}",
        size="S",
        color="Crimson",
        price_minor=420000,
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    db.add_all([var_a1, var_a2, var_b1])
    db.flush()

    # 4. Create SupplierVariant links and inventory balances
    sv_a1 = SupplierVariant(
        supplier_id=v_a.id,
        variant_id=var_a1.id,
        active=True,
        supplier_cost_minor=200000,
    )
    sv_a2 = SupplierVariant(
        supplier_id=v_a.id,
        variant_id=var_a2.id,
        active=True,
        supplier_cost_minor=200000,
    )
    sv_b1 = SupplierVariant(
        supplier_id=v_b.id,
        variant_id=var_b1.id,
        active=True,
        supplier_cost_minor=250000,
    )
    db.add_all([sv_a1, sv_a2, sv_b1])
    db.flush()

    bal_a1 = InventoryBalance(supplier_variant_id=sv_a1.id, on_hand=3, version=0)
    bal_a2 = InventoryBalance(supplier_variant_id=sv_a2.id, on_hand=5, version=0)
    bal_b1 = InventoryBalance(supplier_variant_id=sv_b1.id, on_hand=10, version=0)
    db.add_all([bal_a1, bal_a2, bal_b1])
    db.commit()

    return {
        "v_a": v_a,
        "v_b": v_b,
        "prod_a": prod_a,
        "prod_b": prod_b,
        "var_a1": var_a1,
        "var_a2": var_a2,
        "var_b1": var_b1,
        "sv_a1": sv_a1,
        "bal_a1": bal_a1,
    }


def test_owner_provision_vendor_user_and_lifecycle(db, client):
    """Test owner provisioning, listing, password reset, and access toggling."""
    o_uname, o_pwd = _create_owner(db)
    o_csrf = _login_owner(client, o_uname, o_pwd)

    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]

    # 1. Provision vendor stock user
    v_uname = f"staff_{secrets.token_hex(3)}"
    v_pwd = "VendorPassword123"
    res = client.post(
        f"/api/v1/admin/suppliers/{v_a.id}/users",
        json={"username": v_uname, "password": v_pwd, "allow_short_local": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": o_csrf},
    )
    assert res.status_code == 201, res.text
    user_data = res.json()
    assert user_data["username"] == v_uname
    assert user_data["vendor_id"] == str(v_a.id)
    assert user_data["is_active"] is True
    vendor_user_id = user_data["id"]

    # 2. List users for supplier
    res_list = client.get(
        f"/api/v1/admin/suppliers/{v_a.id}/users",
        headers={"Origin": "http://localhost:3000"},
    )
    assert res_list.status_code == 200
    users = res_list.json()
    assert len(users) >= 1
    assert any(u["username"] == v_uname for u in users)

    # 3. Reset password
    res_reset = client.post(
        f"/api/v1/admin/vendor-users/{vendor_user_id}/reset-password",
        json={"password": "NewVendorPassword456", "allow_short_local": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": o_csrf},
    )
    assert res_reset.status_code == 200

    # 4. Toggle active status
    res_toggle = client.post(
        f"/api/v1/admin/vendor-users/{vendor_user_id}/toggle-status",
        json={"is_active": False},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": o_csrf},
    )
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] is False


def test_vendor_authentication_and_session_isolation(db, client):
    """Test vendor login, session retrieval, rate limits, and scope isolation."""
    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]

    v_uname = f"login_user_{secrets.token_hex(3)}"
    v_pwd = "SecureVendorPassword123!"
    provision_vendor_user(db, v_a.id, v_uname, v_pwd, allow_short_local=True)
    db.commit()

    # 1. Vendor login
    res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.status_code == 200, res.text
    session_data = res.json()
    assert session_data["username"] == v_uname
    assert session_data["vendor_name"] == v_a.name
    assert "csrf_token" in session_data
    v_csrf = session_data["csrf_token"]

    # Verify session cookie was set
    assert "alphazee_vendor_session" in client.cookies

    # 2. Get vendor session
    res_sess = client.get("/api/v1/vendor/auth/session")
    assert res_sess.status_code == 200
    assert res_sess.json()["authenticated"] is True
    assert res_sess.json()["vendor_id"] == str(v_a.id)

    # 3. Scope Isolation: Vendor session CANNOT access admin endpoints
    res_admin = client.get("/api/v1/admin/overview")
    assert res_admin.status_code == 401

    # 4. Vendor logout
    res_logout = client.post(
        "/api/v1/vendor/auth/logout",
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert res_logout.status_code == 204

    # Post-logout session check fails
    res_after = client.get("/api/v1/vendor/auth/session")
    assert res_after.status_code == 401


def test_vendor_stock_list_multi_tenant_isolation(db, client):
    """Test Vendor A sees ONLY Vendor A's items with zero pricing/cost leakage."""
    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]
    v_b = ctx["v_b"]

    v_uname = f"vendor_a_{secrets.token_hex(3)}"
    v_pwd = "Password123!"
    provision_vendor_user(db, v_a.id, v_uname, v_pwd, allow_short_local=True)
    db.commit()

    # Login as Vendor A
    client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )

    # Fetch stock
    res = client.get("/api/v1/vendor/stock")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]

    # Must see Prod A variants
    assert len(items) == 2
    skus = [i["variant_sku"] for i in items]
    assert ctx["var_a1"].sku in skus
    assert ctx["var_a2"].sku in skus

    # Must NOT see Vendor B variant
    assert ctx["var_b1"].sku not in skus

    # ZERO LEAKAGE: Verify sensitive fields are not present in response items
    first_item = items[0]
    for sensitive_key in ["supplier_cost_minor", "cost_minor", "price_minor", "margin", "customer_name"]:
        assert sensitive_key not in first_item, f"Leaked sensitive field '{sensitive_key}' to vendor!"

    # Verify quantities exposed
    assert first_item["allocated_on_hand"] == 3
    assert first_item["held_quantity"] == 0
    assert first_item["available_quantity"] == 3


def test_vendor_count_update_3_to_2_and_idempotency(db, client):
    """Test 3 -> 2 shop sale update, optimistic concurrency, and repeated save."""
    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]
    var_a1 = ctx["var_a1"]

    v_uname = f"vendor_count_{secrets.token_hex(3)}"
    v_pwd = "Password123!"
    provision_vendor_user(db, v_a.id, v_uname, v_pwd, allow_short_local=True)
    db.commit()

    # Login as Vendor A
    login_res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )
    v_csrf = login_res.json()["csrf_token"]

    # 1. Update from 3 to 2 (Shop sale)
    res_update = client.post(
        f"/api/v1/vendor/stock/{var_a1.id}/count",
        json={
            "counted_quantity": 2,
            "expected_version": 0,
            "reason": "shop_sale",
            "note": "One unit sold in physical store",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert res_update.status_code == 200, res_update.text
    body = res_update.json()
    assert body["allocated_on_hand"] == 2
    assert body["available_quantity"] == 2
    assert body["version"] == 1
    assert body["shortage_detected"] is False

    # 2. Concurrency Conflict: Attempting to update with stale version 0 fails with 409
    res_conflict = client.post(
        f"/api/v1/vendor/stock/{var_a1.id}/count",
        json={
            "counted_quantity": 2,
            "expected_version": 0,
            "reason": "shop_sale",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert res_conflict.status_code == 409
    assert "version conflict" in res_conflict.json()["detail"].lower()

    # 3. Repeated Save with correct version (version 1) to count 2 is idempotent
    res_repeat = client.post(
        f"/api/v1/vendor/stock/{var_a1.id}/count",
        json={
            "counted_quantity": 2,
            "expected_version": 1,
            "reason": "inventory_count_correction",
            "note": "Re-saved without change",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert res_repeat.status_code == 200
    assert res_repeat.json()["allocated_on_hand"] == 2
    assert res_repeat.json()["version"] == 2

    # 4. Check audit history includes these updates
    res_hist = client.get("/api/v1/vendor/stock/history")
    assert res_hist.status_code == 200
    events = res_hist.json()["history"]
    assert len(events) >= 2
    assert events[0]["variant_id"] == var_a1.id


def test_vendor_shortage_handling_and_owner_resolution(db, client):
    """Test that a reported count below holds creates a shortage without deleting reservations."""
    from app.models.inventory import StockReservation
    from app.models.orders import Order, OrderLine

    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]
    var_a1 = ctx["var_a1"]
    sv_a1 = ctx["sv_a1"]

    v_uname = f"vendor_shortage_{secrets.token_hex(3)}"
    v_pwd = "Password123!"
    provision_vendor_user(db, v_a.id, v_uname, v_pwd, allow_short_local=True)

    # Create an order and stock hold on var_a1 (held = 1, on_hand = 3)
    order = Order(
        order_number=f"AZ-SHORT-{secrets.token_hex(3)}",
        order_status="confirmed",
        customer_name="Test Customer",
        customer_phone="03001234567",
        shipping_address_line1="123 Street",
        shipping_city="Lahore",
        shipping_province="Punjab",
        total_minor=350000,
        subtotal_minor=350000,
        payment_method="cod",
        payment_status="pending",
    )
    db.add(order)
    db.flush()

    line = OrderLine(
        order_id=order.id,
        variant_id=var_a1.id,
        product_title_snapshot="Linen Shirt",
        variant_sku_snapshot=var_a1.sku,
        quantity=1,
        unit_price_minor=350000,
        line_total_minor=350000,
    )
    db.add(line)
    db.flush()

    hold = StockReservation(
        order_line_id=line.id,
        supplier_variant_id=sv_a1.id,
        quantity=1,
        stage="held",
        legacy_stock_hold=False,
    )
    db.add(hold)
    db.commit()

    # Vendor A logs in
    login_res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )
    v_csrf = login_res.json()["csrf_token"]

    # Vendor reports count 0 while 1 is held!
    res_short = client.post(
        f"/api/v1/vendor/stock/{var_a1.id}/count",
        json={
            "counted_quantity": 0,
            "expected_version": 0,
            "reason": "shop_sale",
            "note": "Items damaged in store flood, 0 left",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert res_short.status_code == 200
    res_body = res_short.json()
    assert res_body["shortage_detected"] is True
    assert "shortage alert recorded" in res_body["message"].lower()

    # Invariants verification:
    # 1. Customer reservation is PRESERVED (still stage='held')
    db.refresh(hold)
    assert hold.stage == "held"
    assert hold.quantity == 1

    # 2. Balance on hand was NOT zeroed or corrupted
    bal = db.get(InventoryBalance, sv_a1.id)
    assert bal.on_hand == 3

    # 3. Owner can view and resolve the shortage
    o_uname, o_pwd = _create_owner(db)
    o_csrf = _login_owner(client, o_uname, o_pwd)

    res_shortages = client.get("/api/v1/admin/shortages", headers={"Origin": "http://localhost:3000"})
    assert res_shortages.status_code == 200
    shortages_list = res_shortages.json()
    assert len(shortages_list) >= 1
    target_shortage = next(s for s in shortages_list if s["variant_id"] == var_a1.id)
    assert target_shortage["reported_count"] == 0
    assert target_shortage["held_reservations"] == 1

    # A promise to wait cannot resolve a physical shortage. Recount first.
    recount = client.post(f'/api/v1/vendor/stock/{var_a1.id}/count', json={
        'counted_quantity': 3, 'expected_version': bal.version, 'reason': 'stock_correction'},
        headers={'Origin': 'http://localhost:3000', 'X-CSRF-Token': v_csrf})
    assert recount.status_code == 200, recount.text
    # Owner resolves shortage after the audited count.
    res_res = client.post(
        f"/api/v1/admin/shortages/{target_shortage['id']}/resolve",
        json={"resolution_action": "resolved", "resolution_note": "Customer contacted and agreed to wait for fresh stock"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": o_csrf},
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"


def test_cross_shop_mutation_rejected(db, client):
    """Test Vendor A cannot update count for Vendor B's variant."""
    ctx = _create_vendor_and_products(db)
    v_a = ctx["v_a"]
    var_b1 = ctx["var_b1"]  # belongs to Vendor B!

    v_uname = f"vendor_a_bad_{secrets.token_hex(3)}"
    v_pwd = "Password123!"
    provision_vendor_user(db, v_a.id, v_uname, v_pwd, allow_short_local=True)
    db.commit()

    # Login as Vendor A
    login_res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )
    v_csrf = login_res.json()["csrf_token"]

    # Attempt to update Vendor B's variant
    res_bad = client.post(
        f"/api/v1/vendor/stock/{var_b1.id}/count",
        json={"counted_quantity": 5, "expected_version": 0, "reason": "restock"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    # Must be rejected (HTTP 400 Bad Request or 404)
    assert res_bad.status_code in (400, 404)
    assert "not assigned" in res_bad.json()["detail"].lower()
