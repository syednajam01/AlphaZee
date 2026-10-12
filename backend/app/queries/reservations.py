"""
reservations.py — Query and management engine for stock reservations and inventory reporting.

Provides:
- InsufficientStockError: raised when attempting to hold more stock than available.
- InvalidReservationTransitionError: raised on invalid lifecycle stage transitions.
- get_inventory_summary: returns owner display triple (Physical, Held, Available) and active order refs.
- create_stock_reservation: atomically creates a stock reservation guarding against over-allocation.
- transition_reservation_stage: advances reservation stage and synchronizes physical on_hand upon fulfillment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import (
    ALLOWED_RESERVATION_STAGES,
    OPEN_RESERVATION_STAGES,
    TERMINAL_RESERVATION_STAGES,
    InventoryBalance,
    StockReservation,
    SupplierVariant,
)
from app.queries.inventory import adjust_inventory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InsufficientStockError(Exception):
    """Raised when available stock is insufficient to satisfy a reservation request."""


class InvalidReservationTransitionError(Exception):
    """Raised when attempting an invalid reservation lifecycle stage transition."""


@dataclass(frozen=True)
class InventorySummary:
    """Owner inventory status triple with order breakdown."""

    supplier_variant_id: uuid.UUID
    physical: int
    held: int
    available: int
    open_reservations: list[dict]

    @property
    def display_line(self) -> str:
        return f"Physical {self.physical} | Held {self.held} | Available {self.available}"


def get_inventory_summary(
    db: Session, supplier_variant_id: uuid.UUID
) -> InventorySummary:
    """
    Compute real-time inventory triple:
    - Physical = inventory_balances.on_hand
    - Held = sum(quantity) across open reservations (held, confirmed, dispatched)
    - Available = max(0, Physical - Held)
    """
    balance = db.get(InventoryBalance, supplier_variant_id)
    physical = balance.on_hand if balance is not None else 0

    stmt = (
        select(StockReservation)
        .where(
            StockReservation.supplier_variant_id == supplier_variant_id,
            StockReservation.stage.in_(OPEN_RESERVATION_STAGES),
        )
        .order_by(StockReservation.created_at.asc())
    )
    open_res = db.scalars(stmt).all()

    held = sum(r.quantity for r in open_res)
    available = max(0, physical - held)

    open_breakdown = [
        {
            "reservation_id": r.id,
            "order_line_id": r.order_line_id,
            "quantity": r.quantity,
            "stage": r.stage,
            "created_at": r.created_at,
        }
        for r in open_res
    ]

    return InventorySummary(
        supplier_variant_id=supplier_variant_id,
        physical=physical,
        held=held,
        available=available,
        open_reservations=open_breakdown,
    )


def create_stock_reservation(
    db: Session,
    *,
    supplier_variant_id: uuid.UUID,
    order_line_id: uuid.UUID,
    quantity: int,
    idempotency_key: str | None = None,
) -> StockReservation:
    """
    Atomically hold stock for an order line item.

    Concurrency & Idempotency Invariants:
    1. If idempotency_key is provided and an open reservation with that key exists, returns it.
    2. Acquires exclusive row-level lock (SELECT ... FOR UPDATE) on inventory_balances to serialize
       concurrent reservations for the same supplier variant and prevent overselling.
    3. Re-checks available stock under lock and raises InsufficientStockError if requested > available.
    """
    if quantity <= 0:
        raise ValueError(f"Reservation quantity must be strictly positive, got {quantity}")

    clean_idemp = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None

    # 1. Idempotency check: if open reservation already exists for this key, return it immediately
    if clean_idemp:
        existing = db.scalars(
            select(StockReservation)
            .where(
                StockReservation.idempotency_key == clean_idemp,
                StockReservation.stage.in_(OPEN_RESERVATION_STAGES),
            )
        ).first()
        if existing is not None:
            return existing

    # 2. Acquire exclusive row lock on the inventory balance row
    stmt = (
        select(InventoryBalance)
        .where(InventoryBalance.supplier_variant_id == supplier_variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    balance = db.scalars(stmt).one_or_none()
    physical = balance.on_hand if balance is not None else 0

    # 3. Sum open reservations under lock
    held_stmt = (
        select(StockReservation.quantity)
        .where(
            StockReservation.supplier_variant_id == supplier_variant_id,
            StockReservation.stage.in_(OPEN_RESERVATION_STAGES),
        )
    )
    held = sum(db.scalars(held_stmt).all())
    available = max(0, physical - held)

    if available < quantity:
        raise InsufficientStockError(
            f"Insufficient stock for supplier variant {supplier_variant_id}. "
            f"Requested: {quantity}, Available: {available} "
            f"(Physical: {physical}, Held: {held})"
        )

    reservation = StockReservation(
        supplier_variant_id=supplier_variant_id,
        order_line_id=order_line_id,
        quantity=quantity,
        stage="held",
        idempotency_key=clean_idemp,
    )
    db.add(reservation)
    db.flush()

    return reservation


def transition_reservation_stage(
    db: Session,
    *,
    reservation_id: uuid.UUID,
    new_stage: str,
    actor_user_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> StockReservation:
    """
    Advance a reservation through its lifecycle stages.

    When transitioning to 'fulfilled':
    - Physical on_hand is decremented atomically via adjust_inventory.
    - A StockEvent is appended in the same transaction.
    - Reservation is marked closed.
    """
    if new_stage not in ALLOWED_RESERVATION_STAGES:
        raise ValueError(f"Invalid stage {new_stage!r}")

    reservation = db.get(StockReservation, reservation_id)
    if reservation is None:
        raise ValueError(f"StockReservation not found for id {reservation_id}")

    if reservation.stage in TERMINAL_RESERVATION_STAGES:
        if new_stage != reservation.stage:
            raise InvalidReservationTransitionError(
                f"Cannot transition reservation {reservation_id} from terminal stage "
                f"{reservation.stage!r} to {new_stage!r}."
            )
        return reservation

    now = _utcnow()

    if new_stage == "confirmed":
        reservation.supplier_accepted_at = now
    elif new_stage == "dispatched":
        reservation.instructions_sent_at = now
    elif new_stage == "fulfilled":
        # Decrement physical stock on hand
        balance = db.get(InventoryBalance, reservation.supplier_variant_id)
        if balance is None:
            raise ValueError(
                f"InventoryBalance not found for supplier_variant_id {reservation.supplier_variant_id}"
            )

        new_on_hand = balance.on_hand - reservation.quantity
        if new_on_hand < 0:
            raise InsufficientStockError(
                f"Cannot fulfill reservation {reservation_id}: physical on_hand {balance.on_hand} "
                f"is less than reservation quantity {reservation.quantity}."
            )

        adjust_inventory(
            db,
            supplier_variant_id=reservation.supplier_variant_id,
            actor_user_id=actor_user_id,
            new_on_hand=new_on_hand,
            reason="reservation_fulfilled",
            expected_version=balance.version,
            notes=notes or f"Fulfillment for order line {reservation.order_line_id}",
            releasing_reservation_id=reservation.id,
        )
        reservation.closed_at = now
    elif new_stage in ("cancelled", "returned"):
        reservation.closed_at = now

    reservation.stage = new_stage
    db.flush()

    return reservation
