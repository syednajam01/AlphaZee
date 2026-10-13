"""
test_reservation_integration.py — Database integration tests for StockReservation lifecycle and owner reporting.

Covers:
1. Owner inventory summary calculation (Physical, Held, Available).
2. Capacity guarding: preventing over-allocation when requested > available.
3. Reservation cancellation: immediately releasing held stock and restoring available.
4. Reservation fulfillment: atomically decrementing on_hand, recording StockEvent, and closing reservation.
5. Terminal state protection: preventing invalid transitions from closed stages.
6. Database check constraints on quantity and stage.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, StockReservation, SupplierVariant
from app.models.suppliers import Supplier, UserAccount
from app.queries.inventory import get_stock_events
from app.queries.reservations import (
    InsufficientStockError,
    InvalidReservationTransitionError,
    create_stock_reservation,
    get_inventory_summary,
    transition_reservation_stage,
)


def _setup_variant_with_stock(db, on_hand: int = 10):
    """Helper to set up catalog product, supplier, supplier variant, and balance."""
    col = Collection(
        id=f"col-res-{uuid.uuid4().hex[:6]}",
        slug=f"col-res-{uuid.uuid4().hex[:6]}",
        name="Reservation Test Col",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-res-{uuid.uuid4().hex[:6]}",
        slug=f"prod-res-{uuid.uuid4().hex[:6]}",
        title="Reservation Test Prod",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-RES-{uuid.uuid4().hex[:6]}",
        product_id=prod.id,
        price_minor=350000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup = Supplier(
        name="Reservation Test Supplier",
        slug=f"res-sup-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db.add(sup)
    db.flush()

    sv = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var.id,
        active=True,
        supplier_cost_minor=200000,
    )
    db.add(sv)
    db.flush()

    ib = InventoryBalance(
        supplier_variant_id=sv.id,
        on_hand=on_hand,
        version=0,
    )
    db.add(ib)
    db.flush()

    return sv, ib


class TestStockReservationLifecycle:
    def test_reservation_creation_and_owner_summary(self, db_session):
        """Holding stock increments Held, decrements Available, preserves Physical."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=10)

        summary_before = get_inventory_summary(db_session, sv.id)
        assert summary_before.physical == 10
        assert summary_before.held == 0
        assert summary_before.available == 10
        assert summary_before.display_line == "Physical 10 | Held 0 | Available 10"

        order_line_id = uuid.uuid4()
        res = create_stock_reservation(
            db_session,
            supplier_variant_id=sv.id,
            order_line_id=order_line_id,
            quantity=2,
        )

        assert res.id is not None
        assert res.stage == "held"

        summary_after = get_inventory_summary(db_session, sv.id)
        assert summary_after.physical == 10
        assert summary_after.held == 2
        assert summary_after.available == 8
        assert summary_after.display_line == "Physical 10 | Held 2 | Available 8"
        assert len(summary_after.open_reservations) == 1
        assert summary_after.open_reservations[0]["order_line_id"] == order_line_id

    def test_reservation_exceeding_available_raises_insufficient_stock(self, db_session):
        """Cannot reserve more stock than Available."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=5)

        # First reservation of 4
        create_stock_reservation(
            db_session,
            supplier_variant_id=sv.id,
            order_line_id=uuid.uuid4(),
            quantity=4,
        )

        # Second reservation of 2 should fail (Available is only 1)
        with pytest.raises(InsufficientStockError) as exc_info:
            create_stock_reservation(
                db_session,
                supplier_variant_id=sv.id,
                order_line_id=uuid.uuid4(),
                quantity=2,
            )

        assert "Requested: 2, Available: 1" in str(exc_info.value)

    def test_reservation_cancellation_releases_held_stock(self, db_session):
        """Cancelling a reservation immediately restores Available stock."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=10)

        res = create_stock_reservation(
            db_session,
            supplier_variant_id=sv.id,
            order_line_id=uuid.uuid4(),
            quantity=3,
        )

        summary_held = get_inventory_summary(db_session, sv.id)
        assert summary_held.held == 3
        assert summary_held.available == 7

        # Cancel reservation
        transition_reservation_stage(db_session, reservation_id=res.id, new_stage="cancelled")

        summary_cancelled = get_inventory_summary(db_session, sv.id)
        assert summary_cancelled.physical == 10
        assert summary_cancelled.held == 0
        assert summary_cancelled.available == 10
        assert len(summary_cancelled.open_reservations) == 0

    def test_reservation_fulfillment_deducts_physical_stock(self, db_session):
        """Fulfilling a reservation deducts physical stock and appends StockEvent."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=10)

        user = UserAccount(
            auth_subject=f"auth0|{uuid.uuid4().hex[:8]}",
            display_name="Fulfillment Admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        res = create_stock_reservation(
            db_session,
            supplier_variant_id=sv.id,
            order_line_id=uuid.uuid4(),
            quantity=2,
        )

        # Advance to confirmed -> dispatched -> fulfilled
        transition_reservation_stage(db_session, reservation_id=res.id, new_stage="confirmed")
        transition_reservation_stage(db_session, reservation_id=res.id, new_stage="dispatched")
        transition_reservation_stage(
            db_session,
            reservation_id=res.id,
            new_stage="fulfilled",
            actor_user_id=user.id,
        )

        db_session.flush()

        # Check balance & summary
        summary_fulfilled = get_inventory_summary(db_session, sv.id)
        assert summary_fulfilled.physical == 8  # Decremented by 2
        assert summary_fulfilled.held == 0
        assert summary_fulfilled.available == 8

        # Check stock audit events
        events = get_stock_events(db_session, sv.id)
        assert len(events) == 1
        assert events[0].reason == "dispatch"
        assert events[0].delta == -2
        assert events[0].previous_on_hand == 10
        assert events[0].new_on_hand == 8

    def test_terminal_reservation_cannot_be_reopened(self, db_session):
        """Terminal reservations (fulfilled/cancelled/returned) cannot transition to open stages."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=10)

        res = create_stock_reservation(
            db_session,
            supplier_variant_id=sv.id,
            order_line_id=uuid.uuid4(),
            quantity=1,
        )
        transition_reservation_stage(db_session, reservation_id=res.id, new_stage="cancelled")

        with pytest.raises(InvalidReservationTransitionError):
            transition_reservation_stage(db_session, reservation_id=res.id, new_stage="held")

        with pytest.raises(InvalidReservationTransitionError):
            transition_reservation_stage(db_session, reservation_id=res.id, new_stage="confirmed")

    def test_quantity_positive_check_constraint(self, db_session):
        """Database CHECK constraint ck_stock_reservations_quantity_positive rejects <= 0."""
        sv, ib = _setup_variant_with_stock(db_session, on_hand=10)

        stmt = text(
            "INSERT INTO stock_reservations (id, supplier_variant_id, order_line_id, quantity, stage) "
            "VALUES (:id, :sv_id, :ol_id, :qty, :stage)"
        )

        with pytest.raises(IntegrityError):
            db_session.execute(
                stmt,
                {
                    "id": uuid.uuid4(),
                    "sv_id": sv.id,
                    "ol_id": uuid.uuid4(),
                    "qty": 0,
                    "stage": "held",
                },
            )
            db_session.flush()
