"""
returns.py — Service layer for customer return requests, size exchanges, bank refunds, and physical restocks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import StockReservation
from app.models.orders import Order, OrderLine, normalize_pakistan_phone
from app.models.returns import (
    ALLOWED_RETURN_REASONS,
    ALLOWED_RETURN_STATUSES,
    ALLOWED_RETURN_TYPES,
    OrderReturn,
)
from app.models.shipments import Shipment
from app.queries.inventory import (
    adjust_inventory,
    get_active_supplier_variant,
    get_inventory_balance,
)
from app.queries.reservations import InsufficientStockError, create_stock_reservation


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
) -> OrderReturn:
    """
    Register a customer return request for a purchased order line item.
    Enforces customer phone ownership verification against the order record.
    """
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found.")

    raw_phone = customer_phone or phone
    if raw_phone:
        try:
            clean_phone = normalize_pakistan_phone(raw_phone)
        except ValueError as err:
            raise CustomerOwnershipError(f"Invalid customer phone number: {err}") from err

        if order.customer_phone != clean_phone:
            raise CustomerOwnershipError("Customer phone number does not match order record.")

    line = db.get(OrderLine, order_line_id)
    if line is None or line.order_id != order.id:
        raise ValueError(f"Order line {order_line_id} does not belong to order {order_id}.")

    clean_type = return_type.strip().lower()
    if clean_type not in ALLOWED_RETURN_TYPES:
        raise ValueError(
            f"Invalid return type {return_type!r}. Must be one of {sorted(ALLOWED_RETURN_TYPES)}."
        )

    clean_reason = reason.strip().lower()
    if clean_reason not in ALLOWED_RETURN_REASONS:
        raise ValueError(
            f"Invalid return reason {reason!r}. Must be one of {sorted(ALLOWED_RETURN_REASONS)}."
        )

    # Calculate default eligible refund amount (minor paisas)
    default_refund = line.line_total_minor if clean_type == "refund_bank_transfer" else 0

    return_obj = OrderReturn(
        order_id=order.id,
        order_line_id=line.id,
        return_type=clean_type,
        reason=clean_reason,
        customer_notes=customer_notes.strip() if customer_notes else None,
        status="requested",
        exchange_variant_id=exchange_variant_id,
        refund_amount_minor=default_refund,
    )
    db.add(return_obj)
    db.flush()
    return return_obj


def approve_return_request(
    db: Session,
    *,
    return_id: uuid.UUID,
    refund_amount_minor: int | None = None,
) -> OrderReturn:
    """
    Approve a requested return.
    If return_type is 'exchange' or 'size_exchange', atomically acquires replacement
    stock reservation against active supplier variant and books a replacement shipment.
    """
    return_obj = db.get(OrderReturn, return_id)
    if return_obj is None:
        raise ValueError(f"Return request {return_id} not found.")

    if return_obj.status != "requested":
        raise ValueError(
            f"Cannot approve return in status '{return_obj.status}'. Only 'requested' can be approved."
        )

    return_obj.status = "approved"
    if refund_amount_minor is not None:
        if refund_amount_minor < 0:
            raise ValueError("Refund amount must be non-negative.")
        return_obj.refund_amount_minor = refund_amount_minor

    # End-to-end exchange completion: reserve replacement stock and create replacement shipment
    if return_obj.return_type in ("exchange", "size_exchange"):
        if not return_obj.exchange_variant_id:
            raise ValueError("Size exchange requires exchange_variant_id to be specified.")

        line = db.get(OrderLine, return_obj.order_line_id)
        qty = line.quantity if line else 1

        sv = get_active_supplier_variant(db, return_obj.exchange_variant_id)
        if not sv:
            raise InsufficientStockError(
                f"No active supplier available for replacement variant {return_obj.exchange_variant_id}."
            )

        # Create stock reservation under exclusive lock
        create_stock_reservation(
            db,
            supplier_variant_id=sv.id,
            quantity=qty,
            order_line_id=line.id if line else None,
            idempotency_key=f"exchange-{return_obj.id}",
        )

        # Create replacement shipment for the order
        replacement_shipment = Shipment(
            order_id=return_obj.order_id,
            courier_code="manual",
            tracking_number=f"EXCH-{return_obj.id.hex[:8].upper()}",
            shipping_cost_minor=0,
            status="booked",
            cod_amount_minor=0,
            cod_remittance_status="not_applicable",
        )
        db.add(replacement_shipment)

    db.flush()
    return return_obj


def complete_return_and_restock(
    db: Session,
    *,
    return_id: uuid.UUID,
    refund_reference: str | None = None,
    should_restock: bool = True,
    actor_user_id: uuid.UUID | None = None,
) -> OrderReturn:
    """
    Complete an approved return, record the bank transfer refund transaction reference,
    and optionally restock the inventory balance back to the supplier.
    """
    return_obj = db.get(OrderReturn, return_id)
    if return_obj is None:
        raise ValueError(f"Return request {return_id} not found.")

    if return_obj.status not in ("approved", "item_received", "inspected_passed"):
        raise ValueError(
            f"Cannot complete return in status '{return_obj.status}'. Must be approved or inspected first."
        )

    return_obj.status = "completed"
    if refund_reference:
        return_obj.refund_reference = refund_reference.strip()

    if should_restock and return_obj.restocked_at is None:
        line = db.get(OrderLine, return_obj.order_line_id)
        if line and line.variant_id:
            # Look up fulfilling supplier from line's historical StockReservation
            res = db.scalars(
                select(StockReservation).where(StockReservation.order_line_id == line.id)
            ).first()
            target_sv_id = res.supplier_variant_id if res else None

            if not target_sv_id:
                sv = get_active_supplier_variant(db, line.variant_id)
                target_sv_id = sv.id if sv else None

            if target_sv_id:
                bal = get_inventory_balance(db, target_sv_id)
                if bal is not None:
                    adjust_inventory(
                        db,
                        supplier_variant_id=target_sv_id,
                        actor_user_id=actor_user_id,
                        new_on_hand=bal.on_hand + line.quantity,
                        reason="rto_return",
                        expected_version=bal.version,
                        notes=f"Customer return restock for return request {return_id}",
                    )
                    return_obj.restocked_at = _utcnow()

    db.flush()
    return return_obj


def reject_return_request(
    db: Session,
    *,
    return_id: uuid.UUID,
) -> OrderReturn:
    """Reject a return request."""
    return_obj = db.get(OrderReturn, return_id)
    if return_obj is None:
        raise ValueError(f"Return request {return_id} not found.")

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
