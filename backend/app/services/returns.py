"""
returns.py — Service layer for customer return requests, size exchanges, bank refunds, and physical restocks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import StockReservation, InventoryBalance, SupplierVariant
from app.models.catalog import Variant, Product
from app.queries.reservations import create_stock_reservation, transition_reservation_stage
from app.models.orders import Order, OrderLine, normalize_pakistan_phone
from app.models.returns import (
    ALLOWED_RETURN_REASONS,
    ALLOWED_RETURN_STATUSES,
    ALLOWED_RETURN_TYPES,
    OrderReturn,
)
from app.models.shipments import Shipment, ShipmentAllocation
from app.queries.inventory import adjust_inventory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomerOwnershipError(Exception):
    """Raised when customer phone does not match order record."""


def create_return_request(
    db: Session,
    *,
    order_id: uuid.UUID,
    order_line_id: uuid.UUID,
    return_type: str,
    reason: str,
    customer_phone: str | None = None,
    phone: str | None = None,
    customer_notes: str | None = None,
    exchange_variant_id: int | None = None,
    quantity: int = 1,
) -> OrderReturn:
    """
    Register a customer return request for a purchased order line item.
    Enforces customer phone ownership verification against the order record.
    """
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update()
                      .execution_options(populate_existing=True))
    if order is None:
        raise ValueError(f"Order {order_id} not found.")
    if order.order_status != 'delivered':
        raise ValueError('A customer return requires a delivered order.')

    raw_phone = customer_phone or phone
    if raw_phone:
        try:
            clean_phone = normalize_pakistan_phone(raw_phone)
        except ValueError as err:
            raise CustomerOwnershipError(f"Invalid customer phone number: {err}") from err

        if order.customer_phone != clean_phone:
            raise CustomerOwnershipError("Customer phone number does not match order record.")

    line = db.get(OrderLine, order_line_id)
    if line is None or line.order_id != order.id or line.fulfillment_kind != 'original':
        raise ValueError(f"Order line {order_line_id} does not belong to order {order_id}.")
    if quantity <= 0 or quantity > line.quantity:
        raise ValueError('Return quantity exceeds the purchased line quantity.')
    previous = db.scalars(select(OrderReturn).where(
        OrderReturn.order_line_id == line.id, OrderReturn.status != 'rejected')).all()
    if sum(r.quantity if r.quantity is not None else line.quantity for r in previous) + quantity > line.quantity:
        raise ValueError('Return quantity exceeds the remaining eligible quantity.')

    clean_type = return_type.strip().lower()
    if clean_type not in ALLOWED_RETURN_TYPES:
        raise ValueError(
            f"Invalid return type {return_type!r}. Must be one of {sorted(ALLOWED_RETURN_TYPES)}."
        )
    if clean_type == 'size_exchange':
        replacement = db.get(Variant, exchange_variant_id) if exchange_variant_id else None
        if replacement is None or replacement.product_id != line.variant.product_id or replacement.id == line.variant_id:
            raise ValueError('Select another variant of the purchased product for exchange.')

    clean_reason = reason.strip().lower()
    if clean_reason not in ALLOWED_RETURN_REASONS:
        raise ValueError(
            f"Invalid return reason {reason!r}. Must be one of {sorted(ALLOWED_RETURN_REASONS)}."
        )

    # Calculate default eligible refund amount (minor paisas)
    default_refund = (line.line_total_minor * quantity // line.quantity
                      if clean_type == 'refund_bank_transfer' else 0)

    return_obj = OrderReturn(
        order_id=order.id,
        order_line_id=line.id,
        return_type=clean_type,
        reason=clean_reason,
        customer_notes=customer_notes.strip() if customer_notes else None,
        status="requested",
        exchange_variant_id=exchange_variant_id,
        refund_amount_minor=default_refund,
        quantity=quantity,
    )
    db.add(return_obj)
    db.flush()
    return return_obj


def approve_return_request(
    db: Session,
    *,
    return_id: uuid.UUID,
    refund_amount_minor: int | None = None,
    replacement_charge_minor: int = 0,
) -> OrderReturn:
    """
    Approve a requested return.
    If return_type is 'exchange' or 'size_exchange', atomically acquires replacement
    stock reservation against active supplier variant and books a replacement shipment.
    """
    return_obj = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id)
                           .with_for_update().execution_options(populate_existing=True))
    if return_obj is None:
        raise ValueError(f"Return request {return_id} not found.")

    if return_obj.status == 'approved' and return_obj.return_type == 'size_exchange':
        return return_obj
    if return_obj.status != "requested":
        raise ValueError(
            f"Cannot approve return in status '{return_obj.status}'. Only 'requested' can be approved."
        )

    if return_obj.return_type == 'size_exchange':
        if refund_amount_minor is not None:
            raise ValueError('An exchange cannot override the original refund amount.')
        if replacement_charge_minor < 0:
            raise ValueError('Replacement charge must be non-negative.')
        variant = db.get(Variant, return_obj.exchange_variant_id)
        original = db.get(OrderLine, return_obj.order_line_id)
        if (variant is None or not variant.is_active or not variant.product.is_active
                or variant.product_id != original.variant.product_id):
            raise ValueError('Replacement variant is unavailable.')
        supplier = db.scalar(select(SupplierVariant).where(
            SupplierVariant.variant_id == variant.id, SupplierVariant.active.is_(True)))
        if supplier is None:
            raise ValueError('Replacement supplier is unavailable.')
        line = OrderLine(order_id=return_obj.order_id, fulfillment_kind='replacement',
            replacement_return_id=return_obj.id, variant_id=variant.id,
            product_title_snapshot=variant.product.title, variant_sku_snapshot=variant.sku,
            variant_size_snapshot=variant.size, variant_color_snapshot=variant.color,
            unit_price_minor=0, unit_cost_minor=supplier.supplier_cost_minor,
            quantity=return_obj.quantity, line_total_minor=0)
        db.add(line)
        db.flush()
        create_stock_reservation(db, supplier_variant_id=supplier.id,
            order_line_id=line.id, quantity=return_obj.quantity)
        return_obj.replacement_charge_minor = replacement_charge_minor
    elif replacement_charge_minor:
        raise ValueError('Replacement charge applies only to exchanges.')

    return_obj.status = "approved"
    if refund_amount_minor is not None:
        if refund_amount_minor < 0:
            raise ValueError("Refund amount must be non-negative.")
        return_obj.refund_amount_minor = refund_amount_minor

    db.flush()
    return return_obj


def receive_return_items(db: Session, *, return_id: uuid.UUID, received_quantity: int) -> OrderReturn:
    """Quarantine physically received customer-return units without increasing sellable stock."""
    ret = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id)
                    .with_for_update().execution_options(populate_existing=True))
    if ret is None or ret.inspection_state == 'legacy_review':
        raise ValueError('Return not found or requires legacy stock reconciliation.')
    if ret.status not in ('approved', 'item_received'):
        raise ValueError('Return must be approved before receipt.')
    if ret.order.order_status != 'delivered' or any(
            shipment.status != 'delivered' for shipment in ret.order.shipments
            if shipment.replacement_return_id is None):
        raise ValueError('Customer return receipt requires a delivered parcel outside the RTO flow.')
    if received_quantity < 0 or received_quantity > ret.quantity:
        raise ValueError('Received quantity exceeds the approved return.')
    if ret.status == 'item_received' and received_quantity == ret.received_quantity:
        return ret
    if ret.status == 'item_received' and received_quantity != ret.received_quantity:
        raise ValueError('Received quantity is already recorded; create a separate receipt record.')
    ret.received_quantity = received_quantity
    ret.status = 'item_received'
    db.flush()
    return ret


def inspect_return_items(db: Session, *, return_id: uuid.UUID, sellable_quantity: int,
                         damaged_quantity: int, notes: str | None = None,
                         actor_user_id: uuid.UUID | None = None) -> OrderReturn:
    """Classify received units and restock only the new accepted quantity."""
    ret = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id)
                    .with_for_update().execution_options(populate_existing=True))
    if ret is None or ret.inspection_state == 'legacy_review':
        raise ValueError('Return not found or requires legacy stock reconciliation.')
    if ret.status not in ('item_received', 'inspected_passed'):
        raise ValueError('Return must be received before inspection.')
    if (sellable_quantity < ret.sellable_quantity or damaged_quantity < ret.damaged_quantity
            or sellable_quantity + damaged_quantity > ret.received_quantity):
        raise ValueError('Inspection quantities exceed receipt or reverse a recorded disposition.')
    if damaged_quantity > ret.damaged_quantity and not (notes and notes.strip()):
        raise ValueError('Record a note for damaged stock.')
    increase = sellable_quantity - ret.sellable_quantity
    damaged_increase = damaged_quantity - ret.damaged_quantity
    if increase:
        allocations = db.scalars(select(ShipmentAllocation).join(StockReservation,
            ShipmentAllocation.reservation_id == StockReservation.id).join(Shipment,
            ShipmentAllocation.shipment_id == Shipment.id).where(
            StockReservation.order_line_id == ret.order_line_id,
            Shipment.status.in_(['delivered', 'rto_initiated', 'rto_delivered']))).all()
        if len(allocations) != 1 or allocations[0].reservation.stage != 'fulfilled':
            raise ValueError('Historical delivered supplier allocation is missing or ambiguous.')
        supplier_variant_id = allocations[0].reservation.supplier_variant_id
        balance = db.scalar(select(InventoryBalance).where(
            InventoryBalance.supplier_variant_id == supplier_variant_id)
            .with_for_update().execution_options(populate_existing=True))
        if balance is None:
            raise ValueError('Historical supplier inventory balance is missing.')
        adjust_inventory(db, supplier_variant_id=supplier_variant_id,
            actor_user_id=actor_user_id, new_on_hand=balance.on_hand + increase,
            reason='customer_return', expected_version=balance.version,
            notes=notes or f'Customer return inspection {ret.id}',
            source_ref=f'customer_return:{ret.id}:{sellable_quantity}')
        ret.restocked_at = ret.restocked_at or _utcnow()
    ret.sellable_quantity = sellable_quantity
    ret.damaged_quantity = damaged_quantity
    if increase or damaged_increase:
        ret.inspection_notes = notes
        ret.inspected_by_user_id = actor_user_id
        ret.inspected_at = _utcnow()
    if sellable_quantity + damaged_quantity == ret.received_quantity:
        ret.status = 'inspected_passed'
    db.flush()
    return ret


def complete_return_and_restock(db: Session, *, return_id: uuid.UUID,
                                refund_reference: str | None = None,
                                should_restock: bool = True,
                                actor_user_id: uuid.UUID | None = None) -> OrderReturn:
    """Complete a fully inspected return; stock was moved during inspection only."""
    ret = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id)
                    .with_for_update().execution_options(populate_existing=True))
    if ret is None or ret.inspection_state == 'legacy_review':
        raise ValueError('Return not found or requires legacy stock reconciliation.')
    if (ret.status != 'inspected_passed' or ret.received_quantity <= 0
            or ret.sellable_quantity + ret.damaged_quantity != ret.received_quantity):
        raise ValueError('Complete receipt and inspect every returned unit first.')
    if not should_restock and ret.sellable_quantity > 0:
        raise ValueError('Sellable units were already restocked at inspection.')
    ret.status = 'completed'
    # Completion approves the liability; only an executed payment supplies a reference.
    db.flush()
    return ret


def reject_return_request(
    db: Session,
    *,
    return_id: uuid.UUID,
) -> OrderReturn:
    """Reject a return request."""
    return_obj = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id)
                           .with_for_update().execution_options(populate_existing=True))
    if return_obj is None:
        raise ValueError(f"Return request {return_id} not found.")

    if return_obj.status not in ('requested', 'approved') or return_obj.received_quantity:
        raise ValueError('Only unreceived pending returns can be rejected.')

    if return_obj.return_type == 'size_exchange' and return_obj.status == 'approved':
        line = db.scalar(select(OrderLine).where(OrderLine.replacement_return_id == return_obj.id))
        if line is not None:
            reservations = db.scalars(select(StockReservation).where(
                StockReservation.order_line_id == line.id).with_for_update()).all()
            if any(res.stage != 'held' for res in reservations):
                raise ValueError('Dispatched replacement cannot be rejected.')
            for res in reservations:
                transition_reservation_stage(db, reservation_id=res.id, new_stage='cancelled')

    return_obj.status = "rejected"
    db.flush()
    return return_obj


def list_order_returns(
    db: Session,
    *,
    order_id: uuid.UUID | None = None,
    status: str | None = None,
) -> Sequence[OrderReturn]:
    """Query return requests."""
    stmt = select(OrderReturn)
    if order_id is not None:
        stmt = stmt.where(OrderReturn.order_id == order_id)
    if status is not None:
        stmt = stmt.where(OrderReturn.status == status)
    stmt = stmt.order_by(OrderReturn.created_at.desc())
    return db.scalars(stmt).all()
