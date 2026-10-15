"""Owner stock detail must reconcile with checkout and preserve supplier history."""
import uuid
import pytest
from sqlalchemy import select
from app.models.catalog import AvailabilityStatus
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant, StockEvent
from app.models.suppliers import Supplier
from app.queries.catalog_stock import public_availability
from app.queries.reservations import InsufficientStockError
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order, cancel_order
from tests.test_orders_integration import _setup_store_catalog


def order(db, variant, quantity=2):
    return place_order(db, CreateOrderDTO(customer_name='SAMPLE M5', customer_phone='03001234567',
        shipping_address_line1='SAMPLE street', shipping_city='Lahore', shipping_province='Punjab',
        payment_method='cod', items=[OrderItemDTO(variant.id, quantity)]))


def test_stock_reads_are_private(client):
    assert client.get('/api/v1/admin/catalog/variants/1/stock').status_code == 401
    assert client.get(f'/api/v1/admin/inventory/{uuid.uuid4()}/holds').status_code == 401


def test_paginated_open_and_orphan_legacy_holds_reconcile(admin_client, db_session, configured_bank):
    v, sv, balance = _setup_store_catalog(db_session, 20)
    first, second = order(db_session, v, 2), order(db_session, v, 3)
    db_session.add_all([
        StockReservation(supplier_variant_id=sv.id, order_line_id=uuid.uuid4(), quantity=4, stage='dispatched', legacy_stock_hold=True),
        StockReservation(supplier_variant_id=sv.id, order_line_id=uuid.uuid4(), quantity=7, stage='cancelled', legacy_stock_hold=False),
    ]); db_session.flush()
    path = f'/api/v1/admin/inventory/{sv.id}/holds'
    rows = []
    for page in range(1, 4):
        response = admin_client.get(path, params={'page': page, 'page_size': 1})
        assert response.status_code == 200, response.text
        data = response.json()
        assert (data['physical_on_hand'], data['held_reservations'], data['available_to_sell'], data['total']) == (20, 9, 11, 3)
        rows += data['holds']
    assert sum(row['quantity'] for row in rows) == 9
    assert len({row['reservation_id'] for row in rows}) == 3
    assert {row['order_id'] for row in rows if row['order_id']} == {str(first.id), str(second.id)}
    assert next(row for row in rows if row['legacy_stock_hold'])['order_link'] is None
    linked = next(row for row in rows if row['order_id'])
    result = admin_client.get('/api/v1/admin/orders', params={'order_id': linked['order_id']}).json()
    assert result['total'] == 1 and result['orders'][0]['id'] == linked['order_id']
    assert admin_client.get(path, params={'page': 0}).status_code == 422
    assert admin_client.get(path, params={'page_size': 101}).status_code == 422
    assert admin_client.get(f'/api/v1/admin/inventory/{uuid.uuid4()}/holds').status_code == 404
    cancel_order(db_session, order_id=first.id); db_session.flush()
    assert admin_client.get(path).json()['held_reservations'] == 7


def test_mapping_switch_preserves_stock_reservations_and_order_cost(admin_client, db_session, configured_bank):
    v, original, balance = _setup_store_catalog(db_session, 10)
    placed = order(db_session, v)
    new_supplier = Supplier(name='SAMPLE second', slug='sample-second', status='active')
    db_session.add(new_supplier); db_session.flush()
    path = f'/api/v1/admin/suppliers/{new_supplier.id}/variants'
    response = admin_client.post(path, json={'variant_id': v.id, 'supplier_cost_minor': 1234})
    assert response.status_code == 200, response.text
    state = admin_client.get(f'/api/v1/admin/catalog/variants/{v.id}/stock').json()
    assert state['mapping']['supplier_cost_minor'] == 1234
    assert state['mapping']['physical_on_hand'] == 0 and state['public_availability'] == 'unavailable'
    historical = state['historical_mappings'][0]
    assert (historical['physical_on_hand'], historical['held_reservations'], historical['available_to_sell']) == (10, 2, 8)
    assert historical['holds'][0]['order_id'] == str(placed.id)
    assert placed.lines[0].unit_cost_minor == 200000
    assert len(list(db_session.scalars(select(SupplierVariant).where(SupplierVariant.variant_id == v.id, SupplierVariant.active.is_(True))))) == 1
    response = admin_client.post(f'/api/v1/admin/suppliers/{original.supplier_id}/variants', json={'variant_id': v.id, 'supplier_cost_minor': 4567})
    assert response.status_code == 200
    state = admin_client.get(f'/api/v1/admin/catalog/variants/{v.id}/stock').json()
    assert state['mapping']['physical_on_hand'] == 10 and state['mapping']['held_reservations'] == 2
    assert state['mapping']['supplier_cost_minor'] == 4567 and placed.lines[0].unit_cost_minor == 200000


def test_adjustment_version_zero_audit_and_held_floor(admin_client, db_session, configured_bank):
    v, sv, balance = _setup_store_catalog(db_session, 5)
    order(db_session, v, 2)
    payload = {'supplier_variant_id': str(sv.id), 'quantity_delta': 3, 'expected_version': 0,
               'reason': 'supplier_receipt', 'reference_id': 'SAMPLE-INVOICE', 'notes': 'SAMPLE received'}
    response = admin_client.post('/api/v1/admin/inventory/adjust', json=payload)
    assert response.status_code == 200, response.text
    assert response.json()['physical_on_hand'] == 8 and response.json()['version'] == 1
    event = db_session.scalar(select(StockEvent).where(StockEvent.supplier_variant_id == sv.id))
    assert event.delta == 3 and event.actor_user_id and event.notes == 'SAMPLE-INVOICE | SAMPLE received'
    assert admin_client.post('/api/v1/admin/inventory/adjust', json=payload).status_code == 409
    assert admin_client.post('/api/v1/admin/inventory/adjust', json=payload | {'expected_version': 1, 'quantity_delta': -7}).status_code == 400
    assert admin_client.post('/api/v1/admin/inventory/adjust', json=payload | {'expected_version': 1, 'quantity_delta': 2147483647}).status_code == 400
    db_session.refresh(balance); assert balance.on_hand == 8
    for invalid in (True, 0.5, 2147483648):
        assert admin_client.post('/api/v1/admin/inventory/adjust', json=payload | {'quantity_delta': invalid}).status_code == 422
    assert len(list(db_session.scalars(select(StockEvent).where(StockEvent.supplier_variant_id == sv.id)))) == 1


@pytest.mark.parametrize('condition', ['zero', 'inactive_supplier', 'missing_cost', 'inactive_mapping', 'owner_unavailable', 'owner_unknown', 'fully_reserved'])
def test_public_eligibility_and_checkout_share_constraints(admin_client, db_session, configured_bank, condition):
    v, sv, balance = _setup_store_catalog(db_session, 2)
    if condition == 'zero': balance.on_hand = 0
    elif condition == 'inactive_supplier': sv.supplier.status = 'inactive'
    elif condition == 'missing_cost': sv.supplier_cost_minor = None
    elif condition == 'inactive_mapping': sv.active = False
    elif condition == 'owner_unavailable': v.availability = AvailabilityStatus.UNAVAILABLE
    elif condition == 'owner_unknown': v.availability = AvailabilityStatus.UNKNOWN
    else: order(db_session, v, 2)
    db_session.flush()
    expected = 'unknown' if condition == 'owner_unknown' else 'unavailable'
    assert public_availability(db_session, [v])[v.id] == expected
    response = admin_client.get(f'/api/v1/products/{v.product.slug}')
    assert response.status_code == 200, response.text
    assert response.json()['variants'][0]['availability'] == expected
    body = response.text
    for private in ('supplier_cost', 'supplier_name', 'held_reservations', 'order_line_id', 'physical_on_hand'):
        assert private not in body
    with pytest.raises((ValueError, InsufficientStockError)): order(db_session, v, 1)


def test_empty_holds_and_mapping_validation(admin_client, db_session):
    v, sv, balance = _setup_store_catalog(db_session, 3)
    data = admin_client.get(f'/api/v1/admin/inventory/{sv.id}/holds').json()
    assert data['holds'] == [] and data['total'] == 0 and data['available_to_sell'] == 3
    assert public_availability(db_session, [v])[v.id] == 'available'
    path = f'/api/v1/admin/suppliers/{sv.supplier_id}/variants'
    for value in (True, 1.5, -1, 2147483648):
        assert admin_client.post(path, json={'variant_id': v.id, 'supplier_cost_minor': value}).status_code == 422
    sv.supplier.status = 'suspended'; db_session.flush()
    assert admin_client.post(path, json={'variant_id': v.id, 'supplier_cost_minor': 100}).status_code == 422
