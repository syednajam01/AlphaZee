"""
shipments.py — Service layer for courier dispatches, delivery lifecycle, COD remittances, and RTO returns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryBalance, StockEvent, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.shipments import ALLOWED_COURIER_CODES, ALLOWED_SHIPMENT_STATUSES, Shipment
from app.queries.reservations import transition_reservation_stage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ShipmentError(Exception):
    """Base exception for shipment operations."""


class OrderNotDispatchableError(ShipmentError):
    """Raised when an order cannot be dispatched (e.g. already cancelled or RTO)."""


class ShipmentNotFoundError(ShipmentError):
    """Raised when a shipment ID is not found."""


def create_shipment(
    db: Session,
    *,
    order_id: uuid.UUID,
    courier_code: str,
    tracking_number: str,
    shipping_cost_minor: int = 0,
    tracking_url: str | None = None,
) -> Shipment:
    """
    Create a new courier dispatch for an order and advance the order to 'dispatched'.
    """
    order = db.get(Order, order_id)
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    if order.order_status in {"cancelled", "rto"}:
        raise OrderNotDispatchableError(
            f"Cannot dispatch order {order.order_number} in status '{order.order_status}'."
        )

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
        order_id=order.id,
        courier_code=clean_courier,
        tracking_number=tracking_number.strip(),
        tracking_url=tracking_url.strip() if tracking_url else None,
        shipping_cost_minor=max(0, int(shipping_cost_minor)),
        status="dispatched",
        cod_amount_minor=cod_amount,
        cod_remittance_status=remittance_status,
        dispatched_at=now,
    )
    db.add(shipment)

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
) -> Shipment:
    """
    Update a shipment's delivery status and synchronize parent order & stock lifecycle.
    """
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise ShipmentNotFoundError(f"Shipment {shipment_id} not found.")

    clean_status = status.strip().lower()
    if clean_status not in ALLOWED_SHIPMENT_STATUSES:
        raise ValueError(
            f"Invalid shipment status {status!r}. Must be one of {sorted(ALLOWED_SHIPMENT_STATUSES)}."
        )

    now = _utcnow()
    shipment.status = clean_status
    shipment.updated_at = now

    order = shipment.order

    if clean_status == "delivered":
        shipment.delivered_at = now
        order.order_status = "delivered"
        order.updated_at = now
        if order.payment_method == "cod":
            order.payment_status = "verified"

        # Fulfill all open stock reservations
        order_line_ids = [line.id for line in order.lines]
        if order_line_ids:
            res_stmt = select(StockReservation).where(
                StockReservation.order_line_id.in_(order_line_ids),
                StockReservation.stage.in_(["held", "draft", "supplier_accepted", "allocated", "dispatched"]),
            )
            reservations = db.scalars(res_stmt).all()
            for res in reservations:
                transition_reservation_stage(
                    db=db,
                    reservation_id=res.id,
                    new_stage="fulfilled",
                )

    elif clean_status in {"rto_initiated", "rto_delivered"}:
        order.order_status = "rto"
        order.updated_at = now
        if rto_reason:
            shipment.rto_reason = rto_reason
        if rto_courier_cost_minor > 0:
            shipment.rto_courier_cost_minor = int(rto_courier_cost_minor)

        if clean_status == "rto_delivered":
            shipment.rto_restocked_at = now
            # Cancel reservations / restore held items
            order_line_ids = [line.id for line in order.lines]
            if order_line_ids:
                res_stmt = select(StockReservation).where(
                    StockReservation.order_line_id.in_(order_line_ids),
                    StockReservation.stage != "cancelled",
                )
                reservations = db.scalars(res_stmt).all()
                for res in reservations:
                    if res.stage == "fulfilled":
                        # Inventory was already decremented, restock it
                        balance = db.get(InventoryBalance, res.supplier_variant_id)
                        if balance:
                            old_on_hand = balance.on_hand
                            balance.on_hand += res.quantity
                            balance.version += 1
                            balance.last_counted_at = now
                            event = StockEvent(
                                supplier_variant_id=res.supplier_variant_id,
                                previous_on_hand=old_on_hand,
                                new_on_hand=balance.on_hand,
                                reason="rto_return",
                                occurred_at=now,
                            )
                            db.add(event)
                    else:
                        transition_reservation_stage(
                            db=db,
                            reservation_id=res.id,
                            new_stage="cancelled",
                        )

    db.flush()
    return shipment


def record_cod_remittance(
    db: Session,
    *,
    shipment_id: uuid.UUID,
    remitted_amount_minor: int,
    reference: str | None = None,
) -> Shipment:
    """
    Record courier cash remittance into AlphaZee's business bank account.
    """
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise ShipmentNotFoundError(f"Shipment {shipment_id} not found.")

    if shipment.cod_amount_minor <= 0:
        raise ShipmentError("Cannot record COD remittance on a non-COD shipment.")

    now = _utcnow()
    shipment.cod_remitted_amount_minor = max(0, int(remitted_amount_minor))
    shipment.cod_remittance_status = "remitted"
    shipment.cod_remittance_reference = reference.strip() if reference else None
    shipment.cod_remitted_at = now
    shipment.updated_at = now

    db.flush()
    return shipment
