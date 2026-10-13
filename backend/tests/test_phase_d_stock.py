"""Phase D/E physical-stock transitions against PostgreSQL."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import StockEvent, StockReservation, InventoryBalance
from app.models.shipments import Shipment, ShipmentAllocation
from app.queries.reservations import get_inventory_summary
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order, confirm_supplier_acceptance
from app.services.shipments import (
    ShipmentError, create_shipment, update_shipment_status, initiate_rto_order,
    receive_rto_parcel, inspect_and_restock_order, preview_legacy_stock,
    reconcile_legacy_stock,
)
from app.services.returns import (
    create_return_request, approve_return_request, receive_return_items,
    inspect_return_items, complete_return_and_restock,
)
from tests.test_payment_separation import _setup_catalog


def _order(db, quantity=2, on_hand=5):
    variant, supplier_variant, _, user = _setup_catalog(db, on_hand=on_hand)
    order = place_order(db, CreateOrderDTO(
        customer_name='SAMPLE Stock Buyer', customer_phone='03001234567',
        shipping_address_line1='Sample Street', shipping_city='Lahore',
        shipping_province='Punjab', payment_method='cod',
        items=[OrderItemDTO(variant_id=variant.id, quantity=quantity)],
    ))
    confirm_supplier_acceptance(db, order_id=order.id)
    return order, supplier_variant, user


def test_dispatch_deducts_once_and_delivery_deducts_zero(db_session):
    order, sv, user = _order(db_session)
    assert get_inventory_summary(db_session, sv.id).physical == 5
    assert get_inventory_summary(db_session, sv.id).held == 2
    shipment = create_shipment(db_session, order_id=order.id, courier_code='manual',
                               tracking_number='SAMPLE-DISPATCH-1', actor_user_id=user.id)
    summary = get_inventory_summary(db_session, sv.id)
    assert (summary.physical, summary.held, summary.available) == (3, 0, 3)
    allocation = db_session.scalar(select(ShipmentAllocation).where(
        ShipmentAllocation.shipment_id == shipment.id))
    assert allocation.quantity == 2
    assert allocation.reservation.supplier_variant_id == sv.id
    with pytest.raises(ShipmentError):
        create_shipment(db_session, order_id=order.id, courier_code='manual',
                        tracking_number='SAMPLE-DISPATCH-2')
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    assert get_inventory_summary(db_session, sv.id).physical == 3
    assert allocation.reservation.stage == 'fulfilled'
    events = db_session.scalars(select(StockEvent).where(StockEvent.supplier_variant_id == sv.id)).all()
    assert [(event.reason, event.delta, event.source_ref) for event in events] == [
        ('dispatch', -2, f'dispatch:{allocation.reservation_id}')]


def test_dispatch_rejects_missing_supplier_allocation_without_stock_change(db_session):
    order, sv, _ = _order(db_session)
    reservation = db_session.scalar(select(StockReservation).where(
        StockReservation.order_line_id == order.lines[0].id))
    reservation.stage = 'held'
    db_session.flush()
    with pytest.raises(ShipmentError, match='complete supplier-confirmed'):
        create_shipment(db_session, order_id=order.id, courier_code='manual',
                        tracking_number='SAMPLE-INCOMPLETE')
    assert get_inventory_summary(db_session, sv.id).physical == 5
    assert db_session.scalar(select(Shipment.id).where(Shipment.order_id == order.id)) is None


def test_partial_rto_inspection_only_restocks_accepted_units(db_session):
    order, sv, user = _order(db_session, quantity=3)
    shipment = create_shipment(db_session, order_id=order.id, courier_code='manual',
                               tracking_number='SAMPLE-RTO')
    assert get_inventory_summary(db_session, sv.id).physical == 2
    initiate_rto_order(db_session, order_id=order.id, rto_reason='Customer refused')
    receive_rto_parcel(db_session, order_id=order.id,
                       received_quantities={order.lines[0].id: 2})
    assert get_inventory_summary(db_session, sv.id).physical == 2
    inspect_and_restock_order(db_session, order_id=order.id,
        lines={order.lines[0].id: (1, 0)}, actor_user_id=user.id)
    assert get_inventory_summary(db_session, sv.id).physical == 3
    inspect_and_restock_order(db_session, order_id=order.id,
        lines={order.lines[0].id: (1, 0)}, actor_user_id=user.id)
    with pytest.raises(ShipmentError):
        inspect_and_restock_order(db_session, order_id=order.id,
            lines={order.lines[0].id: (3, 0)})
    inspect_and_restock_order(db_session, order_id=order.id,
        lines={order.lines[0].id: (1, 1)}, notes='One torn item')
    assert get_inventory_summary(db_session, sv.id).physical == 3
    assert shipment.rto_restocked_at is not None
    assert db_session.scalar(select(StockEvent).where(
        StockEvent.source_ref.like('rto:%'))).delta == 1


def test_customer_return_quarantines_and_uses_historical_allocation(db_session):
    order, sv, user = _order(db_session, quantity=3)
    shipment = create_shipment(db_session, order_id=order.id, courier_code='manual',
                               tracking_number='SAMPLE-RETURN')
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    assert get_inventory_summary(db_session, sv.id).physical == 2
    ret = create_return_request(db_session, order_id=order.id, order_line_id=order.lines[0].id,
        return_type='refund_bank_transfer', reason='damaged_defective', quantity=2,
        customer_phone=order.customer_phone)
    assert ret.refund_amount_minor == order.lines[0].line_total_minor * 2 // 3
    approve_return_request(db_session, return_id=ret.id)
    receive_return_items(db_session, return_id=ret.id, received_quantity=2)
    assert get_inventory_summary(db_session, sv.id).physical == 2
    inspect_return_items(db_session, return_id=ret.id, sellable_quantity=1,
                         damaged_quantity=1, notes='One damaged', actor_user_id=user.id)
    inspect_return_items(db_session, return_id=ret.id, sellable_quantity=1,
                         damaged_quantity=1, notes='Duplicate callback')
    complete_return_and_restock(db_session, return_id=ret.id, refund_reference='SAMPLE-REF-1')
    assert get_inventory_summary(db_session, sv.id).physical == 3
    assert db_session.scalar(select(StockEvent).where(
        StockEvent.source_ref.like('customer_return:%'))).delta == 1


def test_legacy_shipment_requires_owner_deduction_decision(db_session):
    order, sv, user = _order(db_session)
    reservation = db_session.scalar(select(StockReservation).where(
        StockReservation.order_line_id == order.lines[0].id))
    reservation.stage = 'dispatched'
    reservation.legacy_stock_hold = True
    shipment = Shipment(order_id=order.id, courier_code='manual', tracking_number='SAMPLE-OLD',
                        status='dispatched', stock_reconciliation_status='legacy_review')
    db_session.add(shipment)
    order.order_status = 'dispatched'
    db_session.flush()
    assert get_inventory_summary(db_session, sv.id).available == 3
    assert preview_legacy_stock(db_session, shipment.id)['lines'][0]['reservation_id'] == str(reservation.id)
    with pytest.raises(ShipmentError, match='reconciliation'):
        update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    reconcile_legacy_stock(db_session, shipment_id=shipment.id,
        decisions={reservation.id: (False, None)}, note='Historical ledger checked',
        actor_user_id=user.id)
    assert get_inventory_summary(db_session, sv.id).physical == 3
    assert get_inventory_summary(db_session, sv.id).held == 0
    assert get_inventory_summary(db_session, sv.id).available == 3
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    assert get_inventory_summary(db_session, sv.id).physical == 3


def test_return_and_rto_cannot_restock_the_same_parcel(db_session):
    order, sv, _ = _order(db_session)
    shipment = create_shipment(db_session, order_id=order.id, courier_code='manual',
                               tracking_number='SAMPLE-ROUTE-EXCLUSIVE')
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    ret = create_return_request(db_session, order_id=order.id,
        order_line_id=order.lines[0].id, return_type='refund_bank_transfer',
        reason='damaged_defective', quantity=1, customer_phone=order.customer_phone)
    approve_return_request(db_session, return_id=ret.id)
    receive_return_items(db_session, return_id=ret.id, received_quantity=1)
    with pytest.raises(ShipmentError, match='Customer return receipt'):
        initiate_rto_order(db_session, order_id=order.id)
    assert get_inventory_summary(db_session, sv.id).physical == 3


def test_partial_customer_return_receipt_can_complete_after_inspection(db_session):
    order, sv, _ = _order(db_session, quantity=3)
    shipment = create_shipment(db_session, order_id=order.id, courier_code='manual',
                               tracking_number='SAMPLE-PARTIAL-RETURN')
    update_shipment_status(db_session, shipment_id=shipment.id, status='delivered')
    ret = create_return_request(db_session, order_id=order.id,
        order_line_id=order.lines[0].id, return_type='refund_bank_transfer',
        reason='damaged_defective', quantity=2, customer_phone=order.customer_phone)
    approve_return_request(db_session, return_id=ret.id)
    receive_return_items(db_session, return_id=ret.id, received_quantity=1)
    inspect_return_items(db_session, return_id=ret.id, sellable_quantity=0,
                         damaged_quantity=1, notes='Single returned unit damaged')
    complete_return_and_restock(db_session, return_id=ret.id)
    assert ret.status == 'completed'
    assert get_inventory_summary(db_session, sv.id).physical == 2
