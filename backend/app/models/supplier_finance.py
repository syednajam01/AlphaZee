"""
supplier_finance.py — SQLAlchemy ORM models for supplier agreements and ledger entries.

Implements immutable, double-entry-style liability and payment records for local suppliers.
Invariants:
- All monetary amounts use integer paisas (PKR minor units).
- Posted entries are immutable; corrections require explicit reversal entries.
- Idempotency is enforced by unique source_event_key where applicable.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PayableTrigger(str, enum.Enum):
    MANUAL = "manual"
    CONFIRMED_PICKUP = "confirmed_pickup"
    DISPATCH = "dispatch"
    DELIVERY = "delivery"


class LedgerEntryType(str, enum.Enum):
    CHARGE = "charge"
    CREDIT_NOTE = "credit_note"
    PAYMENT = "payment"
    ADVANCE = "advance"
    REFUND_RECEIVED = "refund_received"
    OPENING_BALANCE = "opening_balance"
    ADJUSTMENT = "adjustment"


class LedgerDirection(str, enum.Enum):
    CREDIT = "credit"  # Increases liability (owed to vendor)
    DEBIT = "debit"    # Decreases liability (paid to or credited by vendor)


class SupplierAgreement(Base):
    """
    Contractual settlement agreement terms between AlphaZee and an approved supplier.
    Default trigger for unconfigured suppliers is always MANUAL.
    """

    __tablename__ = "supplier_agreements"
    __table_args__ = (
        CheckConstraint(
            "payable_trigger IN ('manual', 'confirmed_pickup', 'dispatch', 'delivery')",
            name="ck_supplier_agreements_trigger",
        ),
        CheckConstraint(
            "payment_terms_days >= 0",
            name="ck_supplier_agreements_terms_nonnegative",
        ),
        Index("idx_supplier_agreements_supplier_id", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )

    payable_trigger: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default=text("'manual'"),
    )

    payment_terms_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    supplier = relationship("Supplier")

    def __repr__(self) -> str:
        return f"<SupplierAgreement id={self.id} supplier_id={self.supplier_id} trigger={self.payable_trigger}>"


class SupplierLedgerEntry(Base):
    """
    Immutable journal entry tracking supplier liabilities, payments, credits, and adjustments.
    """

    __tablename__ = "supplier_ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_supplier_ledger_amount_positive"),
        CheckConstraint(
            "entry_type IN ('charge', 'credit_note', 'payment', 'advance', 'refund_received', 'opening_balance', 'adjustment')",
            name="ck_supplier_ledger_entry_type",
        ),
        CheckConstraint(
            "direction IN ('credit', 'debit')",
            name="ck_supplier_ledger_direction",
        ),
        CheckConstraint(
            "status IN ('posted', 'reversed')",
            name="ck_supplier_ledger_status",
        ),
        Index("idx_supplier_ledger_supplier_id", "supplier_id"),
        Index("idx_supplier_ledger_effective_date", "effective_date"),
        Index("idx_supplier_ledger_order_id", "order_id"),
        Index(
            "uq_supplier_ledger_source_key",
            "source_event_key",
            unique=True,
            postgresql_where=text("source_event_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)

    source_event_key: Mapped[str | None] = mapped_column(String(160), nullable=True)

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    order_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_lines.id", ondelete="SET NULL"),
        nullable=True,
    )

    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="SET NULL"),
        nullable=True,
    )

    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="posted",
        server_default=text("'posted'"),
    )

    reversal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_ledger_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    supplier = relationship("Supplier")
    order = relationship("Order")
    order_line = relationship("OrderLine")
    shipment = relationship("Shipment")
    recorded_by = relationship("UserAccount")
    allocations_as_payment = relationship(
        "SupplierPaymentAllocation",
        foreign_keys="SupplierPaymentAllocation.payment_entry_id",
        back_populates="payment_entry",
    )
    allocations_as_charge = relationship(
        "SupplierPaymentAllocation",
        foreign_keys="SupplierPaymentAllocation.charge_entry_id",
        back_populates="charge_entry",
    )

    def __repr__(self) -> str:
        return f"<SupplierLedgerEntry id={self.id} supplier_id={self.supplier_id} type={self.entry_type} amount={self.amount_minor}>"


class SupplierPaymentAllocation(Base):
    """
    Explicit allocation linking a payment entry to one or more charge entries.
    """

    __tablename__ = "supplier_payment_allocations"
    __table_args__ = (
        CheckConstraint("allocated_amount_minor > 0", name="ck_payment_alloc_amount_positive"),
        Index("idx_payment_alloc_payment_id", "payment_entry_id"),
        Index("idx_payment_alloc_charge_id", "charge_entry_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    payment_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_ledger_entries.id", ondelete="CASCADE"),
        nullable=False,
    )

    charge_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_ledger_entries.id", ondelete="CASCADE"),
        nullable=False,
    )

    allocated_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    payment_entry = relationship(
        "SupplierLedgerEntry",
        foreign_keys=[payment_entry_id],
        back_populates="allocations_as_payment",
    )
    charge_entry = relationship(
        "SupplierLedgerEntry",
        foreign_keys=[charge_entry_id],
        back_populates="allocations_as_charge",
    )

    def __repr__(self) -> str:
        return f"<SupplierPaymentAllocation id={self.id} payment={self.payment_entry_id} charge={self.charge_entry_id} amount={self.allocated_amount_minor}>"
