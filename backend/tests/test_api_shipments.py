"""
test_api_shipments.py — Integration and API tests for courier dispatch, tracking, COD remittance, and RTO restock.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order
from app.models.shipments import Shipment
from app.models.suppliers import Supplier
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order


@pytest.fixture
def client(db_session: Session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def setup_catalog_and_supplier(db_session: Session):
    col = Collection(
        id="dispatch-col",
        name="Dispatch Collection",
        slug="dispatch-col",
        is_active=True,
        display_order=1,
    )
    db_session.add(col)
    db_session.flush()

    prod = Product(
        id="prod-courier-hoodie",
        collection_id=col.id,
        title="Oversized Courier Hoodie",
        slug="oversized-courier-hoodie",
        is_active=True,
    )
    db_session.add(prod)
    db_session.flush()

    var = Variant(
        product_id=prod.id,
        sku="HOODIE-L-BLK",
        size="L",
        color="Black",
        price_minor=600000,  # PKR 6,000
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    db_session.add(var)
    db_session.flush()

    sup = Supplier(
        name="KHI Apparel Co",
        slug="khi-apparel-co",
        status="active",
    )
    db_session.add(sup)
    db_session.flush()

    sv = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var.id,
        supplier_cost_minor=350000,  # PKR 3,500
        active=True,
    )
    db_session.add(sv)
    db_session.flush()

    balance = InventoryBalance(
        supplier_variant_id=sv.id,
        on_hand=10,
        version=1,
    )
    db_session.add(balance)
    db_session.commit()

    return {
        "collection": col,
        "product": prod,
        "variant": var,
        "supplier": sup,
        "supplier_variant": sv,
        "balance": balance,
    }


def test_order_dispatch_creates_shipment_and_updates_order_status(
    client: TestClient,
    db_session: Session,
    setup_catalog_and_supplier: dict,
):
    var = setup_catalog_and_supplier["variant"]

    # 1. Place COD order
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Ali Khan",
            customer_phone="03001234567",
            customer_email="ali@example.com",
            shipping_address_line1="House 12, Street 4",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.commit()
    assert order.order_status == "placed"

    # 2. Dispatch order via Trax Logistics
    res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "trax",
            "tracking_number": "TRX-987654321",
            "shipping_cost_minor": 25000,  # PKR 250
            "tracking_url": "https://trax.pk/tracking?num=TRX-987654321",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["courier_code"] == "trax"
    assert data["tracking_number"] == "TRX-987654321"
    assert data["shipping_cost_minor"] == 25000
    assert data["cod_amount_minor"] == 600000
    assert data["cod_remittance_status"] == "pending_remittance"
    assert data["status"] == "dispatched"

    # 3. Check order status was updated
    db_session.refresh(order)
    assert order.order_status == "dispatched"


def test_public_order_tracking_endpoint_returns_courier_details(
    client: TestClient,
    db_session: Session,
    setup_catalog_and_supplier: dict,
):
    var = setup_catalog_and_supplier["variant"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Zainab Tariq",
            customer_phone="03219876543",
            shipping_address_line1="Flat 4B, Clifton",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.commit()

    # Dispatch via Leopards
    client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "leopards",
            "tracking_number": "LEO-55443322",
            "shipping_cost_minor": 20000,
        },
    )

    # Fetch public tracking
    res = client.get(f"/api/v1/orders/{order.order_number}?phone=03219876543")
    assert res.status_code == 200
    track_data = res.json()
    assert track_data["order_status"] == "dispatched"
    assert len(track_data["shipments"]) == 1
    ship = track_data["shipments"][0]
    assert ship["courier_name"] == "Leopards Courier"
    assert ship["tracking_number"] == "LEO-55443322"
    assert ship["status"] == "dispatched"


def test_shipment_status_delivered_fulfills_stock_and_marks_cod_payment_verified(
    client: TestClient,
    db_session: Session,
    setup_catalog_and_supplier: dict,
):
    var = setup_catalog_and_supplier["variant"]
    sv = setup_catalog_and_supplier["supplier_variant"]
    balance = setup_catalog_and_supplier["balance"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Usman Riaz",
            customer_phone="03335554433",
            shipping_address_line1="Office 202, Blue Area",
            shipping_city="Islamabad",
            shipping_province="Islamabad Capital Territory",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=2)],
        ),
    )
    db_session.commit()

    # Initial physical = 10, held = 2, available = 8
    db_session.refresh(balance)
    assert balance.on_hand == 10

    # Dispatch
    disp_res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "call_courier",
            "tracking_number": "CC-112233",
            "shipping_cost_minor": 30000,
        },
    )
    shipment_id = disp_res.json()["id"]

    # Mark delivered
    del_res = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "delivered"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "delivered"

    db_session.refresh(order)
    assert order.order_status == "delivered"
    assert order.payment_status == "verified"  # COD payment collected upon delivery

    # Check physical balance decremented from 10 to 8
    db_session.refresh(balance)
    assert balance.on_hand == 8


def test_shipment_rto_return_restocks_inventory(
    client: TestClient,
    db_session: Session,
    setup_catalog_and_supplier: dict,
):
    var = setup_catalog_and_supplier["variant"]
    balance = setup_catalog_and_supplier["balance"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Hamza Sheikh",
            customer_phone="03124443322",
            shipping_address_line1="Model Town",
            shipping_city="Gujranwala",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.commit()

    disp_res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "tcs",
            "tracking_number": "TCS-998877",
            "shipping_cost_minor": 25000,
        },
    )
    shipment_id = disp_res.json()["id"]

    # Customer refused parcel -> RTO Delivered
    rto_res = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={
            "status": "rto_delivered",
            "rto_reason": "Customer refused delivery (changed mind)",
            "rto_courier_cost_minor": 15000,  # Return courier charge
        },
    )
    assert rto_res.status_code == 200
    rto_data = rto_res.json()
    assert rto_data["status"] == "rto_delivered"
    assert rto_data["rto_reason"] == "Customer refused delivery (changed mind)"
    assert rto_data["rto_courier_cost_minor"] == 15000

    db_session.refresh(order)
    assert order.order_status == "rto"


def test_cod_remittance_lifecycle(
    client: TestClient,
    db_session: Session,
    setup_catalog_and_supplier: dict,
):
    var = setup_catalog_and_supplier["variant"]

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Bilal Aslam",
            customer_phone="03451122334",
            shipping_address_line1="Gulberg III",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.commit()

    disp_res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "postex",
            "tracking_number": "PSTX-776655",
            "shipping_cost_minor": 20000,
        },
    )
    shipment_id = disp_res.json()["id"]

    # 1. Deliver
    client.post(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={"status": "delivered"},
    )

    # 2. Record weekly bank remittance
    remit_res = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/remittance",
        json={
            "remitted_amount_minor": 580000,  # PKR 5,800 (net of 200 courier fee)
            "reference": "POSTEX-WEEKLY-PAYOUT-OCT11",
        },
    )
    assert remit_res.status_code == 200
    remit_data = remit_res.json()
    assert remit_data["cod_remittance_status"] == "remitted"
    assert remit_data["cod_remitted_amount_minor"] == 580000
    assert remit_data["cod_remittance_reference"] == "POSTEX-WEEKLY-PAYOUT-OCT11"
    assert remit_data["cod_remitted_at"] is not None
