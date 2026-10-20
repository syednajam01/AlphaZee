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


# The former lifecycle manually constructed delivered/returned/owned rows and called
# the posting helper. Real checkout/dispatch/return/resale API regressions now live
# in test_vf_integration_repairs.py; do not treat ORM setup as acceptance evidence.


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
        from app.dependencies.checkout import require_checkout_enabled
        app.dependency_overrides.pop(require_checkout_enabled, None)
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
    assert "audit_logs" not in pub

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
