"""
test_financial_reporting.py — Verification of Phase F (Accurate Financial Reporting & COD Remittance Guards).

Covers:
1. Placed but unverified/uncollected orders excluded from realized revenue and COGS.
2. Verified bank payments and delivered COD collections included in revenue.
3. Completed customer returns deduct refund amounts from net revenue and profit.
4. Zero or negative COD remittances rejected with HTTP 422.
5. Partial COD remittances rejected with HTTP 422 unless explicit is_partial flag and reason are provided.
6. Recording remittance by order ID endpoint and model properties.
"""

import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.orders import Order
from app.models.returns import OrderReturn
from app.models.suppliers import Supplier
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order


@pytest.fixture
def client(db_session: Session, admin_headers):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, headers=admin_headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def store_catalog(db_session: Session) -> dict:
    col = Collection(
        id="apparel-fin-col",
        name="Apparel Collection",
        slug="apparel-fin-col",
        is_active=True,
        display_order=1,
    )
    db_session.add(col)
    db_session.flush()

    prod = Product(
        id="prod-fin-tee",
        collection_id=col.id,
        title="Heavyweight Boxy Tee",
        slug="fin-heavyweight-boxy-tee",
        is_active=True,
    )
    db_session.add(prod)
    db_session.flush()

    var1 = Variant(
        product_id=prod.id,
        sku="FIN-TEE-M-WHT",
        size="M",
        color="White",
        price_minor=350000,  # PKR 3,500
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    db_session.add(var1)
    db_session.flush()

    sup = Supplier(
        name="Lahore Fin Knitwear Ltd",
        slug="lahore-fin-knitwear",
        status="active",
    )
    db_session.add(sup)
    db_session.flush()

    sv1 = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var1.id,
        supplier_cost_minor=200000,  # PKR 2,000 COGS
        active=True,
    )
    db_session.add(sv1)
    db_session.flush()

    bal1 = InventoryBalance(supplier_variant_id=sv1.id, on_hand=50, version=1)
    db_session.add(bal1)
    db_session.commit()

    return {
        "var1": var1,
        "sv1": sv1,
    }


def test_unpaid_placed_orders_excluded_from_revenue(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    # 1. Place COD order (uncollected, status=placed, payment_status=pending)
    place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Tariq Jamil",
            customer_phone="03001112233",
            shipping_address_line1="DHA Phase 5",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )

    # 2. Place Bank Transfer order (unverified, status=placed, payment_status=pending)
    place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Hamza Abbasi",
            customer_phone="03004445566",
            shipping_address_line1="F-7 Markaz",
            shipping_city="Islamabad",
            shipping_province="Islamabad Capital",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    # Query Profit & Loss report
    res = client.get("/api/v1/admin/analytics/profit-loss")
    assert res.status_code == 200
    data = res.json()

    # Realized revenue must be 0 because neither order is paid/collected yet
    assert data["gross_revenue_minor"] == 0
    assert data["cogs_minor"] == 0
    assert data["gross_profit_minor"] == 0


def test_verified_bank_and_cod_collected_included_in_revenue(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    # 1. Place and verify Bank Transfer order
    bank_order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Sara Ahmed",
            customer_phone="03007778899",
            shipping_address_line1="Clifton Block 2",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    # Verify payment via admin API
    res_pay = client.post(
        f"/api/v1/admin/orders/{bank_order.id}/verify-payment",
        json={"reference": "MEEZAN-FT-998811"},
    )
    assert res_pay.status_code == 200

    # Query Profit & Loss report: Bank order should now be recognized as revenue
    res = client.get("/api/v1/admin/analytics/profit-loss")
    assert res.status_code == 200
    data = res.json()
    assert data["gross_revenue_minor"] == bank_order.total_minor
    assert data["cogs_minor"] == 200000  # supplier cost for 1 unit

    # 2. Place COD order, confirm supplier, dispatch, and mark delivered
    cod_order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Bilal Aslam",
            customer_phone="03003334455",
            shipping_address_line1="Satellite Town",
            shipping_city="Rawalpindi",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    client.post(f"/api/v1/admin/orders/{cod_order.id}/confirm-supplier")

    d1 = client.post(
        f"/api/v1/admin/orders/{cod_order.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-BILAL-01",
            "shipping_cost_minor": 25000,
        },
    )
    assert d1.status_code in (200, 201)
    shipment_id = d1.json()["id"]

    res_deliv = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "delivered"},
    )
    assert res_deliv.status_code == 200

    # Both orders now realized: bank_order + cod_order
    res = client.get("/api/v1/admin/analytics/profit-loss")
    assert res.status_code == 200
    data = res.json()
    assert data["gross_revenue_minor"] == bank_order.total_minor + cod_order.total_minor
    assert data["cogs_minor"] == 400000  # 2 units * 200,000


def test_completed_returns_deducted_from_revenue(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    # Place and verify bank order
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Zainab Bibi",
            customer_phone="03001239876",
            shipping_address_line1="Gulberg III",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()
    client.post(f"/api/v1/admin/orders/{order.id}/verify-payment")

    # Pre-return check
    res_before = client.get("/api/v1/admin/analytics/profit-loss").json()
    gross_before = res_before["gross_revenue_minor"]
    assert gross_before == order.total_minor

    # Add a completed customer return with PKR 1,000 refund (100000 paisas)
    order_line = order.lines[0]
    ret = OrderReturn(
        order_id=order.id,
        order_line_id=order_line.id,
        return_type="refund_bank_transfer",
        reason="damaged_defective",
        status="completed",
        refund_amount_minor=100000,
        refund_reference="REFUND-HBL-991",
    )
    db_session.add(ret)
    db_session.commit()

    res_after = client.get("/api/v1/admin/analytics/profit-loss").json()
    assert res_after["gross_revenue_minor"] == gross_before
    assert res_after.get("refund_total_minor") == 100000
    assert res_after.get("net_revenue_minor") == gross_before - 100000
    assert res_after["gross_profit_minor"] == res_before["gross_profit_minor"] - 100000


def test_zero_or_negative_cod_remittance_rejected_with_422(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Usman Ali",
            customer_phone="03005556677",
            shipping_address_line1="Model Town",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")
    d = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-USMAN-01",
            "shipping_cost_minor": 20000,
        },
    )
    assert d.status_code in (200, 201)
    shipment_id = d.json()["id"]

    # Zero remittance must be rejected with 422
    res_zero = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={"remitted_amount_minor": 0, "reference": "BANK-DEP-00"},
    )
    assert res_zero.status_code == 422

    # Negative remittance must be rejected with 422
    res_neg = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={"remitted_amount_minor": -50000, "reference": "BANK-DEP-NEG"},
    )
    assert res_neg.status_code == 422


def test_partial_cod_remittance_requires_explicit_flag_and_reason(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Farhan Saeed",
            customer_phone="03008889900",
            shipping_address_line1="Hayatabad",
            shipping_city="Peshawar",
            shipping_province="Khyber Pakhtunkhwa",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")
    d = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-FARHAN-01",
            "shipping_cost_minor": 25000,
        },
    )
    assert d.status_code in (200, 201)
    shipment_id = d.json()["id"]
    cod_amount = d.json()["cod_amount_minor"]
    assert cod_amount > 0

    partial_amount = cod_amount - 50000  # 500 PKR short

    # 1. Partial remittance without is_partial flag -> 422
    res_no_flag = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={
            "remitted_amount_minor": partial_amount,
            "reference": "BANK-SHORT-1",
        },
    )
    assert res_no_flag.status_code == 422

    # 2. Partial remittance with is_partial=True but missing partial_reason -> 422
    res_no_reason = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={
            "remitted_amount_minor": partial_amount,
            "reference": "BANK-SHORT-2",
            "is_partial": True,
            "partial_reason": "",
        },
    )
    assert res_no_reason.status_code == 422

    # 3. Partial remittance with is_partial=True and clear partial_reason -> 200
    res_success = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={
            "remitted_amount_minor": partial_amount,
            "reference": "TRAX-SETTLE-OCT-01",
            "is_partial": True,
            "partial_reason": "Courier deducted damaged packaging penalty",
        },
    )
    assert res_success.status_code == 200
    data = res_success.json()
    assert data["cod_remitted_amount_minor"] == partial_amount
    assert data["cod_remittance_status"] == "remitted"
    assert data["is_partial_remittance"] is True
    assert data["remittance_amount_minor"] == partial_amount


def test_mark_cod_remitted_by_order_id_endpoint(
    client: TestClient,
    db_session: Session,
    store_catalog: dict,
):
    var1 = store_catalog["var1"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Kashif Mehmood",
            customer_phone="03006667788",
            shipping_address_line1="Gulshan-e-Iqbal",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")
    d = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-KASHIF-01",
            "shipping_cost_minor": 20000,
        },
    )
    assert d.status_code in (200, 201)
    cod_amount = d.json()["cod_amount_minor"]

    # Remit full amount by order ID endpoint
    res = client.post(
        f"/api/v1/admin/orders/{order.id}/remittance",
        json={
            "remitted_amount_minor": cod_amount,
            "reference": "FULL-REMIT-01",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["cod_remitted_amount_minor"] == cod_amount
    assert data["cod_remittance_status"] == "remitted"
    assert data["is_partial_remittance"] is False
    assert data["remittance_amount_minor"] == cod_amount
