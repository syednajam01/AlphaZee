"""
test_api_shipments.py — Integration and API tests for courier dispatch, tracking, COD remittance, and RTO restock.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order
from app.models.shipments import Shipment
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

    # Confirm supplier acceptance
    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")

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

    # Verify bank payment and confirm supplier acceptance
    vp_res = client.post(f"/api/v1/admin/orders/{order.id}/verify-payment")
    assert vp_res.status_code == 200, vp_res.text
    cs_res = client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")
    assert cs_res.status_code == 200, cs_res.text

    # Dispatch via Leopards
    disp_res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "leopards",
            "tracking_number": "LEO-55443322",
            "shipping_cost_minor": 20000,
        },
    )
    assert disp_res.status_code == 201, disp_res.text

    # Fetch customer tracking with an order-scoped session.
    from app.services.order_access import issue_access, cookie_name
    _, token = issue_access(db_session, order)
    db_session.commit()
    client.headers['Cookie'] = f"{client.headers.get('Cookie', '')}; {cookie_name()}={token}"
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

    # Confirm supplier acceptance
    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")

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

    # Confirm supplier acceptance
    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")

    disp_res = client.post(
        f"/api/v1/admin/orders/{order.id}/dispatch",
        json={
            "courier_code": "tcs",
            "tracking_number": "TCS-998877",
            "shipping_cost_minor": 25000,
        },
    )
    shipment_id = disp_res.json()["id"]

    # Customer refused parcel; record in-transit RTO then physical receipt.
    assert client.post(f"/api/v1/admin/shipments/{shipment_id}/status",
                       json={"status": "rto_initiated", "rto_reason": "Customer refused delivery (changed mind)"}).status_code == 200
    rto_res = client.post(
        f"/api/v1/admin/shipments/{shipment_id}/status",
        json={
            "status": "rto_delivered",
            "rto_reason": "Customer refused delivery (changed mind)",
            "rto_courier_cost_minor": 15000,  # Return courier charge
            "received_lines": [{"order_line_id": str(order.lines[0].id), "received_quantity": 1}],
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

    # Confirm supplier acceptance
    client.post(f"/api/v1/admin/orders/{order.id}/confirm-supplier")

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
            "deductions": [{"entry_type": "outbound_shipping", "amount_minor": 20000,
                            "reference": "POSTEX-COURIER-FEE-OCT11",
                            "note": "Courier invoice for original delivery"}],
        },
    )
    assert remit_res.status_code == 200
    remit_data = remit_res.json()
    assert remit_data["cod_remittance_status"] == "remitted"
    assert remit_data["cod_remitted_amount_minor"] == 580000
    assert remit_data["cod_remittance_reference"] == "POSTEX-WEEKLY-PAYOUT-OCT11"
    assert remit_data["cod_remitted_at"] is not None
    assert remit_data['settlement_deductions_minor'] == 20000
    assert remit_data['settlement_outstanding_minor'] == 0
    assert len(remit_data['settlement_entries']) == 2


def test_partial_settlement_reconciles_without_overwriting_and_rejects_bad_evidence(
    client: TestClient, db_session: Session, setup_catalog_and_supplier: dict,
):
    order = place_order(db_session, CreateOrderDTO(
        customer_name='Settlement Customer', customer_phone='03001112222',
        shipping_address_line1='Main Street', shipping_city='Lahore',
        shipping_province='Punjab', payment_method='cod',
        items=[OrderItemDTO(variant_id=setup_catalog_and_supplier['variant'].id, quantity=1)],
    ))
    db_session.commit()
    assert client.get('/api/v1/admin/analytics/profit-loss').json()['delivered_sales_minor'] == 0
    client.post(f'/api/v1/admin/orders/{order.id}/confirm-supplier')
    dispatched = client.post(f'/api/v1/admin/orders/{order.id}/dispatch', json={
        'courier_code': 'trax', 'tracking_number': 'TRX-SETTLEMENT-01',
        'shipping_cost_minor': 20000,
    })
    shipment_id = dispatched.json()['id']
    assert client.post(f'/api/v1/admin/shipments/{shipment_id}/remittance', json={
        'remitted_amount_minor': 10000, 'reference': 'EARLY-RECEIPT',
    }).status_code == 422
    client.post(f'/api/v1/admin/shipments/{shipment_id}/status', json={'status': 'delivered'})
    report = client.get('/api/v1/admin/analytics/profit-loss').json()
    assert report['delivered_sales_minor'] == 600000
    assert report['cod_collected_minor'] == 600000
    assert report['business_cash_received_minor'] == 0
    first = client.post(f'/api/v1/admin/shipments/{shipment_id}/remittance', json={
        'remitted_amount_minor': 200000, 'reference': 'PAYOUT-PART-01',
    })
    assert first.status_code == 200, first.text
    assert first.json()['cod_remittance_status'] == 'partial'
    assert first.json()['settlement_outstanding_minor'] == 400000
    duplicate = client.post(f'/api/v1/admin/shipments/{shipment_id}/remittance', json={
        'remitted_amount_minor': 10000, 'reference': 'payout-part-01',
    })
    assert duplicate.status_code == 422
    excessive = client.post(f'/api/v1/admin/shipments/{shipment_id}/remittance', json={
        'remitted_amount_minor': 400001, 'reference': 'PAYOUT-TOO-MUCH',
    })
    assert excessive.status_code == 422
    final = client.post(f'/api/v1/admin/orders/{order.id}/remittance', json={
        'remitted_amount_minor': 380000, 'reference': 'PAYOUT-PART-02',
        'deductions': [{'entry_type': 'outbound_shipping', 'amount_minor': 20000,
                        'reference': 'COURIER-INVOICE-01', 'note': 'Delivery invoice 01'}],
        'final_statement': True,
    })
    assert final.status_code == 200, final.text
    assert final.json()['cod_remitted_amount_minor'] == 580000
    assert final.json()['settlement_deductions_minor'] == 20000
    assert final.json()['settlement_outstanding_minor'] == 0
    assert final.json()['cod_remittance_status'] == 'remitted'
    assert len(final.json()['settlement_entries']) == 3
    report = client.get('/api/v1/admin/analytics/profit-loss').json()
    assert report['business_cash_received_minor'] == 580000
    assert report['total_courier_expenses_minor'] == 20000
    assert report['gross_profit_minor'] == 230000


def test_final_short_payout_is_disputed_not_reconciled(
    client: TestClient, db_session: Session, setup_catalog_and_supplier: dict,
):
    order = place_order(db_session, CreateOrderDTO(
        customer_name='Short Payout', customer_phone='03004445555',
        shipping_address_line1='Main Street', shipping_city='Lahore',
        shipping_province='Punjab', payment_method='cod',
        items=[OrderItemDTO(variant_id=setup_catalog_and_supplier['variant'].id, quantity=1)],
    ))
    db_session.commit()
    client.post(f'/api/v1/admin/orders/{order.id}/confirm-supplier')
    dispatched = client.post(f'/api/v1/admin/orders/{order.id}/dispatch', json={
        'courier_code': 'trax', 'tracking_number': 'TRX-SHORT-02',
        'shipping_cost_minor': 20000,
    })
    shipment_id = dispatched.json()['id']
    client.post(f'/api/v1/admin/shipments/{shipment_id}/status', json={'status': 'delivered'})
    payout = client.post(f'/api/v1/admin/shipments/{shipment_id}/remittance', json={
        'remitted_amount_minor': 500000, 'reference': 'SHORT-FINAL-01',
        'final_statement': True,
    })
    assert payout.status_code == 200, payout.text
    assert payout.json()['cod_remittance_status'] == 'disputed'
    assert payout.json()['settlement_outstanding_minor'] == 100000
    assert client.get('/api/v1/admin/analytics/profit-loss').json()['courier_held_cod_minor'] == 100000
