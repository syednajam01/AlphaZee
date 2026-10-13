"""
test_payment_separation.py — Defect reproduction and integration tests for Blocker 3:
Payment and supplier confirmation separation, unpaid dispatch guards, and 4-hour payment window.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order
from app.models.suppliers import Supplier, UserAccount
from app.queries.reservations import get_inventory_summary
from app.services.orders import (
    CreateOrderDTO,
    OrderItemDTO,
    place_order,
    verify_bank_payment,
    confirm_supplier_acceptance,
    mark_expired_bank_orders_for_review,
    record_payment_instructions_sent,
    resolve_payment_review,
)
from app.services.shipments import OrderNotDispatchableError, create_shipment


def _setup_catalog(db: Session, on_hand: int = 10):
    uid = uuid.uuid4().hex[:6]
    col = Collection(
        id=f"col-{uid}",
        slug=f"col-{uid}",
        name="Payment Test Collection",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-{uid}",
        slug=f"prod-{uid}",
        title="Payment Test Tee",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-PAY-{uid}",
        product_id=prod.id,
        size="M",
        color="Slate",
        price_minor=400000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup = Supplier(
        name="Vendor Lahore",
        slug=f"vendor-lahore-{uid}",
        status="active",
    )
    db.add(sup)
    db.flush()

    sv = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var.id,
        active=True,
        supplier_cost_minor=250000,
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

    user = UserAccount(
        auth_subject=f"auth-admin-{uid}",
        display_name="Store Owner",
    )
    db.add(user)
    db.flush()

    return var, sv, ib, user


def test_dispatch_unverified_bank_transfer_rejected(db_session: Session):
    """
    Dispatch must refuse to create a courier shipment if an order is bank_transfer
    and payment is still pending.
    """
    var, sv, ib, user = _setup_catalog(db_session, on_hand=5)

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Usman Tariq",
            customer_phone="03001234567",
            customer_email="usman@example.com",
            shipping_address_line1="DHA Phase 5",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.flush()

    assert order.payment_method == "bank_transfer"
    assert order.payment_status == "pending"

    # Attempt dispatch without verifying payment
    with pytest.raises(OrderNotDispatchableError) as exc_info:
        create_shipment(
            db_session,
            order_id=order.id,
            courier_code="trax",
            tracking_number="TRX-123456",
        )
    assert "payment" in str(exc_info.value).lower() or "verified" in str(exc_info.value).lower()


def test_verify_payment_does_not_confirm_supplier_or_advance_reservations(db_session: Session):
    """
    verify_bank_payment() is a financial operation confirming received funds.
    It must NOT mark order_status='confirmed' or advance stock reservations to 'confirmed'.
    """
    var, sv, ib, user = _setup_catalog(db_session, on_hand=5)

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Bilal Ahmed",
            customer_phone="03219876543",
            shipping_address_line1="F-7/2",
            shipping_city="Islamabad",
            shipping_province="ICT",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var.id, quantity=2)],
        ),
    )
    db_session.flush()

    reservation = db_session.scalars(
        select(StockReservation).where(
            StockReservation.order_line_id == order.lines[0].id
        )
    ).first()
    assert reservation.stage == "held"
    assert order.order_status == "placed"
    assert order.payment_status == "pending"

    # Owner verifies bank funds
    verify_bank_payment(
        db_session,
        order_id=order.id,
        verified_by_user_id=user.id,
    )
    db_session.flush()

    assert order.payment_status == "verified"
    # Order status must remain 'placed' until supplier acceptance is confirmed
    assert order.order_status == "placed"
    db_session.refresh(reservation)
    # Reservation must remain 'held', not prematurely 'confirmed'
    assert reservation.stage == "held"


def test_confirm_supplier_acceptance_advances_order_and_reservations(db_session: Session):
    """
    confirm_supplier_acceptance() records supplier confirmation and advances
    order_status to 'confirmed' and reservation stage to 'confirmed'.
    """
    var, sv, ib, user = _setup_catalog(db_session, on_hand=5)

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Kashif Raza",
            customer_phone="03335557788",
            shipping_address_line1="Gulberg III",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.flush()

    reservation = db_session.scalars(
        select(StockReservation).where(
            StockReservation.order_line_id == order.lines[0].id
        )
    ).first()
    assert reservation.stage == "held"
    assert order.order_status == "placed"

    # Confirm supplier acceptance
    confirmed_order = confirm_supplier_acceptance(
        db_session,
        order_id=order.id,
        supplier_notes="Stock confirmed at Lahore warehouse",
    )
    db_session.flush()

    assert confirmed_order.order_status == "confirmed"
    assert confirmed_order.supplier_confirmed_at is not None
    assert confirmed_order.supplier_notes == "Stock confirmed at Lahore warehouse"

    db_session.refresh(reservation)
    assert reservation.stage == "confirmed"

    # Now dispatch can proceed
    shipment = create_shipment(
        db_session,
        order_id=order.id,
        courier_code="leopards",
        tracking_number="LMS-998877",
    )
    assert shipment.status == "dispatched"
    assert order.order_status == "dispatched"


def test_four_hour_payment_window_and_expired_order_review(db_session: Session):
    """
    The deadline begins only after a confirmed handoff. Expiry keeps holds until review.
    """
    var, sv, ib, user = _setup_catalog(db_session, on_hand=2)

    now = datetime.now(timezone.utc)

    # 1. Checkout does not start a timer.
    bank_order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Saad Sheikh",
            customer_phone="03009998877",
            shipping_address_line1="Clifton Block 2",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.flush()

    assert bank_order.payment_deadline_at is None
    confirm_supplier_acceptance(db_session, order_id=bank_order.id)
    assert bank_order.payment_deadline_at is None
    record_payment_instructions_sent(db_session, order_id=bank_order.id, actor_user_id=user.id,
                                     channel='sms', reference='SAMPLE-message-123')
    diff_hours = (bank_order.payment_deadline_at - now).total_seconds() / 3600
    assert 3.9 <= diff_hours <= 4.1

    # 2. COD order does not have payment_deadline_at
    cod_order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Hamza Mir",
            customer_phone="03123456789",
            shipping_address_line1="Johar Town",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        ),
    )
    db_session.flush()

    assert cod_order.payment_deadline_at is None

    # Check available stock is 0 (2 on hand, 2 held)
    summary = get_inventory_summary(db_session, sv.id)
    assert summary.available == 0

    # 3. Simulate deadline expiration on the bank order
    bank_order.payment_deadline_at = now - timedelta(minutes=10)
    db_session.flush()

    # Expiry flags review and keeps the held quantity intact.
    review = mark_expired_bank_orders_for_review(db_session)
    assert len(review) == 1
    assert bank_order.payment_review_status == 'required'
    assert bank_order.order_status == 'confirmed'
    summary_after = get_inventory_summary(db_session, sv.id)
    assert summary_after.available == 0

    resolved = resolve_payment_review(db_session, order_id=bank_order.id, actor_user_id=user.id,
                                      resolution='release_unpaid', funds_checked=True,
                                      note='Bank balance and pending transfers checked; no funds found')
    assert resolved.order_status == 'cancelled'
    assert resolved.payment_review_status == 'released_unpaid'
    assert get_inventory_summary(db_session, sv.id).available == 1
