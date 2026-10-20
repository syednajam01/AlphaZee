"""
test_orders_integration.py — Integration tests for Order processing, purchase snapshots, stock reservation coordination, and payment workflows.
"""

from __future__ import annotations

import uuid
import pytest

pytestmark = pytest.mark.usefixtures("configured_bank")
from sqlalchemy import select

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine, PaymentReceipt
from app.models.suppliers import Supplier, UserAccount
from app.queries.inventory import get_stock_events
from app.queries.reservations import InsufficientStockError, get_inventory_summary
from app.services.orders import (
    CreateOrderDTO,
    OrderItemDTO,
    cancel_order,
    confirm_supplier_acceptance,
    deliver_order,
    place_order,
    record_payment_instructions_sent,
    upload_payment_receipt,
    verify_bank_payment,
)


def _setup_store_catalog(db, on_hand: int = 10):
    """Helper to set up catalog, supplier, variant, and physical stock."""
    col = Collection(
        id=f"col-ord-{uuid.uuid4().hex[:6]}",
        slug=f"col-ord-{uuid.uuid4().hex[:6]}",
        name="Orders Test Collection",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-ord-{uuid.uuid4().hex[:6]}",
        slug=f"prod-ord-{uuid.uuid4().hex[:6]}",
        title="Heavyweight Boxy Tee",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-TEE-L-{uuid.uuid4().hex[:6]}",
        product_id=prod.id,
        size="L",
        color="Chalk White",
        price_minor=350000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup = Supplier(
        name="Lahore Apparel Mills",
        slug=f"lahore-apparel-{uuid.uuid4().hex[:6]}",
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

    return var, sv, ib


class TestOrderPlacementAndSnapshots:
    def test_place_order_creates_snapshots_and_holds_reservation(self, db_session):
        """Placing an order creates immutable snapshots and locks stock reservations."""
        var, sv, ib = _setup_store_catalog(db_session, on_hand=10)
        from app.services.store_settings import get_or_create_store_settings
        delivery = get_or_create_store_settings(db_session)
        delivery.shipping_rules_configured = True
        delivery.standard_shipping_fee_minor = 25000
        db_session.flush()

        dto = CreateOrderDTO(
            customer_name="Zainab Ahmed",
            customer_phone="0300-1234567",
            customer_email="zainab@example.com",
            shipping_address_line1="Apartment 4B, Clifton Block 5",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="cod",
            shipping_fee_minor=25000,
            items=[OrderItemDTO(variant_id=var.id, quantity=2)],
        )

        order = place_order(db_session, dto)

        assert order.id is not None
        assert order.order_number.startswith("AZ-")
        assert order.customer_phone == "03001234567"
        assert order.subtotal_minor == 700000
        assert order.total_minor == 725000
        assert order.payment_status == "pending"
        assert order.order_status == "placed"

        # Verify OrderLine snapshot
        assert len(order.lines) == 1
        line = order.lines[0]
        assert line.product_title_snapshot == "Heavyweight Boxy Tee"
        assert line.variant_sku_snapshot == var.sku
        assert line.variant_size_snapshot == "L"
        assert line.variant_color_snapshot == "Chalk White"
        assert line.unit_price_minor == 350000
        assert line.unit_cost_minor == 200000
        assert line.quantity == 2
        assert line.line_total_minor == 700000

        # Verify stock reservation locked
        summary = get_inventory_summary(db_session, sv.id)
        assert summary.physical == 10
        assert summary.held == 2
        assert summary.available == 8

    def test_place_order_insufficient_stock_reverts(self, db_session):
        """Placing an order when quantity > available raises InsufficientStockError."""
        var, sv, ib = _setup_store_catalog(db_session, on_hand=1)

        dto = CreateOrderDTO(
            customer_name="Hamza Tariq",
            customer_phone="03211112233",
            shipping_address_line1="House 5, Street 2",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=2)],  # Exceeds available (1)
        )

        with pytest.raises(InsufficientStockError):
            place_order(db_session, dto)

        # Confirm nothing held
        summary = get_inventory_summary(db_session, sv.id)
        assert summary.physical == 1
        assert summary.held == 0
        assert summary.available == 1


class TestOrderLifecycleAndPayments:
    def test_bank_transfer_receipt_and_verification(self, db_session):
        """Uploading receipt and owner verification advances payment to verified and order to confirmed."""
        var, sv, ib = _setup_store_catalog(db_session, on_hand=10)

        owner = UserAccount(
            auth_subject=f"auth0|{uuid.uuid4().hex[:8]}",
            display_name="Owner Najam",
            is_active=True,
        )
        db_session.add(owner)
        db_session.flush()

        dto = CreateOrderDTO(
            customer_name="Bilal Shah",
            customer_phone="03335556677",
            shipping_address_line1="House 10, Street 1",
            shipping_city="Islamabad",
            shipping_province="Islamabad Capital Territory",
            payment_method="bank_transfer",
            items=[OrderItemDTO(variant_id=var.id, quantity=1)],
        )
        order = place_order(db_session, dto)

        confirm_supplier_acceptance(db_session, order_id=order.id)
        record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=owner.id,
                                         channel='sms', reference='SAMPLE-message-123')

        # Upload receipt
        receipt = upload_payment_receipt(
            db_session,
            order_id=order.id,
            receipt_image_url="https://storage.alphazee.pk/receipts/rec-12345.png",
            bank_reference="FT2610118899",
        )
        assert receipt.id is not None
        assert receipt.verified_at is None

        # Owner verifies funds in bank account
        verify_bank_payment(
            db_session,
            order_id=order.id,
            verified_by_user_id=owner.id,
            receipt_id=receipt.id,
        )

        db_session.expire_all()
        reloaded_order = db_session.get(Order, order.id)
        assert reloaded_order.payment_status == "verified"
        assert reloaded_order.order_status == "confirmed"

        reloaded_receipt = db_session.get(PaymentReceipt, receipt.id)
        assert reloaded_receipt.verified_at is not None
        assert reloaded_receipt.verified_by_user_id == owner.id

    def test_cancel_order_releases_stock(self, db_session):
        """Cancelling an order immediately releases held stock back to available."""
        var, sv, ib = _setup_store_catalog(db_session, on_hand=10)

        dto = CreateOrderDTO(
            customer_name="Usman Riaz",
            customer_phone="03451122334",
            shipping_address_line1="Street 5",
            shipping_city="Rawalpindi",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=3)],
        )
        order = place_order(db_session, dto)

        # Verify held
        summary_held = get_inventory_summary(db_session, sv.id)
        assert summary_held.held == 3
        assert summary_held.available == 7

        # Cancel order
        cancel_order(db_session, order_id=order.id, reason="Customer changed mind")

        db_session.expire_all()
        reloaded_order = db_session.get(Order, order.id)
        assert reloaded_order.order_status == "cancelled"

        # Verify stock released
        summary_cancelled = get_inventory_summary(db_session, sv.id)
        assert summary_cancelled.physical == 10
        assert summary_cancelled.held == 0
        assert summary_cancelled.available == 10

    def test_deliver_order_deducts_physical_inventory(self, db_session):
        """Delivering an order fulfills reservations, decrements on_hand, and appends StockEvent."""
        var, sv, ib = _setup_store_catalog(db_session, on_hand=10)

        admin = UserAccount(
            auth_subject=f"auth0|{uuid.uuid4().hex[:8]}",
            display_name="Courier Dispatcher",
            is_active=True,
        )
        db_session.add(admin)
        db_session.flush()

        dto = CreateOrderDTO(
            customer_name="Sarah Malik",
            customer_phone="03019988776",
            shipping_address_line1="Plot 44, DHA Phase 6",
            shipping_city="Karachi",
            shipping_province="Sindh",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var.id, quantity=2)],
        )
        order = place_order(db_session, dto)

        # Supplier acceptance and an allocated dispatch precede delivery.
        from app.services.orders import confirm_supplier_acceptance
        from app.services.shipments import create_shipment
        confirm_supplier_acceptance(db_session, order_id=order.id)
        create_shipment(db_session, order_id=order.id, courier_code='manual',
                        tracking_number=f'DEL-{uuid.uuid4().hex[:8]}', actor_user_id=admin.id)
        deliver_order(db_session, order_id=order.id, actor_user_id=admin.id)

        db_session.expire_all()
        reloaded_order = db_session.get(Order, order.id)
        assert reloaded_order.order_status == "delivered"
        assert reloaded_order.payment_status == "verified"

        # Verify physical stock deducted
        summary_delivered = get_inventory_summary(db_session, sv.id)
        assert summary_delivered.physical == 8
        assert summary_delivered.held == 0
        assert summary_delivered.available == 8

        # Verify StockEvent audit log
        events = get_stock_events(db_session, sv.id)
        assert len(events) == 1
        assert events[0].reason == "dispatch"
        assert events[0].delta == -2
        assert events[0].previous_on_hand == 10
        assert events[0].new_on_hand == 8
