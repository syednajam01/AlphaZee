"""
orders.py — Service layer for order placement, snapshotting, stock reservation coordination, and payment verification.

Coordinates:
- Authoritative backend pricing & snapshotting (title, SKU, options, retail price, wholesale cost).
- Atomic stock reservation holds on order placement (rolling back on insufficient stock).
- Bank transfer receipt verification.
- Order cancellation (immediate release of held stock).
- Order delivery / fulfillment after the dispatch stock movement.
"""

from __future__ import annotations

import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select, text
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
from app.models.inventory import InventoryBalance
from app.models.promotions import Coupon
from app.services.checkout_attempts import fingerprint_order
from app.config import settings
from app.queries.inventory import get_active_supplier_variant
from app.queries.reservations import (
    InsufficientStockError,
    create_stock_reservation,
    transition_reservation_stage,
)


from app.services.promotions import record_coupon_usage, validate_coupon


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _locked_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update()
                      .execution_options(populate_existing=True))
    if order is None:
        raise ValueError(f'Order {order_id} not found.')
    return order


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
    idempotency_key: str | None = None
    checkout_session_hash: str | None = None


class CheckoutAttemptConflict(ValueError):
    """A key belongs to another checkout session or another request body."""


def generate_order_number() -> str:
    """Generate a clean human-readable order number with date prefix (e.g. AZ-20261011-A1B2C3)."""
    date_str = _utcnow().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"AZ-{date_str}-{unique_suffix}"


def place_order(db: Session, order_data: CreateOrderDTO) -> Order:
    """
    Atomically place an order:
    1. Checks idempotency_key to prevent duplicate order submissions.
    2. Validates and normalizes customer data.
    3. Recalculates authoritative prices from the catalog database.
    4. Resolves active supplier variants for each item.
    5. Validates promotional coupon codes and computes discounts.
    6. Creates immutable Order and OrderLine purchase snapshots.
    7. Holds stock reservations for each item with row-level locking (reverts if stock unavailable).
    """
    clean_idemp = (
        order_data.idempotency_key.strip()
        if order_data.idempotency_key and order_data.idempotency_key.strip()
        else None
    )

    fingerprint = fingerprint_order(order_data) if clean_idemp else None
    if clean_idemp:
        # Transaction-scoped across every API worker. The second request waits
        # until the first commits, then reads the authoritative order row.
        lock_id = int.from_bytes(hashlib.sha256(clean_idemp.encode()).digest()[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_id})
        existing_order = db.scalars(
            select(Order).where(Order.idempotency_key == clean_idemp)
        ).first()
        if existing_order is not None:
            if (not order_data.checkout_session_hash or
                    existing_order.checkout_session_hash != order_data.checkout_session_hash or
                    existing_order.request_fingerprint != fingerprint):
                raise CheckoutAttemptConflict('Checkout attempt conflicts with an existing submission.')
            return existing_order
    if not order_data.items:
        raise ValueError("Order must contain at least one item.")

    if order_data.payment_method not in settings.permitted_payment_methods:
        raise ValueError(
            'Bank transfer is unavailable until valid bank account details are configured.'
            if order_data.payment_method == 'bank_transfer' else
            f"Invalid payment method {order_data.payment_method!r}."
        )

    clean_phone = normalize_pakistan_phone(order_data.customer_phone)

    # 1. Pre-validate all items and resolve catalog & supplier linkages
    line_preparations = []
    subtotal_minor = 0

    quantities = {}
    for item in order_data.items:
        quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity

    for variant_id, quantity in sorted(quantities.items()):
        if quantity <= 0:
            raise ValueError(f"Item quantity must be strictly positive, got {quantity}")

        variant = db.get(Variant, variant_id)
        if variant is None:
            raise ValueError(f"Variant id {variant_id} not found in catalog.")

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
        line_total_minor = unit_price_minor * quantity
        subtotal_minor += line_total_minor

        line_preparations.append(
            {
                "variant": variant,
                "product": product,
                "active_sv": active_sv,
                "quantity": quantity,
                "unit_price_minor": unit_price_minor,
                "unit_cost_minor": unit_cost_minor,
                "line_total_minor": line_total_minor,
            }
        )

    # 2. Validate Coupon and Calculate Discount
    discount_amount_minor = 0
    applied_coupon_code = None

    if order_data.coupon_code:
        db.scalars(select(Coupon).where(Coupon.code == order_data.coupon_code.strip().upper()).with_for_update()).first()
        coupon_res = validate_coupon(
            db,
            code=order_data.coupon_code,
            subtotal_minor=subtotal_minor,
            shipping_fee_minor=order_data.shipping_fee_minor,
        )
        discount_amount_minor = coupon_res.discount_amount_minor
        applied_coupon_code = coupon_res.code
        record_coupon_usage(db, coupon_res.code)

    # Lock every shared balance in a stable order before creating any line or
    # reservation. Adjustments take the same balance lock and recheck holds.
    for supplier_variant_id in sorted({p['active_sv'].id for p in line_preparations}):
        balance = db.scalar(select(InventoryBalance).where(
            InventoryBalance.supplier_variant_id == supplier_variant_id).with_for_update())
        if balance is None:
            raise InsufficientStockError(f'No physical stock for supplier variant {supplier_variant_id}.')

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
        payment_deadline_at=None,
        idempotency_key=clean_idemp,
        checkout_session_hash=order_data.checkout_session_hash,
        request_fingerprint=fingerprint,
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

        line_idemp = f"{clean_idemp}:{variant.id}" if clean_idemp else None

        # Hold stock reservation against the supplier variant
        create_stock_reservation(
            db,
            supplier_variant_id=active_sv.id,
            order_line_id=order_line.id,
            quantity=prep["quantity"],
            idempotency_key=line_idemp,
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
    order = _locked_order(db, order_id)
    if (order.payment_method != 'bank_transfer' or order.payment_status != 'pending'
            or order.payment_instructions_sent_at is None
            or order.order_status in ('cancelled', 'delivered', 'rto')):
        raise ValueError('Payment proof can be submitted only after bank instructions are sent for an active order.')
    if order.payment_deadline_at and order.payment_deadline_at < _utcnow() and order.payment_review_status == 'none':
        order.payment_review_status = 'required'
        order.payment_review_started_at = _utcnow()

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
    allow_review: bool = False,
) -> Order:
    """
    Owner confirms cleared funds in AlphaZee's bank account.
    Marks payment as verified only. Does NOT mark supplier confirmed or advance reservations.
    """
    order = _locked_order(db, order_id)
    if order.payment_method != 'bank_transfer' or order.order_status in ('cancelled', 'delivered', 'rto'):
        raise ValueError('Bank payment can only be verified for an active bank transfer order.')
    if not allow_review and (order.payment_review_status == 'required' or
                             (order.payment_deadline_at and order.payment_deadline_at <= _utcnow())):
        raise ValueError('Resolve the expired payment review before verifying funds.')
    if order.payment_status == 'verified':
        return order
    if order.payment_status != 'pending':
        raise ValueError(f'Cannot verify payment in status {order.payment_status!r}.')

    now = _utcnow()
    if receipt_id:
        receipt = db.get(PaymentReceipt, receipt_id)
        if receipt is None or receipt.order_id != order.id:
            raise ValueError('Receipt does not belong to this order.')
        receipt.verified_at = now
        receipt.verified_by_user_id = verified_by_user_id

    order.payment_status = 'verified'
    order.payment_verified_at = now
    order.payment_verified_by_user_id = verified_by_user_id

    db.flush()
    return order


def confirm_supplier_acceptance(
    db: Session,
    *,
    order_id: uuid.UUID,
    supplier_notes: str | None = None,
) -> Order:
    """
    Confirm operational supplier acceptance and readiness to fulfill.
    Advances order_status to 'confirmed' and all open reservations to 'confirmed'.
    """
    order = _locked_order(db, order_id)

    if order.order_status != "placed":
        raise ValueError(f"Cannot confirm supplier acceptance for order in status '{order.order_status}'.")

    now = _utcnow()
    order.order_status = "confirmed"
    order.supplier_confirmed_at = now
    if supplier_notes:
        order.supplier_notes = supplier_notes.strip()

    # Every purchased quantity must still have a real held allocation.
    stmt = (
        select(StockReservation)
        .where(
            StockReservation.order_line_id.in_([line.id for line in order.lines if line.fulfillment_kind == 'original']),
        )
        .order_by(StockReservation.id)
        .with_for_update()
    )
    reservations = db.scalars(stmt).all()
    original_lines = [line for line in order.lines if line.fulfillment_kind == 'original']
    if not original_lines or any(sum(r.quantity for r in reservations if r.order_line_id == line.id
                                  and r.stage == 'held') != line.quantity for line in original_lines):
        raise ValueError('Supplier acceptance requires complete held allocations for every order line.')
    for res in reservations:
        if res.stage != 'held':
            continue
        transition_reservation_stage(db, reservation_id=res.id, new_stage="confirmed")

    db.flush()
    return order


def preview_bank_instructions(db: Session, order_id: uuid.UUID) -> dict:
    order = db.get(Order, order_id)
    if order is None or order.payment_method != 'bank_transfer':
        raise ValueError('Bank transfer order not found.')
    if order.order_status != 'confirmed' or not order.supplier_confirmed_at:
        raise ValueError('Confirm all supplier allocations before preparing payment instructions.')
    if order.payment_instructions_sent_at:
        return {'order_number': order.order_number, 'total_minor': order.total_minor,
                'bank_name': order.payment_bank_name_snapshot, 'account_title': order.payment_account_title_snapshot,
                'account_number': order.payment_account_number_snapshot, 'iban': order.payment_iban_snapshot,
                'already_sent_at': order.payment_instructions_sent_at}
    if not settings.bank_transfer_enabled:
        raise ValueError('Bank transfer account is not configured.')
    return {'order_number': order.order_number, 'total_minor': order.total_minor,
            'bank_name': settings.bank_name.strip(), 'account_title': settings.bank_account_title.strip(),
            'account_number': settings.bank_account_number.strip(), 'iban': settings.bank_iban.replace(' ', '').upper(),
            'already_sent_at': order.payment_instructions_sent_at}


def record_payment_instructions_sent(db: Session, *, order_id: uuid.UUID, actor_user_id: uuid.UUID,
                                     channel: str, reference: str) -> Order:
    """Record an owner's explicit confirmation of an external successful handoff."""
    order = _locked_order(db, order_id)
    if order.payment_method != 'bank_transfer' or order.order_status != 'confirmed' or not order.supplier_confirmed_at:
        raise ValueError('Confirm the supplier before sending bank instructions.')
    if order.payment_instructions_sent_at:
        return order  # Never extend the original payment deadline on retries/resends.
    if order.payment_status != 'pending' or order.payment_review_status != 'none':
        raise ValueError('Payment instructions cannot be sent in the current payment state.')
    if not settings.bank_transfer_enabled:
        raise ValueError('Bank transfer account is not configured.')
    clean_channel = channel.strip().lower()
    clean_reference = reference.strip()
    if clean_channel not in {'whatsapp', 'sms', 'email', 'phone', 'other'} or len(clean_reference) < 3:
        raise ValueError('Record a supported handoff channel and reference.')
    # Recheck the allocation before inviting payment.
    reservations = db.scalars(select(StockReservation).where(
        StockReservation.order_line_id.in_([line.id for line in order.lines if line.fulfillment_kind == 'original']),
        StockReservation.stage == 'confirmed').with_for_update()).all()
    original_lines = [line for line in order.lines if line.fulfillment_kind == 'original']
    if not original_lines or any(sum(r.quantity for r in reservations if r.order_line_id == line.id)
                                  != line.quantity for line in original_lines):
        raise ValueError('All order quantities must be supplier confirmed before payment instructions.')
    now = _utcnow()
    order.payment_instructions_sent_at = now
    order.payment_deadline_at = now + timedelta(hours=4)
    order.payment_instructions_channel = clean_channel
    order.payment_instructions_reference = clean_reference
    order.payment_instructions_sent_by_user_id = actor_user_id
    order.payment_bank_name_snapshot = settings.bank_name.strip()
    order.payment_account_title_snapshot = settings.bank_account_title.strip()
    order.payment_account_number_snapshot = settings.bank_account_number.strip()
    order.payment_iban_snapshot = settings.bank_iban.replace(' ', '').upper()
    db.flush()
    return order


def mark_expired_bank_orders_for_review(db: Session) -> list[Order]:
    """Flag expired unpaid transfers; keep their physical stock and holds intact."""
    now = _utcnow()
    stmt = (
        select(Order)
        .where(
            Order.order_status == "confirmed",
            Order.payment_method == "bank_transfer",
            Order.payment_status == "pending",
            Order.payment_instructions_sent_at.is_not(None),
            Order.payment_deadline_at.is_not(None),
            Order.payment_deadline_at <= now,
            Order.payment_review_status == 'none',
        )
        .order_by(Order.id)
        .with_for_update(skip_locked=True)
    )
    expired_orders = db.scalars(stmt).all()
    for order in expired_orders:
        order.payment_review_status = 'required'
        order.payment_review_started_at = now
    db.flush()
    return expired_orders


def resolve_payment_review(db: Session, *, order_id: uuid.UUID, actor_user_id: uuid.UUID,
                           resolution: str, note: str, funds_checked: bool) -> Order:
    order = _locked_order(db, order_id)
    if (order.payment_method != 'bank_transfer' or order.payment_review_status != 'required'
            or order.order_status != 'confirmed' or not funds_checked or len(note.strip()) < 5):
        raise ValueError('Review requires an expired active bank order, confirmed funds check, and a note.')
    if resolution not in {'payment_received', 'release_unpaid'}:
        raise ValueError('Choose payment_received or release_unpaid.')
    if resolution == 'payment_received':
        verify_bank_payment(db, order_id=order.id, verified_by_user_id=actor_user_id, allow_review=True)
        order.payment_review_status = 'resolved_paid'
    else:
        if order.payment_status != 'pending':
            raise ValueError('Stock cannot be released for an order with verified payment.')
        cancel_order(db, order_id=order.id, review_release=True)
        order.payment_review_status = 'released_unpaid'
    order.payment_reviewed_at = _utcnow()
    order.payment_reviewed_by_user_id = actor_user_id
    order.payment_review_note = note.strip()
    db.flush()
    return order


class OrderNotCancellableError(ValueError):
    """Raised when attempting to cancel an order in a non-cancellable state (e.g. dispatched/in-transit)."""


def cancel_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    reason: str | None = None,
    review_release: bool = False,
) -> Order:
    """
    Cancel an order and immediately release all held stock reservations.
    Refuses cancellation if order is already dispatched (must go through RTO flow).
    """
    order = _locked_order(db, order_id)
    if order.payment_method == 'bank_transfer':
        if order.payment_status == 'verified':
            raise OrderNotCancellableError('Verified bank payments require the refund workflow before stock release.')
        review_due = bool(order.payment_deadline_at and order.payment_deadline_at <= _utcnow())
        if (order.payment_review_status == 'required' or review_due) and not review_release:
            raise OrderNotCancellableError('Expired bank transfers require explicit payment review before releasing stock.')
        if review_release and order.payment_review_status != 'required':
            raise OrderNotCancellableError('Review release requires a pending payment review.')

    if order.order_status == "dispatched":
        raise OrderNotCancellableError(
            f"Cannot cancel order {order.order_number} in 'dispatched' status. "
            f"Parcel is in transit with courier; initiate RTO instead."
        )

    if order.order_status in ("delivered", "cancelled"):
        raise ValueError(f"Cannot cancel order in {order.order_status!r} status.")

    order.order_status = "cancelled"

    # Cancel all associated reservations
    stmt = (
        select(StockReservation)
        .where(
            StockReservation.order_line_id.in_([line.id for line in order.lines if line.fulfillment_kind == 'original']),
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
    """Deliver an existing allocated shipment without changing physical stock."""
    order = _locked_order(db, order_id)
    from app.models.shipments import Shipment
    from app.services.shipments import update_shipment_status
    shipment = db.scalar(select(Shipment).where(Shipment.order_id == order.id,
        Shipment.replacement_return_id.is_(None),
        Shipment.status.in_(['dispatched', 'in_transit', 'out_for_delivery']))
        .order_by(Shipment.created_at.desc()))
    if shipment is None:
        raise ValueError('Delivery requires a previously dispatched shipment with exact allocations.')
    update_shipment_status(db, shipment_id=shipment.id, status='delivered',
                           actor_user_id=actor_user_id)
    return order

