"""
test_analytics.py — Integration tests for owner profit & loss, COGS, and unit economics analytics.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
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
def setup_store_data(db_session: Session):
    col = Collection(
        id="apparel-col",
        name="Apparel Collection",
        slug="apparel-col",
        is_active=True,
        display_order=1,
    )
    db_session.add(col)
    db_session.flush()

    prod = Product(
        id="prod-heavyweight-tee",
        collection_id=col.id,
        title="Heavyweight Boxy Tee",
        slug="heavyweight-boxy-tee",
        is_active=True,
    )
    db_session.add(prod)
    db_session.flush()

    var1 = Variant(
        product_id=prod.id,
        sku="TEE-M-WHT",
        size="M",
        color="White",
        price_minor=350000,  # PKR 3,500
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    var2 = Variant(
        product_id=prod.id,
        sku="TEE-L-BLK",
        size="L",
        color="Black",
        price_minor=400000,  # PKR 4,000
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    db_session.add_all([var1, var2])
    db_session.flush()

    sup = Supplier(
        name="Lahore Knitwear Ltd",
        slug="lahore-knitwear",
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
    sv2 = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var2.id,
        supplier_cost_minor=220000,  # PKR 2,200 COGS
        active=True,
    )
    db_session.add_all([sv1, sv2])
    db_session.flush()

    bal1 = InventoryBalance(supplier_variant_id=sv1.id, on_hand=20, version=1)
    bal2 = InventoryBalance(supplier_variant_id=sv2.id, on_hand=20, version=1)
    db_session.add_all([bal1, bal2])
    db_session.commit()

    return {
        "var1": var1,
        "var2": var2,
        "sv1": sv1,
        "sv2": sv2,
    }


def test_profit_loss_analytics_computes_exact_cogs_and_gross_profit(
    client: TestClient,
    db_session: Session,
    setup_store_data: dict,
):
    var1 = setup_store_data["var1"]
    var2 = setup_store_data["var2"]

    # 1. Place Order 1: 1x var1 (PKR 3,500, COGS PKR 2,000)
    order1 = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Customer One",
            customer_phone="03001111111",
            shipping_address_line1="DHA Phase 5",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    # 2. Place Order 2: 2x var2 (PKR 8,000, COGS PKR 4,400)
    order2 = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Customer Two",
            customer_phone="03002222222",
            shipping_address_line1="Gulshan",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var2.id, quantity=2)],
        ),
    )
    db_session.commit()

    # Confirm Order 1 supplier acceptance
    client.post(f"/api/v1/admin/orders/{order1.id}/confirm-supplier")

    # Dispatch Order 1 via Trax (Courier cost PKR 250 = 25000 paisas)
    d1 = client.post(
        f"/api/v1/admin/orders/{order1.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-101",
            "shipping_cost_minor": 25000,
        },
    )
    s1_id = d1.json()["id"]

    # Verify Order 2 payment and confirm supplier acceptance
    client.post(f"/api/v1/admin/orders/{order2.id}/verify-payment")
    client.post(f"/api/v1/admin/orders/{order2.id}/confirm-supplier")

    # Dispatch Order 2 via Leopards (Courier cost PKR 200 = 20000 paisas)
    d2 = client.post(
        f"/api/v1/admin/orders/{order2.id}/dispatch",
        json={
            "courier_code": "leopards",
            "tracking_number": "LEO-202",
            "shipping_cost_minor": 20000,
        },
    )
    s2_id = d2.json()["id"]

    # Deliver Order 1
    client.post(
        f"/api/v1/admin/shipments/{s1_id}/status",
        json={"status": "delivered"},
    )

    # Order 2 turns into RTO (Courier return penalty PKR 150 = 15000 paisas)
    client.post(
        f"/api/v1/admin/shipments/{s2_id}/status",
        json={
            "status": "rto_delivered",
            "rto_reason": "Address incomplete",
            "rto_courier_cost_minor": 15000,
        },
    )

    # Fetch Profit & Loss report
    res = client.get("/api/v1/admin/analytics/profit-loss")
    assert res.status_code == 200
    data = res.json()

    # Realized Gross Revenue from successful/in-flight orders (Order 1: 350000; Order 2 RTO has 0 revenue)
    assert data["gross_revenue_minor"] == 350000
    assert data["formatted_gross_revenue"] == "PKR 3,500"

    # COGS for fulfilled orders: 1x 200000 = 200000 paisas
    assert data["cogs_minor"] == 200000
    assert data["formatted_cogs"] == "PKR 2,000"

    # Courier Expenses: Outbound (25000 + 20000) + RTO (15000) = 60000 paisas
    assert data["outbound_courier_cost_minor"] == 45000
    assert data["rto_courier_cost_minor"] == 15000
    assert data["total_courier_expenses_minor"] == 60000
    assert data["formatted_courier_expenses"] == "PKR 600"

    # Gross Profit = 350,000 - 200,000 - 60,000 = 90,000 paisas (PKR 900)
    assert data["gross_profit_minor"] == 90000
    assert data["formatted_gross_profit"] == "PKR 900"
    assert data["gross_margin_percent"] == 25.71

    # RTO Metrics: 1 RTO out of 2 shipments = 50.0%
    assert data["total_shipments_count"] == 2
    assert data["delivered_shipments_count"] == 1
    assert data["rto_shipments_count"] == 1
    assert data["rto_rate_percent"] == 50.0


def test_marketing_attribution_analytics(
    client: TestClient,
    db_session: Session,
    setup_store_data: dict,
):
    var1 = setup_store_data["var1"]

    # Place order with UTM tracking and coupon
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Ali Khan",
            customer_phone="03009998877",
            shipping_address_line1="Gulberg",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            utm_source="instagram",
            utm_medium="reels",
            utm_campaign="summer_sale",
            items=[OrderItemDTO(variant_id=var1.id, quantity=1)],
        ),
    )
    db_session.commit()

    res = client.get("/api/v1/admin/analytics/marketing")
    assert res.status_code == 200
    data = res.json()
    assert data["total_campaigns"] >= 1
    ig_channel = next(
        (c for c in data["channels"] if c["utm_source"] == "instagram"), None
    )
    assert ig_channel is not None
    assert ig_channel["utm_campaign"] == "summer_sale"
    assert ig_channel["orders_count"] == 1
    assert ig_channel["revenue_minor"] == 350000

