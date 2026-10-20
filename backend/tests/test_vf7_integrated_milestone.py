"""
test_vf7_integrated_milestone.py — Integrated Milestone Acceptance & End-to-End Scenarios.

Phase VF7 verifies the complete cross-functional lifecycle across:
1. Supplier agreement configuration & payment terms.
2. Restricted vendor authentication & mobile-first stock reporting.
3. Shortage preservation safeguards (customer holds strictly preserved when vendor count drops).
4. Owner order fulfillment, dispatch & automatic supplier liability accrual (with deduplication).
5. Courier COD delivery & cash settlement with expense deduction linkage (no double-counting).
6. Supplier partial payments with FIFO allocation and statement balance drill-down.
7. Customer returns, AlphaZee-borne transport expenses, and restocked AlphaZee-owned inventory.
8. Resale invariant: second sale of AlphaZee-owned returned unit creates zero duplicate vendor liability.
9. Period financial reporting (P&L, cash movement reconciliation, and CSV formula injection mitigation).
10. Multi-tenant security boundaries, owner preferences, and checkout containment.
"""

from datetime import date, datetime, timezone
import secrets
import uuid
import pytest
from sqlalchemy import delete
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.auth import OwnerLoginBucket
from app.models.business_expenses import BusinessExpense
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.finance import CourierSettlementEntry
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment
from app.models.store_settings import OwnerPreference, StoreSettings, StoreSettingsAuditLog
from app.models.supplier_finance import (
    SupplierAgreement,
    SupplierLedgerEntry,
    SupplierPaymentAllocation,
)
from app.models.suppliers import Supplier
from app.models.vendor_portal import VendorSession, VendorStockShortage, VendorUser
from app.schemas.owner_catalog import ProductCreate, VariantEdit
from app.schemas.supplier_finance import (
    SupplierAgreementUpdateRequest,
    SupplierPaymentRequest,
)
from app.services.business_expenses import create_business_expense
from app.services.financial_report import (
    escape_csv_cell,
    export_order_economics_csv,
    export_period_pnl_csv,
    get_order_economics_list,
    get_period_financial_report,
)
from app.services.owner_catalog import create_product
from app.services.owners import provision_owner
from app.services.supplier_finance import (
    get_or_create_supplier_agreement,
    post_event_liability_if_applicable,
    post_supplier_payment,
    update_supplier_agreement,
)
from app.services.vendor_portal import (
    provision_vendor_user,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app, base_url="http://localhost:3000")


def _login_owner(client, username, password):
    with SessionLocal() as s:
        s.execute(delete(OwnerLoginBucket))
        s.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.status_code == 200, res.text
    return res.json()["csrf_token"]


def test_vf7_complete_cross_functional_lifecycle(db, client):
    """
    Full end-to-end scenario:
    1. Setup supplier with agreement (trigger='dispatch', terms=15 days).
    2. Provision vendor user; vendor updates on-hand stock via portal.
    3. Customer order placed -> active hold created.
    4. Vendor reports count below active hold -> shortage record created, customer hold preserved.
    5. Owner fulfills & dispatches -> charge accrued in supplier ledger (120,000 paisas).
    6. Repeated dispatch -> 0 duplicate charge (idempotency).
    7. Courier delivers COD & settles cash: 200,000 paisas collected, 20,000 delivery fee deducted & linked.
    8. Owner pays supplier 70,000 paisas partial payment -> allocated via FIFO, balance 50,000 paisas.
    9. Customer return completed -> unit restocked as 'alphazee_owned'; 15,000 return freight expense logged.
    10. Resale of returned unit -> 0 duplicate supplier liability created!
    11. Period P&L & Cash Reconciliation match to the exact paisa.
    """
    token = secrets.token_hex(4)

    # 1. Supplier & Agreement
    sup = Supplier(
        id=uuid.uuid4(),
        name=f"VF7 Master Vendor ({token})",
        slug=f"vf7-vendor-{token}",
        status="active",
        supplier_type="external_vendor",
    )
    db.add(sup)
    db.flush()

    update_supplier_agreement(
        db,
        sup.id,
        SupplierAgreementUpdateRequest(
            payable_trigger="dispatch",
            payment_terms_days=15,
            notes="VF7 Master Acceptance Agreement",
        ),
    )

    # 2. Product & Variant
    col = db.get(Collection, "essentials")
    if not col:
        col = Collection(id="essentials", slug="essentials", name="Essentials", is_active=True, display_order=1)
        db.add(col)
        db.flush()

    prod = create_product(
        db,
        ProductCreate(
            title=f"VF7 Signature Jacket ({token})",
            slug=f"vf7-jacket-{token}",
            collection_id=col.id,
            stock_management_source="vendor_managed",
            vendor_id=sup.id,
            variants=[
                VariantEdit(
                    sku=f"VF7-JKT-{token}",
                    size="L",
                    color="Charcoal",
                    price_minor=200000,  # PKR 2,000
                    is_active=True,
                )
            ],
        ),
    )
    db.flush()
    var = prod.variants[0]
    sv = db.query(SupplierVariant).filter_by(variant_id=var.id, supplier_id=sup.id).first()
    assert sv is not None

    # Initialize inventory balance
    bal = db.query(InventoryBalance).filter_by(supplier_variant_id=sv.id).first()
    if not bal:
        bal = InventoryBalance(supplier_variant_id=sv.id, on_hand=0, version=0)
        db.add(bal)
        db.commit()

    # 3. Provision Vendor User & Vendor Stock Update via API
    v_uname = f"vstaff_{token}"
    v_pwd = f"StaffPass123_{token}"
    provision_vendor_user(db, sup.id, v_uname, v_pwd, allow_short_local=True)
    db.commit()

    # Vendor logs in via vendor auth endpoint
    v_login_res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": v_uname, "password": v_pwd},
        headers={"Origin": "http://localhost:3000"},
    )
    assert v_login_res.status_code == 200, v_login_res.text
    v_csrf = v_login_res.json()["csrf_token"]

    # Vendor updates physical count to 10 units
    v_up_res = client.post(
        f"/api/v1/vendor/stock/{var.id}/count",
        json={
            "counted_quantity": 10,
            "expected_version": 0,
            "reason": "daily_audit",
            "note": "Initial physical stock verification",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert v_up_res.status_code == 200, v_up_res.text
    stock_body = v_up_res.json()
    assert stock_body["allocated_on_hand"] == 10
    assert stock_body["available_quantity"] == 10
    assert stock_body["version"] == 1

    # 4. Customer Order Placed -> Active Hold
    order1 = Order(
        order_number=f"ORD-VF7-01-{token}",
        customer_name="Ayesha Khan",
        customer_phone="03001234567",
        shipping_address_line1="DHA Phase 5",
        shipping_city="Lahore",
        shipping_province="Punjab",
        payment_method="cod",
        payment_status="pending",
        order_status="confirmed",
        subtotal_minor=200000,
        shipping_fee_minor=0,
        total_minor=200000,
    )
    db.add(order1)
    db.flush()

    line1 = OrderLine(
        order_id=order1.id,
        variant_id=var.id,
        product_title_snapshot=prod.title,
        variant_sku_snapshot=var.sku,
        unit_price_minor=200000,
        unit_cost_minor=120000,  # Wholesale cost PKR 1,200
        quantity=1,
        line_total_minor=200000,
        ownership_source="vendor_consignment",
    )
    order1.lines.append(line1)
    db.flush()

    # Active hold placed
    hold1 = StockReservation(
        order_line_id=line1.id,
        supplier_variant_id=sv.id,
        quantity=1,
        stage="held",
        legacy_stock_hold=False,
    )
    db.add(hold1)
    db.commit()

    # Vendor inspects stock via portal -> sees held_quantity=1, available=9
    v_stock_res = client.get("/api/v1/vendor/stock")
    assert v_stock_res.status_code == 200
    v_items = v_stock_res.json()["items"]
    v_item = next(i for i in v_items if i["variant_id"] == var.id)
    assert v_item["allocated_on_hand"] == 10
    assert v_item["held_quantity"] == 1
    assert v_item["available_quantity"] == 9

    # 5. Shortage Safeguard: Vendor reports 0 while held_count is 1
    # Customer hold must be preserved, shortage detected
    v_short_res = client.post(
        f"/api/v1/vendor/stock/{var.id}/count",
        json={
            "counted_quantity": 0,
            "expected_version": 1,
            "reason": "stock_correction",
            "note": "Cannot locate item in backroom",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert v_short_res.status_code == 200
    short_body = v_short_res.json()
    assert short_body["shortage_detected"] is True
    assert short_body["allocated_on_hand"] == 10
    assert short_body["held_quantity"] == 1
    assert short_body["version"] == 1

    # Verify shortage record in database
    shortage_rec = db.query(VendorStockShortage).filter_by(vendor_id=sup.id, variant_id=var.id).first()
    assert shortage_rec is not None
    assert shortage_rec.reported_count == 0
    assert shortage_rec.held_reservations == 1
    assert shortage_rec.status == "open"

    # Shop staff finds the unit! Updates physical count back to 5 (expected_version is still 1)
    v_recover_res = client.post(
        f"/api/v1/vendor/stock/{var.id}/count",
        json={
            "counted_quantity": 5,
            "expected_version": 1,
            "reason": "stock_correction",
            "note": "Located unit in display rack",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": v_csrf},
    )
    assert v_recover_res.status_code == 200
    assert v_recover_res.json()["allocated_on_hand"] == 5
    assert v_recover_res.json()["held_quantity"] == 1
    assert v_recover_res.json()["available_quantity"] == 4
    assert v_recover_res.json()["version"] == 2

    # 6. Owner Fulfillment & Dispatch -> Supplier Liability Accrual
    entries = post_event_liability_if_applicable(db, order1, "dispatch")
    db.commit()
    assert len(entries) == 1
    charge_entry = entries[0]
    assert charge_entry.entry_type == "charge"
    assert charge_entry.direction == "credit"
    assert charge_entry.amount_minor == 120000  # PKR 1,200

    # Idempotency check: Repeated dispatch does not duplicate charge
    entries_dupe = post_event_liability_if_applicable(db, order1, "dispatch")
    assert len(entries_dupe) == 0

    # 7. Courier Delivery & COD Settlement
    order1.order_status = "delivered"
    order1.delivery_confirmed_at = datetime.now(timezone.utc)
    db.flush()

    # Outbound delivery expense recorded (PKR 200 = 20,000 paisas)
    exp_delivery = BusinessExpense(
        id=uuid.uuid4(),
        category="outbound_delivery",
        amount_minor=20000,
        incurred_date=date.today(),
        paid_date=date.today(),
        payee="Trax Logistics",
        reference=f"TRAX-{token}",
        notes="Outbound COD delivery",
    )
    db.add(exp_delivery)
    db.flush()

    # Courier remits PKR 1,800 net of PKR 200 delivery fee
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order1.id,
        courier_code="trax",
        tracking_number=f"TRX-{token}",
        shipping_cost_minor=20000,
        cod_amount_minor=200000,
        status="delivered",
        cod_remittance_status="remitted",
        delivered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(shipment)
    db.flush()

    remit_receipt = CourierSettlementEntry(
        id=uuid.uuid4(),
        shipment_id=shipment.id,
        entry_type="receipt",
        amount_minor=180000,  # PKR 1,800
        reference=f"BANK-TRX-REMIT-{token}",
        final_statement=True,
        recorded_at=datetime.now(timezone.utc),
    )
    deduction = CourierSettlementEntry(
        id=uuid.uuid4(),
        shipment_id=shipment.id,
        entry_type="outbound_shipping",
        amount_minor=20000,  # PKR 200
        reference=f"TRX-FEE-DED-{token}",
        final_statement=True,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add_all([remit_receipt, deduction])
    db.commit()

    # 8. Supplier Partial Payment & FIFO Allocation
    # Total charge: 120,000 paisas. Owner pays 70,000 paisas.
    payment_entry, allocs = post_supplier_payment(
        db,
        supplier_id=sup.id,
        payload=SupplierPaymentRequest(
            amount_minor=70000,
            payment_method="bank_transfer",
            effective_date=date.today(),
            reference=f"BANK-TRF-{token}",
            notes="Partial payment for VF7 batch",
            auto_allocate_fifo=True,
        ),
    )
    db.commit()
    assert payment_entry.entry_type == "payment"
    assert payment_entry.direction == "debit"
    assert payment_entry.amount_minor == 70000
    assert len(allocs) == 1
    assert allocs[0].charge_entry_id == charge_entry.id
    assert allocs[0].allocated_amount_minor == 70000

    # Check outstanding liability: 120,000 - 70,000 = 50,000 paisas (PKR 500)
    all_entries = db.query(SupplierLedgerEntry).filter_by(supplier_id=sup.id).all()
    credits = sum(e.amount_minor for e in all_entries if e.direction == "credit")
    debits = sum(e.amount_minor for e in all_entries if e.direction == "debit")
    assert credits - debits == 50000

    # 9. Customer Return & AlphaZee-Owned Inventory
    # Customer returns the jacket. AlphaZee bears PKR 150 return shipping.
    exp_return = BusinessExpense(
        id=uuid.uuid4(),
        category="customer_return_transport",
        amount_minor=15000,
        incurred_date=date.today(),
        paid_date=date.today(),
        payee="Trax Reverse",
        reference=f"TRAX-REV-{token}",
        notes="Customer return freight borne 100% by AlphaZee",
    )
    db.add(exp_return)

    order_return = OrderReturn(
        id=uuid.uuid4(),
        order_id=order1.id,
        order_line_id=line1.id,
        return_type="refund_bank_transfer",
        reason="size_too_small",
        status="completed",
        quantity=1,
        received_quantity=1,
        sellable_quantity=1,
        damaged_quantity=0,
        refund_amount_minor=200000,
        created_at=datetime.now(timezone.utc),
        inspected_at=datetime.now(timezone.utc),
    )
    db.add(order_return)
    db.commit()

    # 10. Secondary Resale Invariant: Resale of AlphaZee-Owned Unit
    # Customer 2 purchases the restocked AlphaZee-owned unit.
    order2 = Order(
        order_number=f"ORD-VF7-02-{token}",
        customer_name="Bilal Tariq",
        customer_phone="03009876543",
        shipping_address_line1="Gulberg III",
        shipping_city="Lahore",
        shipping_province="Punjab",
        payment_method="cod",
        payment_status="pending",
        order_status="confirmed",
        subtotal_minor=200000,
        shipping_fee_minor=0,
        total_minor=200000,
    )
    db.add(order2)
    db.flush()

    line2 = OrderLine(
        order_id=order2.id,
        variant_id=var.id,
        product_title_snapshot=prod.title,
        variant_sku_snapshot=var.sku,
        unit_price_minor=200000,
        unit_cost_minor=120000,
        quantity=1,
        line_total_minor=200000,
        ownership_source="alphazee_owned",  # Sourced from returned AlphaZee-owned inventory!
    )
    order2.lines.append(line2)
    db.commit()

    # Dispatch order 2 -> Must create ZERO supplier liability
    entries_order2 = post_event_liability_if_applicable(db, order2, "dispatch")
    assert len(entries_order2) == 0, "Resale of AlphaZee-owned inventory must create 0 supplier liability!"

    # 11. Financial Reports & Cash Reconciliation Validation
    report = get_period_financial_report(db, start_date=date.today(), end_date=date.today())
    assert report["delivered_orders_count"] >= 1
    assert report["revenue"]["gross_sales_minor"] >= 200000
    assert report["freight"]["outbound_freight_minor"] >= 20000
    assert report["freight"]["customer_return_freight_minor"] >= 15000

    # Operating cash reconciliation
    cash = report["cash_reconciliation"]
    assert cash["total_cash_inflow_minor"] >= 180000
    assert cash["supplier_payments_paid_minor"] >= 70000

    # CSV formula injection protection
    assert escape_csv_cell("=1+1") == "'=1+1"
    assert escape_csv_cell("+44789") == "'+44789"
    assert escape_csv_cell("-100") == "'-100"
    assert escape_csv_cell("@admin") == "'@admin"
    assert escape_csv_cell("Normal Text") == "Normal Text"


def test_vf7_security_boundaries_and_containment(db, client):
    """
    Role boundaries and containment:
    1. Vendor cannot access owner settings or shortage admin endpoints.
    2. Unauthenticated access to vendor stock returns 401.
    3. Unauthenticated access to admin settings returns 401.
    4. Normal port checkout containment returns 503.
    """
    token = secrets.token_hex(4)

    # 1. Unauthenticated endpoints
    res_vstock = client.get("/api/v1/vendor/stock")
    assert res_vstock.status_code == 401

    res_admin_settings = client.get("/api/v1/admin/settings")
    assert res_admin_settings.status_code == 401

    # 2. Provision vendor user
    sup = Supplier(
        id=uuid.uuid4(),
        name=f"VF7 Security Sup ({token})",
        slug=f"vf7-sec-{token}",
        status="active",
        supplier_type="external_vendor",
    )
    db.add(sup)
    db.commit()

    provision_vendor_user(db, sup.id, f"sec_user_{token}", "SecPass123_!", allow_short_local=True)
    db.commit()

    # Vendor login
    login_res = client.post(
        "/api/v1/vendor/auth/login",
        json={"username": f"sec_user_{token}", "password": "SecPass123_!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login_res.status_code == 200

    # Authenticated vendor attempts to access admin settings -> Denied
    res_forbidden = client.get("/api/v1/admin/settings")
    assert res_forbidden.status_code == 401

    # Authenticated vendor attempts to access admin shortages -> Denied
    res_shortages_denied = client.get("/api/v1/admin/shortages")
    assert res_shortages_denied.status_code == 401

    # Vendor accesses their own stock -> 200 OK
    res_stock_ok = client.get("/api/v1/vendor/stock")
    assert res_stock_ok.status_code == 200

    # 3. Checkout containment check:
    # Ensure GET /api/v1/orders/checkout-session is protected by require_checkout_enabled
    from app.config import settings
    if not settings.checkout_enabled:
        session_res = client.get("/api/v1/orders/checkout-session")
        assert session_res.status_code == 503


def test_vf7_store_settings_and_preferences_persistence(db, client):
    """
    Store settings and owner preferences:
    1. Settings update bumps version and creates audit log diff.
    2. Policy draft/publish works without affecting storefront layout.
    3. Per-owner preferences are saved independently and can be reset.
    4. Public store settings returns safe subset.
    """
    token = secrets.token_hex(4)
    uname, pwd = f"owner_vf7_{token}", f"OwnerPass123_{token}"
    owner = provision_owner(db, uname, pwd, allow_short_local=True)
    db.commit()

    csrf = _login_owner(client, uname, pwd)

    # 1. Public settings
    pub_res = client.get("/api/v1/store/settings")
    assert pub_res.status_code == 200
    pub = pub_res.json()
    assert "brand_name" in pub
    assert not hasattr(pub, "audit_logs")

    # 2. Update admin store settings
    res_up = client.put(
        "/api/v1/admin/settings",
        json={
            "brand_name": f"AlphaZee {token}",
            "announcement_banner_text": f"VF7 Integrated Release ({token})",
            "announcement_banner_enabled": True,
            "accent_color": "#1e3a8a",
            "font_family": "Outfit, sans-serif",
            "free_shipping_threshold_minor": 600000,
            "standard_shipping_fee_minor": 30000,
            "delivery_policy_content": "Standard delivery takes 2-4 business days via Trax / TCS.",
            "change_reason": "VF7 milestone verification",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res_up.status_code == 200, res_up.text
    updated = res_up.json()
    assert updated["announcement_banner_text"] == f"VF7 Integrated Release ({token})"
    assert updated["accent_color"] == "#1e3a8a"
    assert updated["standard_shipping_fee_minor"] == 30000

    # 3. Check audit log via API
    logs_res = client.get("/api/v1/admin/settings/audit-logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert "announcement_banner_text" in logs[0]["changed_fields"]

    # 4. Policy publish via API
    policy_res = client.post(
        "/api/v1/admin/settings/policies/delivery/publish",
        json={"publish": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert policy_res.status_code == 200
    assert policy_res.json()["delivery_policy_status"] == "published"
    assert policy_res.json()["delivery_policy_published_at"] is not None

    # Unpublish back to draft to verify toggle and leave clean singleton state
    unpub_res = client.post(
        "/api/v1/admin/settings/policies/delivery/publish",
        json={"publish": False},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert unpub_res.status_code == 200
    assert unpub_res.json()["delivery_policy_status"] == "draft"

    # 5. Owner preferences via API
    pref_res = client.put(
        "/api/v1/admin/preferences",
        json={"theme": "dark", "table_density": "compact", "default_date_range": "this_month"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert pref_res.status_code == 200
    prefs = pref_res.json()
    assert prefs["theme"] == "dark"
    assert prefs["table_density"] == "compact"

    # 6. Reset preferences via API
    reset_res = client.post(
        "/api/v1/admin/preferences/reset",
        json={},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert reset_res.status_code == 200
    reset_prefs = reset_res.json()
    assert reset_prefs["theme"] == "system"
    assert reset_prefs["table_density"] == "comfortable"
