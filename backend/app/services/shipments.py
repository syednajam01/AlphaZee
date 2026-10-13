"""
shipments.py — Service layer for courier dispatches, delivery lifecycle, COD remittances, and RTO returns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryBalance, StockReservation
from app.models.orders import Order, OrderLine
from app.models.shipments import ALLOWED_COURIER_CODES, ALLOWED_SHIPMENT_STATUSES, Shipment, ShipmentAllocation
from app.queries.inventory import adjust_inventory
from app.queries.reservations import transition_reservation_stage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShipmentError(Exception):
    """Base exception for shipment operations."""


class OrderNotDispatchableError(ShipmentError):
    """Raised when an order cannot be dispatched (e.g. already cancelled or RTO)."""


class ShipmentNotFoundError(ShipmentError):
    """Raised when a shipment ID is not found."""


class InvalidRemittanceError(ShipmentError):
    """Raised when COD remittance parameters or amounts are invalid."""


def create_shipment(
    db: Session,
    *,
    order_id: uuid.UUID,
    courier_code: str,
    tracking_number: str,
    shipping_cost_minor: int = 0,
    tracking_url: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Shipment:
    """
    Create a new courier dispatch for an order and advance the order to 'dispatched'.
    """
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update()
                      .execution_options(populate_existing=True))
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    if order.payment_method == "bank_transfer" and order.payment_status != "verified":
        raise OrderNotDispatchableError(
            f"Cannot dispatch Bank Transfer order {order.order_number}: payment status is '{order.payment_status}', must be 'verified'."
        )

    if order.payment_method == 'bank_transfer' and order.payment_review_status == 'required':
        raise OrderNotDispatchableError('Resolve the pending payment review before dispatch.')

    if order.order_status != "confirmed":
        raise OrderNotDispatchableError(
            f"Cannot dispatch order {order.order_number} in status '{order.order_status}'. Order must be confirmed by supplier first."
        )

    if not order.supplier_confirmed_at:
        raise OrderNotDispatchableError('Supplier acceptance must be recorded before dispatch.')
    if db.scalar(select(Shipment.id).where(Shipment.order_id == order.id)) is not None:
        raise OrderNotDispatchableError('Order already has a shipment; dispatch it through its existing allocation.')

    line_ids = [line.id for line in order.lines]
    reservations = db.scalars(select(StockReservation).where(
        StockReservation.order_line_id.in_(line_ids),
        StockReservation.stage == 'confirmed').order_by(StockReservation.supplier_variant_id,
                                                        StockReservation.id).with_for_update()).all()
    if not order.lines or any(sum(r.quantity for r in reservations if r.order_line_id == line.id)
                              != line.quantity for line in order.lines):
        raise OrderNotDispatchableError('Dispatch requires complete supplier-confirmed allocations for every line.')

    clean_courier = courier_code.strip().lower()
    if clean_courier not in ALLOWED_COURIER_CODES:
        raise ValueError(
            f"Invalid courier code {courier_code!r}. Must be one of {sorted(ALLOWED_COURIER_CODES)}."
        )

    # Determine COD amount
    if order.payment_method == "cod":
        cod_amount = order.total_minor
        remittance_status = "pending_remittance"
    else:
        cod_amount = 0
        remittance_status = "not_applicable"

    now = _utcnow()
    shipment = Shipment(
        order=order,
        courier_code=clean_courier,
        tracking_number=tracking_number.strip(),
        tracking_url=tracking_url.strip() if tracking_url else None,
        shipping_cost_minor=int(shipping_cost_minor),
        status="dispatched",
        cod_amount_minor=cod_amount,
        cod_remittance_status=remittance_status,
        dispatched_at=now,
    )
    if shipment.shipping_cost_minor < 0:
        raise ValueError('Shipping cost must be non-negative.')
    db.add(shipment)
    db.flush()
    for res in reservations:
        transition_reservation_stage(db, reservation_id=res.id, new_stage='dispatched',
                                     actor_user_id=actor_user_id)
        db.add(ShipmentAllocation(shipment_id=shipment.id, reservation_id=res.id,
                                  quantity=res.quantity))

    # Advance order status
    order.order_status = "dispatched"
    order.updated_at = now

    db.flush()
    return shipment


def update_shipment_status(
    db: Session,
    *,
    shipment_id: uuid.UUID,
    status: str,
    rto_reason: str | None = None,
    rto_courier_cost_minor: int = 0,
    received_quantities: dict[uuid.UUID, int] | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Shipment:
    """
    Update a shipment's delivery status and synchronize parent order & stock lifecycle.
    """
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id).with_for_update()
                         .execution_options(populate_existing=True))
    if not shipment:
        raise ShipmentNotFoundError(f"Shipment {shipment_id} not found.")

    clean_status = status.strip().lower()
    if clean_status not in ALLOWED_SHIPMENT_STATUSES:
        raise ValueError(
            f"Invalid shipment status {status!r}. Must be one of {sorted(ALLOWED_SHIPMENT_STATUSES)}."
        )

    order = shipment.order
    if shipment.stock_reconciliation_status == 'legacy_review':
        raise ShipmentError('Legacy shipment requires explicit stock reconciliation before status changes.')
    if clean_status == shipment.status:
        return shipment
    allowed = {
        'booked': {'cancelled'},
        'dispatched': {'in_transit', 'out_for_delivery', 'delivered', 'rto_initiated'},
        'in_transit': {'out_for_delivery', 'delivered', 'rto_initiated'},
        'out_for_delivery': {'delivered', 'rto_initiated'},
        'delivered': {'rto_initiated'},
        'rto_initiated': {'rto_delivered'},
    }
    if clean_status not in allowed.get(shipment.status, set()):
        raise ShipmentError(f'Cannot move shipment from {shipment.status} to {clean_status}.')
    allocations = db.scalars(select(ShipmentAllocation).where(
        ShipmentAllocation.shipment_id == shipment.id).order_by(ShipmentAllocation.id)
        .with_for_update()).all()
    if not allocations:
        raise ShipmentError('Shipment has no exact stock allocations.')

    now = _utcnow()
    if clean_status == "delivered":
        if order.payment_method == 'bank_transfer' and order.payment_status != 'verified':
            raise ShipmentError('Bank funds must be verified before delivery.')
        if any(a.reservation.stage != 'dispatched' for a in allocations):
            raise ShipmentError('Delivery requires every allocated reservation to be dispatched.')
        for allocation in allocations:
            transition_reservation_stage(db, reservation_id=allocation.reservation_id,
                                         new_stage='fulfilled', actor_user_id=actor_user_id)
        shipment.delivered_at = now
        order.order_status = "delivered"
        order.updated_at = now
        if order.payment_method == "cod":
            order.payment_status = "verified"

    elif clean_status == 'rto_initiated':
        order.order_status = "rto"
        order.updated_at = now
        if rto_reason:
            shipment.rto_reason = rto_reason.strip()
        if rto_courier_cost_minor > 0:
            shipment.rto_courier_cost_minor = int(rto_courier_cost_minor)
    elif clean_status == 'rto_delivered':
        by_line = received_quantities or {}
        allocated_lines = {a.reservation.order_line_id for a in allocations}
        if set(by_line) != allocated_lines:
            raise ShipmentError('Record received quantities for every allocated order line.')
        for allocation in allocations:
            received = by_line[allocation.reservation.order_line_id]
            if received < 0 or received > allocation.quantity:
                raise ShipmentError('Received quantity is outside the dispatched allocation.')
            allocation.received_quantity = received
        order.order_status = 'rto'
        order.updated_at = now
        if rto_reason:
            shipment.rto_reason = rto_reason.strip()
        if rto_courier_cost_minor > 0:
            shipment.rto_courier_cost_minor = int(rto_courier_cost_minor)

    shipment.status = clean_status
    shipment.updated_at = now

    db.flush()
    return shipment


def preview_legacy_stock(db: Session, shipment_id: uuid.UUID) -> dict:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None or shipment.stock_reconciliation_status != 'legacy_review':
        raise ShipmentError('Legacy shipment requiring reconciliation was not found.')
    order = shipment.order
    reservations = db.scalars(select(StockReservation).where(
        StockReservation.order_line_id.in_([line.id for line in order.lines]),
        StockReservation.stage.in_(['dispatched', 'fulfilled'])).order_by(StockReservation.id)).all()
    return {'shipment_id': str(shipment.id), 'order_id': str(order.id), 'status': shipment.status,
            'shipment_count': len(order.shipments), 'lines': [
                {'reservation_id': str(r.id), 'order_line_id': str(r.order_line_id),
                 'supplier_variant_id': str(r.supplier_variant_id), 'quantity': r.quantity,
                 'stage': r.stage, 'legacy_stock_hold': r.legacy_stock_hold}
                for r in reservations]}


def reconcile_legacy_stock(db: Session, *, shipment_id: uuid.UUID,
                           decisions: dict[uuid.UUID, tuple[bool, int | None]],
                           note: str, actor_user_id: uuid.UUID | None) -> Shipment:
    """Resolve historical deduction ambiguity only from an explicit per-reservation owner decision."""
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id).with_for_update()
                          .execution_options(populate_existing=True))
    if shipment is None or shipment.stock_reconciliation_status != 'legacy_review':
        raise ShipmentError('Legacy shipment requiring reconciliation was not found.')
    order = db.scalar(select(Order).where(Order.id == shipment.order_id).with_for_update())
    if not note or len(note.strip()) < 5 or len(order.shipments) != 1:
        raise ShipmentError('A note and an unambiguous single-shipment order are required.')
    reservations = db.scalars(select(StockReservation).where(
        StockReservation.order_line_id.in_([line.id for line in order.lines]),
        StockReservation.stage.in_(['dispatched', 'fulfilled']))
        .order_by(StockReservation.supplier_variant_id, StockReservation.id).with_for_update()
        .execution_options(populate_existing=True)).all()
    if (not reservations or set(decisions) != {r.id for r in reservations}
            or any(sum(r.quantity for r in reservations if r.order_line_id == line.id)
                   != line.quantity for line in order.lines)):
        raise ShipmentError('Provide a physical deduction decision for every exact historical allocation.')
    for reservation in reservations:
        deducted, received = decisions[reservation.id]
        if shipment.status == 'rto_delivered':
            if received is None or received < 0 or received > reservation.quantity:
                raise ShipmentError('Record actual historical RTO receipt quantity for every allocation.')
        elif received is not None:
            raise ShipmentError('Received quantities apply only to returned parcels.')
        if not deducted:
            balance = db.scalar(select(InventoryBalance).where(
                InventoryBalance.supplier_variant_id == reservation.supplier_variant_id)
                .with_for_update().execution_options(populate_existing=True))
            if balance is None or balance.on_hand < reservation.quantity:
                raise ShipmentError('Physical stock cannot cover the historical dispatch deduction.')
            adjust_inventory(db, supplier_variant_id=reservation.supplier_variant_id,
                actor_user_id=actor_user_id, new_on_hand=balance.on_hand - reservation.quantity,
                expected_version=balance.version, reason='dispatch',
                releasing_reservation_id=reservation.id,
                source_ref=f'legacy_dispatch:{reservation.id}', notes=note.strip())
        reservation.legacy_stock_hold = False
        db.add(ShipmentAllocation(shipment_id=shipment.id, reservation_id=reservation.id,
                                  quantity=reservation.quantity, received_quantity=received or 0))
    shipment.stock_reconciliation_status = 'resolved'
    db.flush()
    return shipment


def record_cod_remittance(
    db: Session,
    *,
    shipment_id: uuid.UUID,
    remitted_amount_minor: int,
    reference: str | None = None,
    is_partial: bool = False,
    partial_reason: str | None = None,
) -> Shipment:
    """
    Record courier cash remittance into AlphaZee's business bank account.
    Guards:
    - Rejects non-COD shipments.
    - Rejects remitted_amount_minor <= 0.
    - Rejects remitted_amount_minor < cod_amount_minor unless explicit is_partial=True and partial_reason provided.
    """
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise ShipmentNotFoundError(f"Shipment {shipment_id} not found.")

    if shipment.cod_amount_minor <= 0:
        raise ShipmentError("Cannot record COD remittance on a non-COD shipment.")

    if remitted_amount_minor <= 0:
        raise InvalidRemittanceError("Remitted amount must be greater than zero.")

    expected_cod = shipment.cod_amount_minor
    if remitted_amount_minor < expected_cod:
        if not is_partial:
            raise InvalidRemittanceError(
                f"Remitted amount ({remitted_amount_minor} paisas) is less than expected COD amount ({expected_cod} paisas). "
                "Partial remittance requires explicit is_partial=True."
            )
        if not partial_reason or not partial_reason.strip():
            raise InvalidRemittanceError(
                "Partial remittance requires an explicit partial_reason explaining the courier short settlement."
            )

    now = _utcnow()
    shipment.cod_remitted_amount_minor = int(remitted_amount_minor)
    shipment.cod_remittance_status = "remitted"
    shipment.cod_remittance_reference = reference.strip() if reference else None
    shipment.cod_remitted_at = now
    shipment.updated_at = now

    db.flush()
    return shipment


def mark_cod_remitted(
    db: Session,
    *,
    order_id: uuid.UUID,
    amount_minor: int,
    reference: str | None = None,
    is_partial: bool = False,
    partial_reason: str | None = None,
) -> Shipment:
    """
    Record courier COD cash remittance for an order by looking up its active shipment.
    """
    stmt = (
        select(Shipment)
        .where(Shipment.order_id == order_id)
        .order_by(Shipment.created_at.desc())
    )
    shipment = db.scalar(stmt)
    if not shipment:
        raise ShipmentNotFoundError(f"Shipment for order {order_id} not found.")

    return record_cod_remittance(
        db,
        shipment_id=shipment.id,
        remitted_amount_minor=amount_minor,
        reference=reference,
        is_partial=is_partial,
        partial_reason=partial_reason,
    )


def initiate_rto_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    rto_reason: str | None = None,
    rto_courier_cost_minor: int = 0,
) -> Shipment:
    """
    Transition a dispatched order and its shipment to 'rto_initiated'.
    Physical stock remains out of sellable inventory while with the courier.
    """
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update()
                      .execution_options(populate_existing=True))
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    if order.order_status not in ("dispatched", "delivered"):
        raise OrderNotDispatchableError(
            f"Cannot initiate RTO for order {order.order_number} in '{order.order_status}' status. "
            f"Only dispatched or delivered orders can enter RTO."
        )

    # Find the active shipment
    shipment = db.scalars(
        select(Shipment).where(Shipment.order_id == order_id).order_by(Shipment.created_at.desc())
    ).first()

    if not shipment:
        raise ShipmentError('RTO requires an existing dispatched shipment.')
    if any(ret.received_quantity or ret.sellable_quantity or ret.damaged_quantity
           for ret in order.returns):
        raise ShipmentError('Customer return receipt already started; parcel cannot also enter RTO.')

    return update_shipment_status(
        db,
        shipment_id=shipment.id,
        status="rto_initiated",
        rto_reason=rto_reason,
        rto_courier_cost_minor=rto_courier_cost_minor,
    )


def receive_rto_parcel(
    db: Session,
    *,
    order_id: uuid.UUID,
    received_quantities: dict[uuid.UUID, int],
) -> Shipment:
    """
    Record actual returned quantities in quarantine without increasing sellable stock.
    """
    order = db.get(Order, order_id)
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    shipment = db.scalars(
        select(Shipment).where(Shipment.order_id == order_id).order_by(Shipment.created_at.desc())
    ).first()

    if not shipment or shipment.status != "rto_initiated":
        raise ShipmentError(
            f"Cannot receive RTO: order {order.order_number} does not have an active in-transit RTO shipment."
        )

    return update_shipment_status(
        db,
        shipment_id=shipment.id,
        status="rto_delivered",
        received_quantities=received_quantities,
    )


def inspect_and_restock_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    lines: dict[uuid.UUID, tuple[int, int]],
    notes: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Shipment:
    """Record cumulative sellable/damaged quantities; only new sellable units move stock."""
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update()
                      .execution_options(populate_existing=True))
    if order is None:
        raise ShipmentError(f'Order {order_id} not found.')
    shipment = db.scalar(select(Shipment).where(Shipment.order_id == order_id,
        Shipment.status == 'rto_delivered').order_by(Shipment.created_at.desc())
        .with_for_update().execution_options(populate_existing=True))
    if shipment is None or shipment.stock_reconciliation_status == 'legacy_review':
        raise ShipmentError('A received and reconciled RTO shipment is required for inspection.')
    allocations = db.scalars(select(ShipmentAllocation).where(
        ShipmentAllocation.shipment_id == shipment.id).order_by(ShipmentAllocation.id)
        .with_for_update().execution_options(populate_existing=True)).all()
    if not allocations or set(lines) != {a.reservation.order_line_id for a in allocations}:
        raise ShipmentError('Inspect every allocated order line explicitly.')
    for allocation in allocations:
        sellable, damaged = lines[allocation.reservation.order_line_id]
        if (sellable < allocation.sellable_quantity or damaged < allocation.damaged_quantity
                or sellable + damaged > allocation.received_quantity):
            raise ShipmentError('Inspection quantities exceed receipt or reverse a recorded disposition.')
        if damaged > allocation.damaged_quantity and not (notes and notes.strip()):
            raise ShipmentError('Record a note for damaged stock.')
        increase = sellable - allocation.sellable_quantity
        damaged_increase = damaged - allocation.damaged_quantity
        if increase:
            balance = db.scalar(select(InventoryBalance).where(
                InventoryBalance.supplier_variant_id == allocation.reservation.supplier_variant_id)
                .with_for_update().execution_options(populate_existing=True))
            if balance is None:
                raise ShipmentError('Historical supplier inventory balance is missing.')
            adjust_inventory(db,
                supplier_variant_id=allocation.reservation.supplier_variant_id,
                actor_user_id=actor_user_id,
                new_on_hand=balance.on_hand + increase,
                reason='rto_return', expected_version=balance.version,
                notes=notes or f'RTO inspection for allocation {allocation.id}',
                source_ref=f'rto:{allocation.id}:{sellable}')
        allocation.sellable_quantity = sellable
        allocation.damaged_quantity = damaged
        if increase or damaged_increase:
            allocation.inspection_notes = notes
            allocation.inspected_by_user_id = actor_user_id
            allocation.inspected_at = _utcnow()
    if all(a.sellable_quantity + a.damaged_quantity == a.received_quantity for a in allocations):
        shipment.rto_restocked_at = shipment.rto_restocked_at or _utcnow()
    db.flush()
    return shipment
