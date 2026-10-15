"""
test_exchange_flow.py — Verification of Phase G order access and replacement fulfillment.

Covers:
1. Phone without a scoped session cannot submit a return.
2. A scoped session allows a return request.
3. Exchange approval reserves replacement stock once; dispatch and RTO touch only replacement stock.
4. Insufficient replacement stock rolls approval back atomically.
5. A bank refund does not create replacement fulfillment.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment
from app.models.suppliers import Supplier
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order, confirm_supplier_acceptance, deliver_order
from app.services.shipments import create_shipment
from app.services.order_access import issue_access, cookie_name


def _authorize(client, db, order):
    _, token = issue_access(db, order)
    db.commit()
    client.headers['Cookie'] = f"{client.headers.get('Cookie', '')}; {cookie_name()}={token}"


def _deliver(db, order):
    confirm_supplier_acceptance(db, order_id=order.id)
    create_shipment(db, order_id=order.id, courier_code='manual',
                    tracking_number=f'EX-ORIG-{uuid.uuid4().hex[:8]}')
    deliver_order(db, order_id=order.id)
    db.commit()


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
def setup_catalog(db_session: Session) -> dict:
    col = Collection(
        id=f"col-exch-{uuid.uuid4().hex[:6]}",
        name="Exchange Test Collection",
        slug=f"exch-col-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(col)
    db_session.flush()

    prod = Product(
        id=f"prod-exch-{uuid.uuid4().hex[:6]}",
        title="Oversized Hoodie",
        slug=f"oversized-hoodie-{uuid.uuid4().hex[:6]}",
        collection_id=col.id,
        is_active=True,
    )
    db_session.add(prod)
    db_session.flush()

    var_m = Variant(
        product_id=prod.id,
        sku=f"HOODIE-M-{uuid.uuid4().hex[:6]}",
        size="M",
        color="Black",
        price_minor=500000,  # PKR 5,000
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    var_l = Variant(
        product_id=prod.id,
        sku=f"HOODIE-L-{uuid.uuid4().hex[:6]}",
        size="L",
        color="Black",
        price_minor=500000,  # PKR 5,000
        availability=AvailabilityStatus.AVAILABLE,
        is_active=True,
    )
    db_session.add_all([var_m, var_l])
    db_session.flush()

    sup = Supplier(
        name=f"Exchange Supplier {uuid.uuid4().hex[:6]}",
        slug=f"exch-sup-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db_session.add(sup)
    db_session.flush()

    sv_m = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var_m.id,
        supplier_cost_minor=300000,
        active=True,
    )
    sv_l = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var_l.id,
        supplier_cost_minor=300000,
        active=True,
    )
    db_session.add_all([sv_m, sv_l])
    db_session.flush()

    bal_m = InventoryBalance(supplier_variant_id=sv_m.id, on_hand=10, version=1)
    bal_l = InventoryBalance(supplier_variant_id=sv_l.id, on_hand=5, version=1)
    db_session.add_all([bal_m, bal_l])
    db_session.commit()

    return {
        "var_m": var_m,
        "var_l": var_l,
        "sv_m": sv_m,
        "sv_l": sv_l,
        "bal_m": bal_m,
        "bal_l": bal_l,
    }


def test_return_request_with_wrong_phone_rejected_with_403(
    client: TestClient,
    db_session: Session,
    setup_catalog: dict,
):
    var_m = setup_catalog["var_m"]
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Adeel Akhtar",
            customer_phone="03001234567",
            shipping_address_line1="DHA Phase 6",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=1)],
        ),
    )
    _deliver(db_session, order)
    line_id = order.lines[0].id

    # Customer tries to file return using a different phone number
    res = client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line_id),
            "quantity": 1,
            "customer_phone": "03009998877",  # WRONG PHONE
            "return_type": "refund_bank_transfer",
            "reason": "changed_mind",
            "customer_notes": "No longer need item",
        },
    )
    assert res.status_code == 404


def test_return_request_with_valid_phone_accepted(
    client: TestClient,
    db_session: Session,
    setup_catalog: dict,
):
    var_m = setup_catalog["var_m"]
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Nadia Ali",
            customer_phone="03007654321",
            shipping_address_line1="Gulshan-e-Iqbal",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=1)],
        ),
    )
    _deliver(db_session, order)
    _authorize(client, db_session, order)
    line_id = order.lines[0].id

    # A scoped session authorizes the request; phone is ignored.
    res = client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line_id),
            "quantity": 1,
            "customer_phone": "+92 300 7654321",  # Un-normalized input
            "return_type": "refund_bank_transfer",
            "reason": "damaged_defective",
            "customer_notes": "Defective zipper",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "requested"
    assert data["order_id"] == str(order.id)


def test_approve_exchange_creates_replacement_reservation_and_shipment(
    client: TestClient,
    db_session: Session,
    setup_catalog: dict,
):
    var_m = setup_catalog["var_m"]
    var_l = setup_catalog["var_l"]
    sv_l = setup_catalog["sv_l"]
    bal_l = setup_catalog["bal_l"]

    initial_l_on_hand = bal_l.on_hand
    assert initial_l_on_hand == 5

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Faraz Shah",
            customer_phone="03125554433",
            shipping_address_line1="Blue Area",
            shipping_city="Islamabad",
            shipping_province="Islamabad Capital",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=1)],
        ),
    )
    _deliver(db_session, order)
    _authorize(client, db_session, order)
    line_id = order.lines[0].id

    # 1. Customer submits size exchange request from M to L
    req_res = client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line_id),
            "quantity": 1,
            "customer_phone": "03125554433",
            "return_type": "size_exchange",
            "reason": "size_too_small",
            "exchange_variant_id": var_l.id,
            "customer_notes": "Need larger size L",
        },
    )
    assert req_res.status_code == 201
    return_id = req_res.json()["id"]

    # Approval creates exactly one held replacement allocation.
    app_res = client.post(f"/api/v1/admin/returns/{return_id}/approve")
    assert app_res.status_code == 200, app_res.text
    assert client.post(f"/api/v1/admin/returns/{return_id}/approve").status_code == 200

    # 3. Verify replacement reservation created for variant L
    res_stmt = db_session.query(StockReservation).filter(
        StockReservation.supplier_variant_id == sv_l.id,
        StockReservation.stage == "held",
    )
    res_record = res_stmt.first()
    assert res_record is not None
    assert db_session.get(OrderLine, res_record.order_line_id).fulfillment_kind == 'replacement'

    # 4. Verify replacement shipment created for the order
    ship_stmt = db_session.query(Shipment).filter(
        Shipment.order_id == order.id,
        Shipment.status == "booked",
    )
    assert ship_stmt.first() is None
    assert client.post(f'/api/v1/admin/returns/{return_id}/receive',
                       json={'received_quantity': 1}).status_code == 200
    assert client.post(f'/api/v1/admin/returns/{return_id}/inspect',
                       json={'sellable_quantity': 1, 'damaged_quantity': 0}).status_code == 200
    dispatched = client.post(f'/api/v1/admin/returns/{return_id}/dispatch-replacement',
                             json={'courier_code': 'manual', 'tracking_number': 'REPL-12345'})
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()['cod_amount_minor'] == 0
    db_session.refresh(bal_l)
    assert bal_l.on_hand == initial_l_on_hand - 1
    assert order.order_status == 'delivered'
    assert order.payment_status == 'verified'
    shipment_id = dispatched.json()['id']
    delivered = client.post(f'/api/v1/admin/shipments/{shipment_id}/status',
                            json={'status': 'delivered'})
    assert delivered.status_code == 200, delivered.text
    assert order.order_status == 'delivered'
    assert order.payment_status == 'verified'
    assert client.post(f'/api/v1/admin/shipments/{shipment_id}/status',
                       json={'status': 'rto_initiated'}).status_code == 200
    received = client.post(f'/api/v1/admin/shipments/{shipment_id}/status', json={
        'status': 'rto_delivered', 'received_lines': [
            {'order_line_id': str(res_record.order_line_id), 'received_quantity': 1}]})
    assert received.status_code == 200, received.text
    pending = next(row for row in client.get('/api/v1/admin/returns').json() if row['id'] == return_id)
    assert pending['replacement_rto_inspected_at'] is None
    assert pending['replacement_stock_reconciliation_status'] != 'legacy_review'
    inspected = client.post(f'/api/v1/admin/shipments/{shipment_id}/inspect-rto', json={
        'lines': [{'order_line_id': str(res_record.order_line_id), 'sellable_quantity': 1,
                   'damaged_quantity': 0}], 'notes': 'Returned unopened'})
    assert inspected.status_code == 200, inspected.text
    # The test shares one session across HTTP calls; emulate a new request's
    # relationship load after the independent shipment mutation.
    db_session.expire_all()
    completed = next(row for row in client.get('/api/v1/admin/returns').json() if row['id'] == return_id)
    assert completed['replacement_rto_inspected_at'] is not None
    db_session.refresh(bal_l)
    assert bal_l.on_hand == initial_l_on_hand
    assert order.order_status == 'delivered'


def test_approve_exchange_with_no_stock_raises_422(
    client: TestClient,
    db_session: Session,
    setup_catalog: dict,
):
    var_m = setup_catalog["var_m"]
    var_l = setup_catalog["var_l"]
    bal_l = setup_catalog["bal_l"]

    # Set replacement stock on hand to 0
    bal_l.on_hand = 0
    db_session.commit()

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Kamran Akmal",
            customer_phone="03331112244",
            shipping_address_line1="Saddar",
            shipping_city="Rawalpindi",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=1)],
        ),
    )
    _deliver(db_session, order)
    _authorize(client, db_session, order)
    line_id = order.lines[0].id

    req_res = client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line_id),
            "quantity": 1,
            "customer_phone": "03331112244",
            "return_type": "size_exchange",
            "reason": "size_too_small",
            "exchange_variant_id": var_l.id,
        },
    )
    assert req_res.status_code == 201
    return_id = req_res.json()["id"]

    # Failed reservation rolls back both the replacement line and approval.
    app_res = client.post(f"/api/v1/admin/returns/{return_id}/approve")
    assert app_res.status_code == 422

    # Verify return status remains "requested"
    ret = db_session.get(OrderReturn, uuid.UUID(return_id))
    assert ret.status == "requested"


def test_approve_refund_return_does_not_create_replacement_shipment(
    client: TestClient,
    db_session: Session,
    setup_catalog: dict,
):
    var_m = setup_catalog["var_m"]
    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Rashid Latif",
            customer_phone="03214443322",
            shipping_address_line1="Gulberg",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=1)],
        ),
    )
    _deliver(db_session, order)
    _authorize(client, db_session, order)
    line_id = order.lines[0].id

    req_res = client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line_id),
            "quantity": 1,
            "customer_phone": "03214443322",
            "return_type": "refund_bank_transfer",
            "reason": "changed_mind",
        },
    )
    assert req_res.status_code == 201
    return_id = req_res.json()["id"]

    app_res = client.post(f"/api/v1/admin/returns/{return_id}/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "approved"

    # No replacement shipment is created beyond the original delivered parcel.
    shipments = db_session.query(Shipment).filter(Shipment.order_id == order.id).all()
    assert len(shipments) == 1
