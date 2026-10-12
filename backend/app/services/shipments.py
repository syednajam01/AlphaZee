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
from app.queries.inventory import adjust_inventory, get_active_supplier_variant
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
) -> Shipment:
    """
    Create a new courier dispatch for an order and advance the order to 'dispatched'.
    """
    order = db.get(Order, order_id)
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    if order.payment_method == "bank_transfer" and order.payment_status != "verified":
        raise OrderNotDispatchableError(
            f"Cannot dispatch Bank Transfer order {order.order_number}: payment status is '{order.payment_status}', must be 'verified'."
        )

    if order.order_status != "confirmed":
        raise OrderNotDispatchableError(
            f"Cannot dispatch order {order.order_number} in status '{order.order_status}'. Order must be confirmed by supplier first."
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
        order=order,
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

    # Advance line reservations to 'dispatched'
    order_line_ids = [line.id for line in order.lines]
    if order_line_ids:
        res_stmt = select(StockReservation).where(
            StockReservation.order_line_id.in_(order_line_ids),
            StockReservation.stage.in_(["held", "confirmed"]),
        )
        reservations = db.scalars(res_stmt).all()
        for res in reservations:
            if res.stage == "held":
                transition_reservation_stage(db=db, reservation_id=res.id, new_stage="confirmed")
            transition_reservation_stage(db=db, reservation_id=res.id, new_stage="dispatched")

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

        # Fulfill all open stock reservations sequentially
        order_line_ids = [line.id for line in order.lines]
        if order_line_ids:
            res_stmt = select(StockReservation).where(
                StockReservation.order_line_id.in_(order_line_ids),
                StockReservation.stage.in_(["held", "confirmed", "dispatched", "draft", "supplier_accepted", "allocated"]),
            )
            reservations = db.scalars(res_stmt).all()
            for res in reservations:
                if res.stage == "held":
                    transition_reservation_stage(db=db, reservation_id=res.id, new_stage="confirmed")
                if res.stage in ("held", "confirmed"):
                    transition_reservation_stage(db=db, reservation_id=res.id, new_stage="dispatched")
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
        # Note: In Blocker 5, physical restocking does NOT occur automatically upon rto_delivered.
        # It requires explicit physical condition inspection via inspect_and_restock_order().

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
    Stock remains held in reservation while parcel is in-transit with courier.
    """
    order = db.get(Order, order_id)
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
        now = _utcnow()
        shipment = Shipment(
            order=order,
            courier_code="manual",
            tracking_number=f"RTO-{order.order_number}",
            status="rto_initiated",
            rto_reason=rto_reason.strip() if rto_reason else None,
            rto_courier_cost_minor=max(0, int(rto_courier_cost_minor)),
            dispatched_at=now,
        )
        db.add(shipment)
        order.order_status = "rto"
        order.updated_at = now
        db.flush()
        return shipment

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
) -> Shipment:
    """
    Mark physical arrival of returned parcel at shop ('rto_delivered').
    Cancels reservations, releasing held inventory back to available stock.
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
    )


def inspect_and_restock_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    condition_ok: bool,
    notes: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Shipment:
    """
    Perform physical condition inspection on returned RTO parcel:
    - If condition_ok is True: restores inventory against the fulfilling supplier variant(s)
      and records StockEvent with positive delta and reason='rto_return'. Marks shipment.rto_restocked_at.
    - If condition_ok is False: leaves inventory untouched and records rejection note.
    """
    order = db.get(Order, order_id)
    if not order:
        raise ShipmentError(f"Order {order_id} not found.")

    shipment = db.scalars(
        select(Shipment).where(Shipment.order_id == order_id).order_by(Shipment.created_at.desc())
    ).first()
    if not shipment or shipment.status != "rto_delivered":
        raise ShipmentError(
            f"Cannot inspect RTO: order {order.order_number} has no shipment in 'rto_delivered' status."
        )

    if shipment.rto_restocked_at is not None:
        raise ShipmentError(
            f"Order {order.order_number} has already been inspected and restocked."
        )

    now = _utcnow()

    if condition_ok:
        shipment.rto_restocked_at = now
        if notes:
            shipment.rto_reason = f"{shipment.rto_reason or ''} | Inspection Passed: {notes.strip()}".strip(" |")

        # Restock each line against its fulfilling supplier variant
        for line in order.lines:
            # Find the fulfilling reservation for this order line
            res = db.scalars(
                select(StockReservation).where(StockReservation.order_line_id == line.id)
            ).first()

            if res is not None:
                supplier_variant_id = res.supplier_variant_id
                if res.stage == "fulfilled":
                    # Decremented from physical on_hand upon delivery, so increment on_hand via adjust_inventory
                    balance = db.get(InventoryBalance, supplier_variant_id)
                    if balance:
                        adjust_inventory(
                            db,
                            supplier_variant_id=supplier_variant_id,
                            actor_user_id=actor_user_id,
                            new_on_hand=balance.on_hand + res.quantity,
                            reason="rto_return",
                            expected_version=balance.version,
                            notes=notes or f"RTO restock for order {order.order_number}",
                        )
                elif res.stage in ("dispatched", "held", "confirmed"):
                    # Still open / held, cancel it so held quantity drops and available increases
                    transition_reservation_stage(
                        db=db,
                        reservation_id=res.id,
                        new_stage="cancelled",
                        actor_user_id=actor_user_id,
                        notes="RTO inspection passed; held reservation released.",
                    )
            else:
                # Fallback to active supplier variant if no historical reservation exists
                active_sv = get_active_supplier_variant(db, line.variant_id)
                if active_sv:
                    balance = db.get(InventoryBalance, active_sv.id)
                    if balance:
                        adjust_inventory(
                            db,
                            supplier_variant_id=active_sv.id,
                            actor_user_id=actor_user_id,
                            new_on_hand=balance.on_hand + line.quantity,
                            reason="rto_return",
                            expected_version=balance.version,
                            notes=notes or f"RTO restock for order {order.order_number}",
                        )
    else:
        # Condition failed / damaged
        rejection_note = f"Inspection Rejected: {notes.strip() if notes else 'Damaged goods'}"
        shipment.rto_reason = f"{shipment.rto_reason or ''} | {rejection_note}".strip(" |")

    shipment.updated_at = now
    db.flush()
    return shipment


