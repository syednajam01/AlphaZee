"""
test_api_orders.py — Integration tests for Customer Order Storefront API endpoints.

Tests:
- POST /api/v1/orders: Valid COD and Bank Transfer orders, authoritative price snapshotting, stock reservation holding.
- POST /api/v1/orders: 422 on invalid phone format, 409 on insufficient inventory, 400 on unavailable variant.
- POST /api/v1/orders/{order_number}/receipt: Payment proof submission with order-scoped session.
- GET /api/v1/orders/{order_number}: Customer tracking with private-code access.
"""

from __future__ import annotations

import uuid
import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from sqlalchemy.orm import Session

from app.config import settings
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.suppliers import Supplier
from app.models.suppliers import UserAccount
from app.services.orders import confirm_supplier_acceptance, record_payment_instructions_sent
from app.models.orders import Order, OrderLine
from app.models.inventory import StockReservation
from app.queries.inventory import adjust_inventory
from app.queries.reservations import get_inventory_summary
from sqlalchemy import select


def _post_order(client, payload):
    assert client.get('/api/v1/orders/checkout-session').status_code == 200
    return client.post('/api/v1/orders', json=payload, headers={
        'Origin': 'http://localhost:3000', 'Idempotency-Key': f'chk_{uuid.uuid4().hex}',
    })


def test_checkout_attempt_requires_key_and_browser_session(client):
    payload = {
        'customer_name': 'SAMPLE Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 1', 'shipping_city': 'Lahore',
        'shipping_province': 'Punjab', 'payment_method': 'cod',
        'items': [{'variant_id': 1, 'quantity': 1}],
    }
    origin = {'Origin': 'http://localhost:3000'}
    headers = {**origin, 'Idempotency-Key': f'chk_{uuid.uuid4().hex}'}
    assert client.post('/api/v1/orders', json=payload, headers=headers).status_code == 428
    assert client.get('/api/v1/orders/checkout-session').status_code == 200
    assert client.post('/api/v1/orders', json=payload, headers=origin).status_code == 422
    assert client.post('/api/v1/orders', json=payload, headers={
        **headers, 'Origin': 'https://untrusted.example',
    }).status_code == 403


def test_checkout_replay_checks_payload_and_session(client, db_session):
    item = _create_catalog_item(db_session, on_hand=2)
    payload = {
        'customer_name': 'SAMPLE Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 1', 'shipping_city': 'Lahore',
        'shipping_province': 'Punjab', 'payment_method': 'cod',
        'items': [{'variant_id': item['variant'].id, 'quantity': 1}],
    }
    client.get('/api/v1/orders/checkout-session')
    headers = {'Origin': 'http://localhost:3000', 'Idempotency-Key': f'chk_{uuid.uuid4().hex}'}
    first = client.post('/api/v1/orders', json=payload, headers=headers)
    assert first.status_code == 201
    assert client.post('/api/v1/orders', json={**payload, 'customer_name': 'Changed Buyer'},
                       headers=headers).status_code == 409
    client.cookies.clear()
    client.get('/api/v1/orders/checkout-session')
    foreign = client.post('/api/v1/orders', json=payload, headers=headers)
    assert foreign.status_code == 409
    assert first.json()['order_number'] not in foreign.text
    assert len(db_session.scalars(select(Order).where(Order.customer_name == 'SAMPLE Buyer')).all()) == 1
    assert get_inventory_summary(db_session, item['sv'].id).held == 1


def test_second_line_failure_rolls_back_order_and_holds(client, db_session):
    available = _create_catalog_item(db_session, on_hand=1)
    unavailable = _create_catalog_item(db_session, on_hand=0)
    payload = {
        'customer_name': 'SAMPLE Atomic Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 1', 'shipping_city': 'Lahore',
        'shipping_province': 'Punjab', 'payment_method': 'cod',
        'items': [{'variant_id': available['variant'].id, 'quantity': 1},
                  {'variant_id': unavailable['variant'].id, 'quantity': 1}],
    }
    result = _post_order(client, payload)
    assert result.status_code == 409
    assert not db_session.scalars(select(Order).where(Order.customer_name == 'SAMPLE Atomic Buyer')).all()
    assert get_inventory_summary(db_session, available['sv'].id).held == 0
    assert not db_session.scalars(select(StockReservation).join(OrderLine,
        StockReservation.order_line_id == OrderLine.id).join(Order, OrderLine.order_id == Order.id)
        .where(Order.customer_name == 'SAMPLE Atomic Buyer')).all()


def test_inventory_adjustment_cannot_take_stock_reserved_by_checkout(client, db_session):
    item = _create_catalog_item(db_session, on_hand=1)
    payload = {
        'customer_name': 'SAMPLE Held Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 1', 'shipping_city': 'Lahore',
        'shipping_province': 'Punjab', 'payment_method': 'cod',
        'items': [{'variant_id': item['variant'].id, 'quantity': 1}],
    }
    assert _post_order(client, payload).status_code == 201
    with pytest.raises(ValueError, match='active holds'):
        adjust_inventory(db_session, supplier_variant_id=item['sv'].id, actor_user_id=None,
                         new_on_hand=0, reason='adjustment_correction',
                         expected_version=item['balance'].version)
    assert get_inventory_summary(db_session, item['sv'].id).available == 0


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

    res = _post_order(client, payload)
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


def test_post_order_bank_transfer_waits_for_instructions(client, db_session):
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

    res = _post_order(client, payload)
    assert res.status_code == 201
    data = res.json()

    assert data["customer_phone"] == "03001234567"  # Normalized
    assert data["payment_method"] == "bank_transfer"
    assert data["payment_deadline_at"] is None
    assert data["bank_instructions"] is None


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

    res = _post_order(client, payload)
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

    res = _post_order(client, payload)
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
    order_res = _post_order(client, order_payload)
    assert order_res.status_code == 201
    order_num = order_res.json()["order_number"]
    owner = UserAccount(auth_subject=f'SAMPLE-order-{uuid.uuid4().hex}', display_name='SAMPLE Owner')
    db_session.add(owner)
    db_session.flush()
    confirm_supplier_acceptance(db_session, order_id=uuid.UUID(order_res.json()['id']))
    record_payment_instructions_sent(db_session, order_id=uuid.UUID(order_res.json()['id']),
                                     actor_user_id=owner.id, channel='sms', reference='SAMPLE-message-123')

    # 2. Upload receipt proof
    receipt_payload = {
        "customer_phone": "0345-1234567",
        "receipt_image_url": "https://storage.alphazee.pk/receipts/proof-123.jpg",
        "bank_reference": "TXN998877",
    }
    receipt_res = client.post(f"/api/v1/orders/{order_num}/receipt", json=receipt_payload,
                              headers={'Origin': 'http://localhost:3000'})
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

    # Phone numbers cannot authorize access; the private code can restore a session.
    from fastapi.testclient import TestClient
    from app.main import app
    other_client = TestClient(app)
    bad_track_res = other_client.get(f"/api/v1/orders/{order_num}?phone=03451234567")
    assert bad_track_res.status_code == 404
    restored = other_client.post('/api/v1/orders/access', json={
        'order_number': order_num, 'access_code': order_res.json()['access_code']},
        headers={'Origin': 'http://localhost:3000'})
    assert restored.status_code == 200
    assert other_client.get(f"/api/v1/orders/{order_num}").status_code == 200


def test_order_access_is_scoped_hashed_and_revocable(client, db_session):
    from app.models.order_access import OrderAccessGrant
    from app.services.order_access import revoke_order_access
    item = _create_catalog_item(db_session, on_hand=3)
    payload = {
        'customer_name': 'SAMPLE Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 1', 'shipping_city': 'Lahore',
        'shipping_province': 'Punjab', 'payment_method': 'cod',
        'items': [{'variant_id': item['variant'].id, 'quantity': 1}],
    }
    first = _post_order(client, payload)
    second = _post_order(client, payload)
    assert first.status_code == second.status_code == 201
    first_number = first.json()['order_number']
    second_number = second.json()['order_number']
    first_code = first.json()['access_code']
    assert first_code not in str(db_session.scalars(select(OrderAccessGrant.code_hash)).all())
    assert client.get(f'/api/v1/orders/{first_number}?phone=03001234567').status_code == 404
    assert client.get(f'/api/v1/orders/{second_number}').status_code == 200
    wrong = client.post('/api/v1/orders/access', json={
        'order_number': first_number, 'access_code': second.json()['access_code']},
        headers={'Origin': 'http://localhost:3000'})
    assert wrong.status_code == 404
    restored = client.post('/api/v1/orders/access', json={
        'order_number': first_number, 'access_code': first_code},
        headers={'Origin': 'http://localhost:3000'})
    assert restored.status_code == 200
    assert client.get(f'/api/v1/orders/{first_number}').status_code == 200
    revoke_order_access(db_session, uuid.UUID(first.json()['id']))
    db_session.commit()
    assert client.get(f'/api/v1/orders/{first_number}').status_code == 404
    assert client.post('/api/v1/orders/access', json={
        'order_number': first_number, 'access_code': first_code},
        headers={'Origin': 'http://localhost:3000'}).status_code == 404
    attempts = [client.post('/api/v1/orders/access', json={
        'order_number': first_number, 'access_code': 'A' * 43},
        headers={'Origin': 'http://localhost:3000'}).status_code for _ in range(10)]
    assert 429 in attempts


def test_owner_assisted_access_recovery_requires_note_and_supports_revoke(admin_client, db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    item = _create_catalog_item(db_session, on_hand=2)
    from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order
    order = place_order(db_session, CreateOrderDTO(
        customer_name='SAMPLE Historical Buyer', customer_phone='03001234567',
        shipping_address_line1='SAMPLE Street 2', shipping_city='Lahore',
        shipping_province='Punjab', payment_method='cod',
        items=[OrderItemDTO(variant_id=item['variant'].id, quantity=1)]))
    db_session.commit()
    customer = TestClient(app)
    assert customer.get(f'/api/v1/orders/{order.order_number}').status_code == 404
    assert admin_client.post(f'/api/v1/admin/orders/{order.id}/access-recovery', json={
        'verification_note': 'short'}).status_code == 422
    recovered = admin_client.post(f'/api/v1/admin/orders/{order.id}/access-recovery', json={
        'verification_note': 'Identity verified through original payment evidence'})
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers['Cache-Control'] == 'no-store'
    exchanged = customer.post('/api/v1/orders/access', json={
        'order_number': order.order_number, 'access_code': recovered.json()['access_code']},
        headers={'Origin': 'http://localhost:3000'})
    assert exchanged.status_code == 200, exchanged.text
    assert customer.get(f'/api/v1/orders/{order.order_number}').status_code == 200
    assert admin_client.post(f'/api/v1/admin/orders/{order.id}/access-revoke').status_code == 200
    assert customer.get(f'/api/v1/orders/{order.order_number}').status_code == 404
