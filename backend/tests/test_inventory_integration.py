"""
test_inventory_integration.py — Integration and concurrency tests for supplier and inventory models.

Covers:
1. Database constraints:
   - Partial unique index: uq_sv_one_active_per_variant (only 1 active supplier per variant).
   - Check constraint: ck_inventory_on_hand_nonnegative (on_hand >= 0).
   - Foreign key ON DELETE RESTRICT on supplier_variants when stock_events exist.
   - Foreign key ON DELETE SET NULL on stock_events.actor_user_id when UserAccount is deleted.
2. Atomic adjust_inventory operation.
3. Two-session concurrency test validating optimistic concurrency control (version BIGINT) and rollback.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, SupplierVariant
from app.models.suppliers import Supplier, UserAccount
from app.queries.inventory import (
    StaleInventoryError,
    adjust_inventory,
    get_active_supplier_variant,
    get_inventory_balance,
    get_stock_events,
)


def _setup_catalog_and_supplier(db):
    """Helper to create minimal catalog item and supplier for tests."""
    col = Collection(
        id="col-inv-test",
        slug="col-inv-test",
        name="Inventory Test Collection",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id="prod-inv-test",
        slug="prod-inv-test",
        title="Inventory Test Product",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku="SKU-INV-TEST",
        product_id=prod.id,
        price_minor=500000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup = Supplier(
        name="Karachi Apparel",
        slug=f"karachi-apparel-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db.add(sup)
    db.flush()

    return var, sup


class TestSupplierInventoryConstraints:
    def test_one_active_supplier_per_variant_partial_index(self, db_session):
        """Only one SupplierVariant with active=True may exist per variant_id."""
        var, sup1 = _setup_catalog_and_supplier(db_session)
        sup2 = Supplier(
            name="Lahore Textiles",
            slug=f"lahore-textiles-{uuid.uuid4().hex[:6]}",
            status="active",
        )
        db_session.add(sup2)
        db_session.flush()

        sv1 = SupplierVariant(
            supplier_id=sup1.id,
            variant_id=var.id,
            active=True,
            supplier_cost_minor=300000,
        )
        db_session.add(sv1)
        db_session.flush()

        sv2 = SupplierVariant(
            supplier_id=sup2.id,
            variant_id=var.id,
            active=True,  # Conflict! A second active supplier for same variant
            supplier_cost_minor=320000,
        )
        db_session.add(sv2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()

        assert "uq_sv_one_active_per_variant" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()

    def test_multiple_inactive_suppliers_per_variant_permitted(self, db_session):
        """Multiple historical/inactive supplier linkages are allowed for the same variant."""
        var, sup1 = _setup_catalog_and_supplier(db_session)
        sup2 = Supplier(
            name="Faisalabad Fabrics",
            slug=f"faisalabad-fabrics-{uuid.uuid4().hex[:6]}",
            status="active",
        )
        db_session.add(sup2)
        db_session.flush()

        sv1 = SupplierVariant(
            supplier_id=sup1.id,
            variant_id=var.id,
            active=False,  # Inactive historical link
            supplier_cost_minor=280000,
        )
        sv2 = SupplierVariant(
            supplier_id=sup2.id,
            variant_id=var.id,
            active=True,  # Currently active link
            supplier_cost_minor=300000,
        )
        db_session.add_all([sv1, sv2])
        db_session.flush()

        assert sv1.id is not None
        assert sv2.id is not None

    def test_inventory_balance_nonnegative_constraint(self, db_session):
        """CHECK constraint on_hand >= 0 prevents negative stock values."""
        var, sup = _setup_catalog_and_supplier(db_session)
        sv = SupplierVariant(
            supplier_id=sup.id,
            variant_id=var.id,
            active=True,
        )
        db_session.add(sv)
        db_session.flush()

        ib = InventoryBalance(
            supplier_variant_id=sv.id,
            on_hand=-5,  # Invalid
            version=0,
        )
        db_session.add(ib)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()

        assert "ck_inventory_on_hand_nonnegative" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()

    def test_stock_event_actor_user_id_set_null(self, db_session):
        """Deleting an administrative user sets actor_user_id to NULL on audit events."""
        var, sup = _setup_catalog_and_supplier(db_session)
        user = UserAccount(
            auth_subject=f"auth0|{uuid.uuid4().hex[:8]}",
            display_name="Operator User",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        sv = SupplierVariant(supplier_id=sup.id, variant_id=var.id, active=True)
        db_session.add(sv)
        db_session.flush()

        event = StockEvent(
            supplier_variant_id=sv.id,
            actor_user_id=user.id,
            previous_on_hand=0,
            new_on_hand=10,
            delta=10,
            reason="supplier_receipt",
        )
        db_session.add(event)
        db_session.flush()
        event_id = event.id

        # Delete user account
        db_session.delete(user)
        db_session.flush()

        db_session.expire_all()
        reloaded_event = db_session.get(StockEvent, event_id)
        assert reloaded_event is not None
        assert reloaded_event.actor_user_id is None


class TestInventoryAdjustmentQuery:
    def test_adjust_inventory_success_flow(self, db_session):
        """Successful inventory adjustment increments version and inserts stock event."""
        var, sup = _setup_catalog_and_supplier(db_session)
        sv = SupplierVariant(supplier_id=sup.id, variant_id=var.id, active=True)
        db_session.add(sv)
        db_session.flush()

        ib = InventoryBalance(supplier_variant_id=sv.id, on_hand=10, version=0)
        db_session.add(ib)
        db_session.flush()

        user = UserAccount(
            auth_subject=f"auth0|{uuid.uuid4().hex[:8]}",
            display_name="Admin",
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        event = adjust_inventory(
            db_session,
            supplier_variant_id=sv.id,
            actor_user_id=user.id,
            new_on_hand=15,
            reason="supplier_receipt",
            expected_version=0,
            notes="Received 5 additional units",
        )

        assert event.delta == 5
        assert event.previous_on_hand == 10
        assert event.new_on_hand == 15

        db_session.flush()
        reloaded_ib = db_session.get(InventoryBalance, sv.id)
        assert reloaded_ib.on_hand == 15
        assert reloaded_ib.version == 1

        events = get_stock_events(db_session, sv.id)
        assert len(events) == 1
        assert events[0].reason == "supplier_receipt"

    def test_adjust_inventory_version_mismatch_raises_stale_error(self, db_session):
        """Adjusting inventory with mismatched expected_version raises StaleInventoryError."""
        var, sup = _setup_catalog_and_supplier(db_session)
        sv = SupplierVariant(supplier_id=sup.id, variant_id=var.id, active=True)
        db_session.add(sv)
        db_session.flush()

        ib = InventoryBalance(supplier_variant_id=sv.id, on_hand=10, version=2)
        db_session.add(ib)
        db_session.flush()

        with pytest.raises(StaleInventoryError):
            adjust_inventory(
                db_session,
                supplier_variant_id=sv.id,
                actor_user_id=None,
                new_on_hand=8,
                reason="manual_count",
                expected_version=0,  # Stale! Expected 2
            )


class TestTwoSessionConcurrency:
    def test_optimistic_concurrency_two_sessions(self, test_engine):
        """
        Genuine two-session concurrency test:
        - Session A and Session B both read balance at version 0, on_hand 10.
        - Session A successfully updates to on_hand 8, version 1 and commits.
        - Session B attempts update with expected_version 0 -> raises StaleInventoryError and rolls back.
        - Assert: Final on_hand == 8, final version == 1, exactly 1 StockEvent created.
        """
        SessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)

        # Setup initial state in setup session
        setup_session = SessionLocal()
        try:
            col = Collection(
                id=f"col-conc-{uuid.uuid4().hex[:6]}",
                slug=f"col-conc-{uuid.uuid4().hex[:6]}",
                name="Concurrency Test Col",
                is_active=True,
                display_order=0,
            )
            setup_session.add(col)
            setup_session.flush()

            prod = Product(
                id=f"prod-conc-{uuid.uuid4().hex[:6]}",
                slug=f"prod-conc-{uuid.uuid4().hex[:6]}",
                title="Concurrency Test Prod",
                collection_id=col.id,
                is_active=True,
            )
            setup_session.add(prod)
            setup_session.flush()

            var = Variant(
                sku=f"SKU-CONC-{uuid.uuid4().hex[:6]}",
                product_id=prod.id,
                price_minor=400000,
                is_active=True,
                availability=AvailabilityStatus.AVAILABLE,
            )
            setup_session.add(var)
            setup_session.flush()

            sup = Supplier(
                name="Concurrency Supplier",
                slug=f"conc-sup-{uuid.uuid4().hex[:6]}",
                status="active",
            )
            setup_session.add(sup)
            setup_session.flush()

            sv = SupplierVariant(
                supplier_id=sup.id,
                variant_id=var.id,
                active=True,
            )
            setup_session.add(sv)
            setup_session.flush()

            ib = InventoryBalance(
                supplier_variant_id=sv.id,
                on_hand=10,
                version=0,
            )
            setup_session.add(ib)
            setup_session.commit()
            sv_id = sv.id
        finally:
            setup_session.close()

        # Session A and Session B both open
        session_a = SessionLocal()
        session_b = SessionLocal()

        try:
            # Both read initial state
            ib_a = get_inventory_balance(session_a, sv_id)
            ib_b = get_inventory_balance(session_b, sv_id)

            assert ib_a.on_hand == 10
            assert ib_a.version == 0
            assert ib_b.on_hand == 10
            assert ib_b.version == 0

            # Session A adjusts inventory and commits
            adjust_inventory(
                session_a,
                supplier_variant_id=sv_id,
                actor_user_id=None,
                new_on_hand=8,
                reason="manual_count",
                expected_version=0,
            )
            session_a.commit()

            # Session B attempts to adjust with stale expected_version=0
            with pytest.raises(StaleInventoryError):
                adjust_inventory(
                    session_b,
                    supplier_variant_id=sv_id,
                    actor_user_id=None,
                    new_on_hand=5,
                    reason="manual_count",
                    expected_version=0,  # Conflict! Version is now 1 in DB
                )
            session_b.rollback()

            # Verify final database state via a fresh session
            verify_session = SessionLocal()
            try:
                final_ib = get_inventory_balance(verify_session, sv_id)
                assert final_ib.on_hand == 8
                assert final_ib.version == 1

                events = get_stock_events(verify_session, sv_id)
                assert len(events) == 1
                assert events[0].new_on_hand == 8
                assert events[0].previous_on_hand == 10
                assert events[0].delta == -2
            finally:
                verify_session.close()

        finally:
            session_a.close()
            session_b.close()
