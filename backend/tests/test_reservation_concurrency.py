"""
test_reservation_concurrency.py — Integration tests for StockReservation concurrency & checkout idempotency.

Reproduces Blocker 2:
1. Reservation concurrency:
   Two concurrent transactions attempting to hold the last remaining unit (on_hand = 1).
   Without SELECT ... FOR UPDATE row-level locking on inventory_balances, both claim the unit.
   With SELECT ... FOR UPDATE, one succeeds and the other receives InsufficientStockError.
2. Reservation idempotency:
   Calling create_stock_reservation with an idempotency_key returns the existing open reservation.
3. Order checkout idempotency:
   Submitting POST /api/v1/orders with the same Idempotency-Key header returns the existing order
   without creating duplicate order rows or duplicate stock reservations.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order
from app.models.suppliers import Supplier
from app.queries.reservations import (
    InsufficientStockError,
    create_stock_reservation,
    get_inventory_summary,
)
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order


def _setup_conc_item(engine, on_hand: int = 1):
    """Create committed catalog items and inventory balance for multi-session testing."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:6]
        col = Collection(
            id=f"col-c-{suffix}",
            slug=f"col-c-{suffix}",
            name="Conc Collection",
            is_active=True,
            display_order=0,
        )
        session.add(col)
        session.flush()

        prod = Product(
            id=f"prod-c-{suffix}",
            slug=f"prod-c-{suffix}",
            title="Conc Product",
            collection_id=col.id,
            is_active=True,
        )
        session.add(prod)
        session.flush()

        var = Variant(
            sku=f"SKU-C-{suffix}",
            product_id=prod.id,
            price_minor=300000,
            is_active=True,
            availability=AvailabilityStatus.AVAILABLE,
        )
        session.add(var)
        session.flush()

        sup = Supplier(
            name="Conc Supplier",
            slug=f"sup-c-{suffix}",
            status="active",
        )
        session.add(sup)
        session.flush()

        sv = SupplierVariant(
            supplier_id=sup.id,
            variant_id=var.id,
            active=True,
            supplier_cost_minor=150000,
        )
        session.add(sv)
        session.flush()

        balance = InventoryBalance(
            supplier_variant_id=sv.id,
            on_hand=on_hand,
            version=1,
        )
        session.add(balance)
        session.commit()

        return {
            "variant_id": var.id,
            "sv_id": sv.id,
        }
    finally:
        session.close()


def test_concurrent_reservations_cannot_oversell(test_engine):
    """
    Two concurrent sessions try to claim the last single unit (on_hand = 1).
    Exactly one must succeed; the other must receive InsufficientStockError.
    Total open reservations must NEVER exceed on_hand.
    """
    setup = _setup_conc_item(test_engine, on_hand=1)
    sv_id = setup["sv_id"]
    SessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)

    results = []
    errors = []
    line1 = uuid.uuid4()
    line2 = uuid.uuid4()

    barrier = threading.Barrier(2)

    def worker(order_line_id: uuid.UUID):
        s = SessionLocal()
        try:
            barrier.wait(timeout=5)
            # Both threads invoke create_stock_reservation simultaneously
            res = create_stock_reservation(
                s,
                supplier_variant_id=sv_id,
                order_line_id=order_line_id,
                quantity=1,
            )
            s.commit()
            results.append(res.id)
        except InsufficientStockError as err:
            s.rollback()
            errors.append(err)
        except Exception as err:
            s.rollback()
            errors.append(err)
        finally:
            s.close()

    t1 = threading.Thread(target=worker, args=(line1,))
    t2 = threading.Thread(target=worker, args=(line2,))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Verification:
    # Exactly one succeeded, exactly one failed with InsufficientStockError
    assert len(results) == 1, f"Expected 1 successful reservation, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 failed reservation, got {len(errors)}"
    assert isinstance(errors[0], InsufficientStockError)

    # Check total held reservations in database
    verify_session = SessionLocal()
    try:
        summary = get_inventory_summary(verify_session, sv_id)
        assert summary.physical == 1
        assert summary.held == 1, f"Expected held=1, but got {summary.held} (oversold!)"
        assert summary.available == 0
    finally:
        verify_session.close()


def test_reservation_idempotency_returns_existing_record(db_session):
    """
    Calling create_stock_reservation with an idempotency_key returns the existing
    reservation and does not hold additional inventory.
    """
    var_id, sv_id = None, None
    suffix = uuid.uuid4().hex[:6]
    col = Collection(id=f"col-{suffix}", slug=f"col-{suffix}", name="Col", is_active=True, display_order=0)
    db_session.add(col)
    db_session.flush()

    prod = Product(id=f"prod-{suffix}", slug=f"prod-{suffix}", title="Prod", collection_id=col.id, is_active=True)
    db_session.add(prod)
    db_session.flush()

    var = Variant(sku=f"SKU-{suffix}", product_id=prod.id, price_minor=100000, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(var)
    db_session.flush()

    sup = Supplier(name="Sup", slug=f"sup-{suffix}", status="active")
    db_session.add(sup)
    db_session.flush()

    sv = SupplierVariant(supplier_id=sup.id, variant_id=var.id, active=True, supplier_cost_minor=50000)
    db_session.add(sv)
    db_session.flush()

    bal = InventoryBalance(supplier_variant_id=sv.id, on_hand=10, version=1)
    db_session.add(bal)
    db_session.flush()

    idemp_key = f"res-idemp-{uuid.uuid4().hex}"
    line_id = uuid.uuid4()

    # 1. First call creates reservation
    res1 = create_stock_reservation(
        db_session,
        supplier_variant_id=sv.id,
        order_line_id=line_id,
        quantity=2,
        idempotency_key=idemp_key,
    )
    db_session.flush()

    # 2. Duplicate call with same idempotency_key returns original reservation
    res2 = create_stock_reservation(
        db_session,
        supplier_variant_id=sv.id,
        order_line_id=line_id,
        quantity=2,
        idempotency_key=idemp_key,
    )
    db_session.flush()

    assert res1.id == res2.id

    # 3. Held count must be 2, not 4
    summary = get_inventory_summary(db_session, sv.id)
    assert summary.held == 2
    assert summary.available == 8


def test_order_checkout_idempotency_header(client, db_session):
    """
    Submitting POST /api/v1/orders with Idempotency-Key header multiple times returns
    the same created order without duplicate submissions or double stock holds.
    """
    suffix = uuid.uuid4().hex[:6]
    col = Collection(id=f"col-{suffix}", slug=f"col-{suffix}", name="Col", is_active=True, display_order=0)
    db_session.add(col)
    db_session.flush()

    prod = Product(id=f"prod-{suffix}", slug=f"prod-{suffix}", title="Prod", collection_id=col.id, is_active=True)
    db_session.add(prod)
    db_session.flush()

    var = Variant(sku=f"SKU-{suffix}", product_id=prod.id, price_minor=250000, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(var)
    db_session.flush()

    sup = Supplier(name="Sup", slug=f"sup-{suffix}", status="active")
    db_session.add(sup)
    db_session.flush()

    sv = SupplierVariant(supplier_id=sup.id, variant_id=var.id, active=True, supplier_cost_minor=100000)
    db_session.add(sv)
    db_session.flush()

    bal = InventoryBalance(supplier_variant_id=sv.id, on_hand=5, version=1)
    db_session.add(bal)
    db_session.flush()

    idemp_key = f"chkout-{uuid.uuid4().hex}"
    payload = {
        "customer_name": "Idempotent Buyer",
        "customer_phone": "03001234567",
        "shipping_address_line1": "Street 1",
        "shipping_city": "Lahore",
        "shipping_province": "Punjab",
        "payment_method": "cod",
        "items": [{"variant_id": var.id, "quantity": 1}],
    }

    # 1. First submission
    res1 = client.post("/api/v1/orders", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 201
    order1 = res1.json()

    # 2. Duplicate submission with identical header
    res2 = client.post("/api/v1/orders", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code in (200, 201)
    order2 = res2.json()

    # Must be the exact same order
    assert order1["id"] == order2["id"]
    assert order1["order_number"] == order2["order_number"]

    # Exactly 1 order in database
    orders = db_session.scalars(select(Order).where(Order.customer_name == "Idempotent Buyer")).all()
    assert len(orders) == 1

    # Exactly 1 unit held
    summary = get_inventory_summary(db_session, sv.id)
    assert summary.held == 1
    assert summary.available == 4
