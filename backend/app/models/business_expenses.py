"""
business_expenses.py — SQLAlchemy ORM model for categorized operating expenses, logistics overhead, and courier deduction links.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_EXPENSE_CATEGORIES = {
    "packaging",
    "advertising",
    "outbound_delivery",
    "rto_transport",
    "customer_return_transport",
    "platform_hosting",
    "office_supplies",
    "salaries",
    "other_overhead",
}

ALLOWED_EXPENSE_PAYMENT_METHODS = {
    "cash",
    "bank_transfer",
    "courier_deduction",
    "credit_card",
    "other",
}


class BusinessExpense(Base):
    """
    Categorized business expense entry.
    AlphaZee strictly bears outbound delivery, RTO transport, and customer return transport costs.
    Links to courier settlement entries to eliminate double-counting.
    """

    __tablename__ = "business_expenses"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_business_expenses_amount_positive"),
        CheckConstraint(
            f"category IN ({', '.join(repr(c) for c in sorted(ALLOWED_EXPENSE_CATEGORIES))})",
            name="ck_business_expenses_category",
        ),
        CheckConstraint(
            f"payment_method IN ({', '.join(repr(m) for m in sorted(ALLOWED_EXPENSE_PAYMENT_METHODS))})",
            name="ck_business_expenses_payment_method",
        ),
        Index("ix_business_expenses_category", "category"),
        Index("ix_business_expenses_incurred_date", "incurred_date"),
        Index("ix_business_expenses_shipment", "linked_shipment_id"),
        Index("ix_business_expenses_return", "linked_return_id"),
        Index("ix_business_expenses_settlement", "linked_courier_settlement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    """Amount in integer PKR paisas (minor units)."""

    incurred_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    paid_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    """Null if expense is accrued/unpaid."""

    payee: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="bank_transfer",
        server_default=text("'bank_transfer'"),
    )

    linked_shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="SET NULL"),
        nullable=True,
    )

    linked_return_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_returns.id", ondelete="SET NULL"),
        nullable=True,
    )

    linked_courier_settlement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courier_settlement_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
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
    shipment = relationship("Shipment", foreign_keys=[linked_shipment_id])
    order_return = relationship("OrderReturn", foreign_keys=[linked_return_id])
    courier_settlement = relationship("CourierSettlementEntry", foreign_keys=[linked_courier_settlement_id])
    recorded_by = relationship("UserAccount", foreign_keys=[recorded_by_user_id])

    @validates("category")
    def validate_category(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_EXPENSE_CATEGORIES:
            raise ValueError(f"Invalid category {value!r}. Must be one of {sorted(ALLOWED_EXPENSE_CATEGORIES)}")
        return clean

    @validates("payment_method")
    def validate_payment_method(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_EXPENSE_PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method {value!r}. Must be one of {sorted(ALLOWED_EXPENSE_PAYMENT_METHODS)}")
        return clean

    @validates("amount_minor")
    def validate_amount(self, key: str, value: int) -> int:
        if value <= 0:
            raise ValueError(f"Expense amount must be strictly positive, got {value}")
        return value

    def __repr__(self) -> str:
        return f"<BusinessExpense id={self.id} category={self.category!r} amount={self.amount_minor} payee={self.payee!r}>"
