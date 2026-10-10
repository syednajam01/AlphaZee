"""
inventory.py — Query and adjustment layer for supplier inventory balances and audit logs.

Provides:
- StaleInventoryError: domain exception raised on optimistic concurrency conflicts.
- adjust_inventory: atomic inventory adjustment guarded by expected_version.
- Read queries for balances and stock event history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.inventory import (
    ALLOWED_STOCK_EVENT_REASONS,
    InventoryBalance,
    StockEvent,
    SupplierVariant,
)
from app.models.suppliers import Supplier


class StaleInventoryError(Exception):
    """
    Raised when an inventory adjustment fails due to an optimistic concurrency conflict
    (the version in the database did not match expected_version).
    """


def get_inventory_balance(
    db: Session, supplier_variant_id: uuid.UUID
) -> InventoryBalance | None:
    """Fetch the current physical inventory balance for a supplier variant."""
    return db.get(InventoryBalance, supplier_variant_id)


def get_stock_events(
    db: Session,
    supplier_variant_id: uuid.UUID,
    *,
    limit: int = 50,
) -> Sequence[StockEvent]:
    """Fetch reverse-chronological audit events for a supplier variant."""
    stmt = (
        select(StockEvent)
        .where(StockEvent.supplier_variant_id == supplier_variant_id)
        .order_by(StockEvent.occurred_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


def get_active_supplier_variant(
    db: Session, variant_id: int
) -> SupplierVariant | None:
    """Fetch the single active supplier linkage for a catalog variant."""
    stmt = select(SupplierVariant).where(
        SupplierVariant.variant_id == variant_id,
        SupplierVariant.active.is_(True),
    )
    return db.scalars(stmt).first()


def get_active_suppliers(db: Session) -> Sequence[Supplier]:
    """Fetch all suppliers with status = 'active'."""
    stmt = (
        select(Supplier)
        .where(Supplier.status == "active")
        .order_by(Supplier.name.asc())
    )
    return db.scalars(stmt).all()


def adjust_inventory(
    db: Session,
    *,
    supplier_variant_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    new_on_hand: int,
    reason: str,
    expected_version: int,
    notes: str | None = None,
    last_counted_at: datetime | None = None,
) -> StockEvent:
    """
    Atomically update inventory_balances and record an audit stock_event.

    Uses a targeted UPDATE ... WHERE version = :expected_version.
    If 0 rows are updated, raises StaleInventoryError (optimistic concurrency conflict).
    Both the balance update and event insertion execute within the caller's transaction.
    """
    if new_on_hand < 0:
        raise ValueError(f"new_on_hand must be non-negative, got {new_on_hand}")

    if reason not in ALLOWED_STOCK_EVENT_REASONS:
        raise ValueError(
            f"Invalid reason {reason!r}. Must be one of {sorted(ALLOWED_STOCK_EVENT_REASONS)}."
        )

    # 1. Read current on_hand for delta computation
    current_balance = db.get(InventoryBalance, supplier_variant_id)
    if current_balance is None:
        raise ValueError(f"InventoryBalance not found for supplier_variant_id {supplier_variant_id}")

    previous_on_hand = current_balance.on_hand

    # 2. Targeted atomic UPDATE guarded by expected_version
    values_to_update: dict = {
        "on_hand": new_on_hand,
        "version": InventoryBalance.version + 1,
    }
    if last_counted_at is not None:
        values_to_update["last_counted_at"] = last_counted_at

    stmt = (
        update(InventoryBalance)
        .where(
            InventoryBalance.supplier_variant_id == supplier_variant_id,
            InventoryBalance.version == expected_version,
        )
        .values(**values_to_update)
    )

    result = db.execute(stmt)

    if result.rowcount == 0:
        raise StaleInventoryError(
            f"Inventory version conflict for {supplier_variant_id}. Expected version {expected_version}."
        )

    # 3. Insert immutable audit event in the same transaction
    delta = new_on_hand - previous_on_hand
    event = StockEvent(
        supplier_variant_id=supplier_variant_id,
        actor_user_id=actor_user_id,
        previous_on_hand=previous_on_hand,
        new_on_hand=new_on_hand,
        delta=delta,
        reason=reason,
        notes=notes,
    )
    db.add(event)
    db.flush()

    return event
