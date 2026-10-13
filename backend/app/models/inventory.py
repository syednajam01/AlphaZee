"""
inventory.py — SQLAlchemy ORM models for supplier stock balances, linkages, and audit trail.

Schema:
- SupplierVariant: Link between catalog Variant and supplying vendor, with partial unique index.
- InventoryBalance: Physical stock count with optimistic locking version counter.
- StockEvent: Append-only audit log tracking every inventory adjustment.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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


ALLOWED_STOCK_EVENT_REASONS = {
    "manual_count",
    "supplier_receipt",
    "reservation_fulfilled",
    "reservation_cancelled",
    "rto_return",
    "dispatch",
    "customer_return",
    "adjustment_correction",
}


class SupplierVariant(Base):
    """
    Links a catalog product Variant to the Supplier providing it.

    Invariants:
    - At most ONE supplier_variant row per variant_id may have active=True (enforced by uq_sv_one_active_per_variant).
    - supplier_cost_minor must be non-negative.
    """

    __tablename__ = "supplier_variants"
    __table_args__ = (
        CheckConstraint(
            "supplier_cost_minor >= 0",
            name="ck_supplier_variant_cost_nonnegative",
        ),
        Index("idx_sv_supplier_id", "supplier_id"),
        Index("idx_sv_variant_id", "variant_id"),
        Index(
            "uq_sv_one_active_per_variant",
            "variant_id",
            unique=True,
            postgresql_where=text("active = true"),
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

    variant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    supplier_cost_minor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    """Agreed wholesale cost in PKR minor units (paisas)."""

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
    supplier = relationship("Supplier", back_populates="variants")
    variant = relationship("Variant")
    balance: Mapped[InventoryBalance | None] = relationship(
        "InventoryBalance",
        back_populates="supplier_variant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stock_events: Mapped[list[StockEvent]] = relationship(
        "StockEvent",
        back_populates="supplier_variant",
    )
    reservations: Mapped[list[StockReservation]] = relationship(
        "StockReservation",
        back_populates="supplier_variant",
    )

    def __repr__(self) -> str:
        return f"<SupplierVariant id={self.id} supplier_id={self.supplier_id} variant_id={self.variant_id} active={self.active}>"


class InventoryBalance(Base):
    """
    Physical stock on-hand maintained by the owner, protected by an optimistic concurrency counter.
    """

    __tablename__ = "inventory_balances"
    __table_args__ = (
        CheckConstraint("on_hand >= 0", name="ck_inventory_on_hand_nonnegative"),
    )

    supplier_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_variants.id", ondelete="CASCADE"),
        primary_key=True,
    )

    on_hand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    last_counted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    supplier_variant: Mapped[SupplierVariant] = relationship(
        "SupplierVariant",
        back_populates="balance",
    )

    def __repr__(self) -> str:
        return f"<InventoryBalance supplier_variant_id={self.supplier_variant_id} on_hand={self.on_hand} version={self.version}>"


class StockEvent(Base):
    """
    Immutable append-only audit event for inventory adjustments.
    """

    __tablename__ = "stock_events"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('manual_count', 'supplier_receipt', 'reservation_fulfilled', 'reservation_cancelled', 'rto_return', 'adjustment_correction', 'dispatch', 'customer_return')",
            name="ck_stock_events_reason",
        ),
        Index("idx_se_sv_occurred", "supplier_variant_id", "occurred_at"),
        Index("idx_se_actor", "actor_user_id"),
        Index("uq_stock_events_source_ref", "source_ref", unique=True,
              postgresql_where=text("source_ref IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    supplier_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    previous_on_hand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    new_on_hand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    delta: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    supplier_variant: Mapped[SupplierVariant] = relationship(
        "SupplierVariant",
        back_populates="stock_events",
    )
    actor_user = relationship("UserAccount")

    @validates("reason")
    def validate_reason(self, key: str, value: str) -> str:
        if value not in ALLOWED_STOCK_EVENT_REASONS:
            raise ValueError(
                f"Invalid stock event reason {value!r}. Must be one of {sorted(ALLOWED_STOCK_EVENT_REASONS)}."
            )
        return value

    def __repr__(self) -> str:
        return (
            f"<StockEvent id={self.id} sv_id={self.supplier_variant_id} "
            f"delta={self.delta} reason={self.reason!r}>"
        )


ALLOWED_RESERVATION_STAGES = {
    "held",
    "confirmed",
    "dispatched",
    "fulfilled",
    "cancelled",
    "returned",
}

OPEN_RESERVATION_STAGES = {"held", "confirmed"}
TERMINAL_RESERVATION_STAGES = {"fulfilled", "cancelled", "returned"}


class StockReservation(Base):
    """
    Tracks inventory units held for orders prior to dispatch/fulfillment or cancellation.
    """

    __tablename__ = "stock_reservations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_reservations_quantity_positive"),
        CheckConstraint(
            "stage IN ('held', 'confirmed', 'dispatched', 'fulfilled', 'cancelled', 'returned')",
            name="ck_stock_reservations_stage",
        ),
        Index("idx_sr_supplier_variant_id", "supplier_variant_id"),
        Index("idx_sr_order_line_id", "order_line_id"),
        Index(
            "idx_sr_open_stage",
            "supplier_variant_id",
            "quantity",
            postgresql_where=text("stage IN ('held', 'confirmed') OR legacy_stock_hold = true"),
        ),
        Index(
            "uq_sr_idempotency_open",
            "idempotency_key",
            unique=True,
            postgresql_where=text("stage NOT IN ('cancelled', 'returned') AND idempotency_key IS NOT NULL"),
        ),
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
    """Client/service idempotency key guarding against duplicate holds."""

    supplier_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    """External UUID identifier for the order line item."""

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="held",
        server_default=text("'held'"),
    )

    legacy_stock_hold: Mapped[bool] = mapped_column(Boolean, nullable=False,
        default=False, server_default=text('false'))

    supplier_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    instructions_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payment_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    """Wholesale supplier payment deadline (distinct from customer bank verification)."""

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    supplier_variant = relationship(
        "SupplierVariant",
        back_populates="reservations",
    )

    @validates("stage")
    def validate_stage(self, key: str, value: str) -> str:
        if value not in ALLOWED_RESERVATION_STAGES:
            raise ValueError(
                f"Invalid reservation stage {value!r}. Must be one of {sorted(ALLOWED_RESERVATION_STAGES)}."
            )
        return value

    @validates("quantity")
    def validate_quantity(self, key: str, value: int) -> int:
        if value <= 0:
            raise ValueError(f"Reservation quantity must be strictly positive, got {value}.")
        return value

    def __repr__(self) -> str:
        return (
            f"<StockReservation id={self.id} sv_id={self.supplier_variant_id} "
            f"order_line={self.order_line_id} qty={self.quantity} stage={self.stage!r}>"
        )

