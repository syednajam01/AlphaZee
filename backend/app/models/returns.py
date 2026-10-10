"""
returns.py — SQLAlchemy ORM models for customer return requests, size exchanges, and bank refund tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
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


ALLOWED_RETURN_TYPES = {"refund_bank_transfer", "size_exchange", "store_credit"}
ALLOWED_RETURN_REASONS = {
    "size_too_small",
    "size_too_large",
    "damaged_defective",
    "not_as_described",
    "changed_mind",
}
ALLOWED_RETURN_STATUSES = {
    "requested",
    "approved",
    "item_received",
    "inspected_passed",
    "completed",
    "rejected",
}


class OrderReturn(Base):
    """
    Customer return request for an order line item.
    """

    __tablename__ = "order_returns"
    __table_args__ = (
        CheckConstraint("refund_amount_minor >= 0", name="ck_order_returns_refund_nonnegative"),
        CheckConstraint(
            f"return_type IN ({', '.join(repr(t) for t in sorted(ALLOWED_RETURN_TYPES))})",
            name="ck_order_returns_type",
        ),
        CheckConstraint(
            f"reason IN ({', '.join(repr(r) for r in sorted(ALLOWED_RETURN_REASONS))})",
            name="ck_order_returns_reason",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in sorted(ALLOWED_RETURN_STATUSES))})",
            name="ck_order_returns_status",
        ),
        Index("idx_order_returns_order_id", "order_id"),
        Index("idx_order_returns_status", "status"),
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

    order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_lines.id", ondelete="CASCADE"),
        nullable=False,
    )

    return_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="refund_bank_transfer",
    )

    reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    customer_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="requested",
        server_default=text("'requested'"),
    )

    exchange_variant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("variants.id", ondelete="SET NULL"),
        nullable=True,
    )

    refund_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    refund_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    restocked_at: Mapped[datetime | None] = mapped_column(
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

    # Relationship to parent Order
    order: Mapped[Order] = relationship(
        "Order",
        back_populates="returns",
    )

    @validates("return_type")
    def validate_type(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_RETURN_TYPES:
            raise ValueError(
                f"Invalid return type {value!r}. Must be one of {sorted(ALLOWED_RETURN_TYPES)}."
            )
        return clean

    @validates("reason")
    def validate_reason(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_RETURN_REASONS:
            raise ValueError(
                f"Invalid return reason {value!r}. Must be one of {sorted(ALLOWED_RETURN_REASONS)}."
            )
        return clean

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_RETURN_STATUSES:
            raise ValueError(
                f"Invalid return status {value!r}. Must be one of {sorted(ALLOWED_RETURN_STATUSES)}."
            )
        return clean
