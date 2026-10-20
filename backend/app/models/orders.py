"""
orders.py — SQLAlchemy ORM models for customer orders, immutable purchase snapshots, and bank payment receipts.

Schema:
- Order: Customer order header, address details, totals, and statuses.
- OrderLine: Line items containing immutable purchase-time snapshots of title, SKU, options, customer price, and supplier cost.
- PaymentReceipt: Uploaded bank transfer payment proofs pending owner verification.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.shipments import Shipment
    from app.models.returns import OrderReturn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_PAYMENT_METHODS = {"cod", "bank_transfer"}
ALLOWED_PAYMENT_STATUSES = {"pending", "verified", "failed", "refunded"}
ALLOWED_ORDER_STATUSES = {
    "placed",
    "confirmed",
    "dispatched",
    "delivered",
    "cancelled",
    "rto",
}


def normalize_pakistan_phone(phone_input: str) -> str:
    """
    Validate and normalize a Pakistani mobile phone number to canonical 03XXXXXXXXX format.
    Accepts: '03001234567', '+923001234567', '0300-1234567', '0300 1234567', '923001234567'.
    """
    cleaned = re.sub(r"[\s\-\(\)]", "", phone_input.strip())
    if cleaned.startswith("+92"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("92") and len(cleaned) == 12:
        cleaned = "0" + cleaned[2:]

    if not re.match(r"^03\d{9}$", cleaned):
        raise ValueError(
            f"Invalid Pakistani mobile phone number: {phone_input!r}. Must be a valid 11-digit mobile number (e.g. 03001234567)."
        )
    return cleaned


class Order(Base):
    """
    Customer order entity.
    """

    __tablename__ = "orders"
    shipping_rule_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supplier_picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("subtotal_minor >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("shipping_fee_minor >= 0", name="ck_orders_shipping_fee_nonnegative"),
        CheckConstraint("discount_amount_minor >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("total_minor >= 0", name="ck_orders_total_nonnegative"),
        CheckConstraint(
            "payment_method IN ('cod', 'bank_transfer')",
            name="ck_orders_payment_method",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'verified', 'failed', 'refunded')",
            name="ck_orders_payment_status",
        ),
        CheckConstraint(
            "order_status IN ('placed', 'confirmed', 'dispatched', 'delivered', 'cancelled', 'rto')",
            name="ck_orders_order_status",
        ),
        CheckConstraint(
            "payment_review_status IN ('none', 'required', 'resolved_paid', 'released_unpaid')",
            name='ck_orders_payment_review_status',
        ),
        Index("idx_orders_customer_phone", "customer_phone"),
        Index("idx_orders_status", "order_status", "payment_status"),
        Index("idx_orders_placed_at", "placed_at"),
        Index(
            "uq_orders_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("idx_orders_payment_deadline", "payment_deadline_at"),
        Index("idx_orders_payment_review_status", "payment_review_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    """Client submission key preventing duplicate order creations."""

    checkout_session_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    """Human-readable order identifier (e.g. AZ-2026-1001)."""

    customer_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    customer_phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    shipping_address_line1: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    shipping_address_line2: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    shipping_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    shipping_province: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    shipping_postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    order_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="placed",
        server_default=text("'placed'"),
    )

    subtotal_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    discount_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    coupon_code_snapshot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    shipping_fee_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    total_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Marketing Attribution
    utm_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    utm_medium: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    utm_campaign: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    customer_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    payment_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """Four-hour deadline for bank transfer customers to submit payment proof."""

    payment_instructions_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_instructions_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_instructions_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payment_instructions_sent_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True)
    payment_bank_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_account_title_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_account_number_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_iban_snapshot: Mapped[str | None] = mapped_column(String(34), nullable=True)
    payment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True)
    payment_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default='none',
                                                       server_default=text("'none'"))
    payment_review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True)
    payment_review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """Timestamp when supplier confirmed order stock and acceptance for fulfillment."""

    supplier_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    """Operational notes from owner/supplier regarding order fulfillment."""

    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    lines: Mapped[list[OrderLine]] = relationship(
        "OrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    receipts: Mapped[list[PaymentReceipt]] = relationship(
        "PaymentReceipt",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    shipments: Mapped[list[Shipment]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    returns: Mapped[list[OrderReturn]] = relationship(
        "OrderReturn",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    @validates("customer_phone")
    def validate_phone(self, key: str, value: str) -> str:
        return normalize_pakistan_phone(value)

    @validates("payment_method")
    def validate_payment_method(self, key: str, value: str) -> str:
        if value not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method {value!r}. Must be one of {sorted(ALLOWED_PAYMENT_METHODS)}."
            )
        return value

    @validates("payment_status")
    def validate_payment_status(self, key: str, value: str) -> str:
        if value not in ALLOWED_PAYMENT_STATUSES:
            raise ValueError(
                f"Invalid payment status {value!r}. Must be one of {sorted(ALLOWED_PAYMENT_STATUSES)}."
            )
        return value

    @validates("order_status")
    def validate_order_status(self, key: str, value: str) -> str:
        if value not in ALLOWED_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status {value!r}. Must be one of {sorted(ALLOWED_ORDER_STATUSES)}."
            )
        return value

    def __repr__(self) -> str:
        return f"<Order id={self.id} number={self.order_number!r} total={self.total_minor}>"


class OrderLine(Base):
    """
    Immutable purchase snapshot for each item in an order.
    """

    __tablename__ = "order_lines"
    __table_args__ = (
        CheckConstraint("unit_price_minor >= 0", name="ck_order_lines_unit_price_nonnegative"),
        CheckConstraint(
            "unit_cost_minor IS NULL OR unit_cost_minor >= 0",
            name="ck_order_lines_unit_cost_nonnegative",
        ),
        CheckConstraint("quantity > 0", name="ck_order_lines_quantity_positive"),
        CheckConstraint("line_total_minor >= 0", name="ck_order_lines_line_total_nonnegative"),
        Index("idx_ol_order_id", "order_id"),
        Index("idx_ol_variant_id", "variant_id"),
        CheckConstraint("fulfillment_kind IN ('original', 'replacement')", name='ck_order_lines_fulfillment_kind'),
        CheckConstraint("(fulfillment_kind = 'original' AND replacement_return_id IS NULL) OR "
                        "(fulfillment_kind = 'replacement' AND replacement_return_id IS NOT NULL)",
                        name='ck_order_lines_replacement_link'),
        CheckConstraint("ownership_source IN ('vendor_consignment', 'alphazee_owned')", name='ck_order_lines_ownership_source'),
        Index('uq_order_lines_replacement_return', 'replacement_return_id', unique=True,
              postgresql_where=text('replacement_return_id IS NOT NULL')),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    fulfillment_kind: Mapped[str] = mapped_column(String(20), nullable=False, default='original',
                                                   server_default=text("'original'"))
    ownership_source: Mapped[str] = mapped_column(String(32), nullable=False, default='vendor_consignment',
                                                   server_default=text("'vendor_consignment'"))
    acquisition_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    acquisition_cost_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    replacement_return_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('order_returns.id', ondelete='RESTRICT',
                                     use_alter=True, name='fk_order_lines_replacement_return'), nullable=True)

    variant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    product_title_snapshot: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    variant_sku_snapshot: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    variant_size_snapshot: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    variant_color_snapshot: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    unit_price_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    """Agreed customer purchase price per unit in minor units (paisas)."""

    unit_cost_minor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    """Wholesale supplier cost snapshot per unit in minor units (paisas)."""

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    line_total_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    """unit_price_minor * quantity."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="lines")
    variant = relationship("Variant")

    @validates("quantity")
    def validate_quantity(self, key: str, value: int) -> int:
        if value <= 0:
            raise ValueError(f"Line item quantity must be strictly positive, got {value}")
        return value

    def __repr__(self) -> str:
        return f"<OrderLine id={self.id} order_id={self.order_id} sku={self.variant_sku_snapshot!r} qty={self.quantity}>"


class PaymentReceipt(Base):
    """
    Bank transfer payment proof uploaded by the customer.
    """

    __tablename__ = "payment_receipts"
    __table_args__ = (
        Index("idx_pr_order_id", "order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    receipt_image_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    bank_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="receipts")
    verified_by_user = relationship("UserAccount")

    def __repr__(self) -> str:
        return f"<PaymentReceipt id={self.id} order_id={self.order_id} verified={self.verified_at is not None}>"
