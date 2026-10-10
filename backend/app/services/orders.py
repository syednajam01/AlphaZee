"""
orders.py — Service layer for order placement, snapshotting, stock reservation coordination, and payment verification.

Coordinates:
- Authoritative backend pricing & snapshotting (title, SKU, options, retail price, wholesale cost).
- Atomic stock reservation holds on order placement (rolling back on insufficient stock).
- Bank transfer receipt verification.
- Order cancellation (immediate release of held stock).
- Order delivery / fulfillment (synchronizing physical inventory deductions and stock events).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import AvailabilityStatus, Product, Variant
from app.models.inventory import StockReservation, SupplierVariant
from app.models.orders import (
    ALLOWED_PAYMENT_METHODS,
    Order,
    OrderLine,
    PaymentReceipt,
    normalize_pakistan_phone,
)
from app.queries.inventory import get_active_supplier_variant
from app.queries.reservations import (
    InsufficientStockError,
    create_stock_reservation,
    transition_reservation_stage,
)


from app.services.promotions import record_coupon_usage, validate_coupon


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class OrderItemDTO:
    variant_id: int
    quantity: int


@dataclass(frozen=True)
class CreateOrderDTO:
    customer_name: str
    customer_phone: str
    shipping_address_line1: str
    shipping_city: str
    shipping_province: str
    payment_method: str
    items: list[OrderItemDTO]
    customer_email: str | None = None
    shipping_address_line2: str | None = None
    shipping_postal_code: str | None = None
    shipping_fee_minor: int = 0
    coupon_code: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    customer_notes: str | None = None


def generate_order_number() -> str:
    """Generate a clean human-readable order number with date prefix (e.g. AZ-20261011-A1B2C3)."""
    date_str = _utcnow().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"AZ-{date_str}-{unique_suffix}"


def place_order(db: Session, order_data: CreateOrderDTO) -> Order:
    """
    Atomically place an order:
    1. Validates and normalizes customer data.
    2. Recalculates authoritative prices from the catalog database.
    3. Resolves active supplier variants for each item.
    4. Validates promotional coupon codes and computes discounts.
    5. Creates immutable Order and OrderLine purchase snapshots.
    6. Holds stock reservations for each item (reverts entire transaction if stock unavailable).
    """
    if not order_data.items:
        raise ValueError("Order must contain at least one item.")

    if order_data.payment_method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError(
            f"Invalid payment method {order_data.payment_method!r}. Must be one of {sorted(ALLOWED_PAYMENT_METHODS)}."
        )

    clean_phone = normalize_pakistan_phone(order_data.customer_phone)

    # 1. Pre-validate all items and resolve catalog & supplier linkages
    line_preparations = []
    subtotal_minor = 0

    for item in order_data.items:
        if item.quantity <= 0:
            raise ValueError(f"Item quantity must be strictly positive, got {item.quantity}")

        variant = db.get(Variant, item.variant_id)
        if variant is None:
            raise ValueError(f"Variant id {item.variant_id} not found in catalog.")

        if not variant.is_active or variant.availability != AvailabilityStatus.AVAILABLE:
            raise ValueError(
                f"Variant SKU {variant.sku!r} is not currently available for purchase."
            )

        active_sv = get_active_supplier_variant(db, variant.id)
        if active_sv is None:
            raise ValueError(
                f"No active supplier configured for variant SKU {variant.sku!r}."
            )

        product = variant.product
        unit_price_minor = variant.price_minor
        unit_cost_minor = active_sv.supplier_cost_minor
        line_total_minor = unit_price_minor * item.quantity
        subtotal_minor += line_total_minor

        line_preparations.append(
            {
                "variant": variant,
                "product": product,
                "active_sv": active_sv,
                "quantity": item.quantity,
                "unit_price_minor": unit_price_minor,
                "unit_cost_minor": unit_cost_minor,
                "line_total_minor": line_total_minor,
            }
        )

    # 2. Validate Coupon and Calculate Discount
    discount_amount_minor = 0
    applied_coupon_code = None

    if order_data.coupon_code:
        coupon_res = validate_coupon(
            db,
            code=order_data.coupon_code,
            subtotal_minor=subtotal_minor,
            shipping_fee_minor=order_data.shipping_fee_minor,
        )
        discount_amount_minor = coupon_res.discount_amount_minor
        applied_coupon_code = coupon_res.code
        record_coupon_usage(db, coupon_res.code)

    total_minor = max(0, subtotal_minor - discount_amount_minor + order_data.shipping_fee_minor)

    # 3. Create Order Header
    order = Order(
        order_number=generate_order_number(),
        customer_name=order_data.customer_name.strip(),
        customer_phone=clean_phone,
        customer_email=order_data.customer_email.strip() if order_data.customer_email else None,
        shipping_address_line1=order_data.shipping_address_line1.strip(),
        shipping_address_line2=order_data.shipping_address_line2.strip() if order_data.shipping_address_line2 else None,
        shipping_city=order_data.shipping_city.strip(),
        shipping_province=order_data.shipping_province.strip(),
        shipping_postal_code=order_data.shipping_postal_code.strip() if order_data.shipping_postal_code else None,
        payment_method=order_data.payment_method,
        payment_status="pending",
        order_status="placed",
        subtotal_minor=subtotal_minor,
        discount_amount_minor=discount_amount_minor,
        coupon_code_snapshot=applied_coupon_code,
        shipping_fee_minor=order_data.shipping_fee_minor,
        total_minor=total_minor,
        utm_source=order_data.utm_source.strip() if order_data.utm_source else None,
        utm_medium=order_data.utm_medium.strip() if order_data.utm_medium else None,
        utm_campaign=order_data.utm_campaign.strip() if order_data.utm_campaign else None,
        customer_notes=order_data.customer_notes.strip() if order_data.customer_notes else None,
    )
    db.add(order)
    db.flush()

    # 3. Create Order Lines & Hold Stock Reservations
    for prep in line_preparations:
        variant = prep["variant"]
        product = prep["product"]
        active_sv = prep["active_sv"]

        order_line = OrderLine(
            order_id=order.id,
            variant_id=variant.id,
            product_title_snapshot=product.title,
            variant_sku_snapshot=variant.sku,
            variant_size_snapshot=variant.size,
            variant_color_snapshot=variant.color,
            unit_price_minor=prep["unit_price_minor"],
            unit_cost_minor=prep["unit_cost_minor"],
            quantity=prep["quantity"],
            line_total_minor=prep["line_total_minor"],
        )
        db.add(order_line)
        db.flush()

        # Hold stock reservation against the supplier variant
        create_stock_reservation(
            db,
            supplier_variant_id=active_sv.id,
            order_line_id=order_line.id,
            quantity=prep["quantity"],
        )

    db.flush()
    return order


def upload_payment_receipt(
    db: Session,
    *,
    order_id: uuid.UUID,
    receipt_image_url: str,
    bank_reference: str | None = None,
) -> PaymentReceipt:
    """Record an uploaded bank payment receipt screenshot for an order."""
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found.")

    receipt = PaymentReceipt(
        order_id=order.id,
        receipt_image_url=receipt_image_url.strip(),
        bank_reference=bank_reference.strip() if bank_reference else None,
    )
    db.add(receipt)
    db.flush()
    return receipt


def verify_bank_payment(
    db: Session,
    *,
    order_id: uuid.UUID,
    verified_by_user_id: uuid.UUID,
    receipt_id: uuid.UUID | None = None,
) -> Order:
    """
    Owner confirms cleared funds in AlphaZee's bank account.
    Marks payment as verified, order as confirmed, and advances reservations to 'confirmed'.
    """
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found.")

    order.payment_status = "verified"
    order.order_status = "confirmed"

    now = _utcnow()
    if receipt_id:
        receipt = db.get(PaymentReceipt, receipt_id)
        if receipt and receipt.order_id == order.id:
            receipt.verified_at = now
            receipt.verified_by_user_id = verified_by_user_id

    # Advance all open reservations for this order's lines
    stmt = (
        select(StockReservation)
        .where(
            StockReservation.order_line_id.in_([line.id for line in order.lines]),
            StockReservation.stage == "held",
        )
    )
    reservations = db.scalars(stmt).all()
    for res in reservations:
        transition_reservation_stage(db, reservation_id=res.id, new_stage="confirmed")

    db.flush()
    return order


def cancel_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    reason: str | None = None,
) -> Order:
    """
    Cancel an order and immediately release all held stock reservations.
    """
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found.")

    if order.order_status in ("delivered", "cancelled"):
        raise ValueError(f"Cannot cancel order in {order.order_status!r} status.")

    order.order_status = "cancelled"

    # Cancel all associated reservations
    stmt = (
        select(StockReservation)
        .where(
            StockReservation.order_line_id.in_([line.id for line in order.lines]),
            StockReservation.stage.in_(["held", "confirmed", "dispatched"]),
        )
    )
    reservations = db.scalars(stmt).all()
    for res in reservations:
        transition_reservation_stage(db, reservation_id=res.id, new_stage="cancelled")

    db.flush()
    return order


def deliver_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    actor_user_id: uuid.UUID | None = None,
) -> Order:
    """
    Mark an order as delivered:
    - Sets order_status = 'delivered'.
    - If COD, marks payment_status = 'verified'.
    - Fulfills all associated reservations (which decrements physical inventory and records StockEvent).
    """
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found.")

    order.order_status = "delivered"
    if order.payment_method == "cod":
        order.payment_status = "verified"

    # Fulfill all open reservations
    stmt = (
        select(StockReservation)
        .where(
            StockReservation.order_line_id.in_([line.id for line in order.lines]),
            StockReservation.stage.in_(["held", "confirmed", "dispatched"]),
        )
    )
    reservations = db.scalars(stmt).all()
    for res in reservations:
        transition_reservation_stage(
            db,
            reservation_id=res.id,
            new_stage="fulfilled",
            actor_user_id=actor_user_id,
            notes=f"Delivery of order {order.order_number}",
        )

    db.flush()
    return order
