"""
test_orders_unit.py — Unit tests for Order, OrderLine, and PaymentReceipt models and phone normalization.
"""

import uuid
import pytest

from app.models.orders import (
    Order,
    OrderLine,
    PaymentReceipt,
    normalize_pakistan_phone,
)


def test_normalize_pakistan_phone_valid():
    assert normalize_pakistan_phone("03001234567") == "03001234567"
    assert normalize_pakistan_phone("+923001234567") == "03001234567"
    assert normalize_pakistan_phone("923001234567") == "03001234567"
    assert normalize_pakistan_phone("0300-1234567") == "03001234567"
    assert normalize_pakistan_phone("  0300 123 4567  ") == "03001234567"
    assert normalize_pakistan_phone("0321 (9876543)") == "03219876543"


def test_normalize_pakistan_phone_invalid():
    with pytest.raises(ValueError, match="Invalid Pakistani mobile phone number"):
        normalize_pakistan_phone("0211234567")  # Landline

    with pytest.raises(ValueError, match="Invalid Pakistani mobile phone number"):
        normalize_pakistan_phone("0300123456")  # Too short

    with pytest.raises(ValueError, match="Invalid Pakistani mobile phone number"):
        normalize_pakistan_phone("030012345678")  # Too long

    with pytest.raises(ValueError, match="Invalid Pakistani mobile phone number"):
        normalize_pakistan_phone("+14155552671")  # US number


def test_order_model_instantiation_and_validation():
    order = Order(
        order_number="AZ-2026-0001",
        customer_name="Ali Khan",
        customer_phone="+923001234567",
        shipping_address_line1="House 12, Street 4, Sector F-8/2",
        shipping_city="Islamabad",
        shipping_province="Islamabad Capital Territory",
        payment_method="cod",
        payment_status="pending",
        order_status="placed",
        subtotal_minor=500000,
        shipping_fee_minor=25000,
        total_minor=525000,
    )
    assert order.order_number == "AZ-2026-0001"
    assert order.customer_phone == "03001234567"
    assert order.payment_method == "cod"
    assert order.payment_status == "pending"
    assert order.order_status == "placed"
    assert order.total_minor == 525000
    assert "AZ-2026-0001" in repr(order)



def test_order_model_rejects_invalid_enums():
    with pytest.raises(ValueError, match="Invalid payment method"):
        Order(
            order_number="AZ-BAD-1",
            customer_name="Ali Khan",
            customer_phone="03001234567",
            shipping_address_line1="Street 1",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="easy_paisa",  # Not supported yet
            subtotal_minor=1000,
            total_minor=1000,
        )

    with pytest.raises(ValueError, match="Invalid payment status"):
        Order(
            order_number="AZ-BAD-2",
            customer_name="Ali Khan",
            customer_phone="03001234567",
            shipping_address_line1="Street 1",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            payment_status="unknown_status",
            subtotal_minor=1000,
            total_minor=1000,
        )


def test_order_line_instantiation():
    ol_id = uuid.uuid4()
    order_id = uuid.uuid4()
    line = OrderLine(
        id=ol_id,
        order_id=order_id,
        variant_id=1,
        product_title_snapshot="Heavyweight Boxy Tee",
        variant_sku_snapshot="PROD-TEE-L-BLACK",
        variant_size_snapshot="L",
        variant_color_snapshot="Black",
        unit_price_minor=350000,
        unit_cost_minor=200000,
        quantity=2,
        line_total_minor=700000,
    )
    assert line.id == ol_id
    assert line.order_id == order_id
    assert line.product_title_snapshot == "Heavyweight Boxy Tee"
    assert line.line_total_minor == 700000
    assert repr(line).startswith("<OrderLine")


def test_order_line_quantity_validation():
    with pytest.raises(ValueError, match="Line item quantity must be strictly positive"):
        OrderLine(
            order_id=uuid.uuid4(),
            variant_id=1,
            product_title_snapshot="Tee",
            variant_sku_snapshot="SKU-1",
            unit_price_minor=100,
            quantity=0,
            line_total_minor=0,
        )
