"""
promotions.py — SQLAlchemy ORM models for promotional coupons, percentage discounts, and min-spend rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_DISCOUNT_TYPES = {"percentage", "fixed_amount", "free_shipping"}


class Coupon(Base):
    """
    Promotional discount voucher.
    
    Supports:
    - percentage (e.g. 10 for 10% off)
    - fixed_amount (e.g. 50000 paisas = PKR 500 off)
    - free_shipping (100% waiver on courier shipping charge)
    """

    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("discount_value >= 0", name="ck_coupons_discount_value_nonnegative"),
        CheckConstraint("min_subtotal_minor >= 0", name="ck_coupons_min_subtotal_nonnegative"),
        CheckConstraint(
            f"discount_type IN ({', '.join(repr(t) for t in sorted(ALLOWED_DISCOUNT_TYPES))})",
            name="ck_coupons_discount_type",
        ),
        Index("idx_coupons_code", "code", unique=True),
        Index("idx_coupons_active", "is_active", "valid_from", "valid_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    discount_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="percentage",
    )

    discount_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    min_subtotal_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    max_discount_minor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    usage_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    times_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        clean = value.strip().upper()
        if not clean:
            raise ValueError("Coupon code cannot be empty.")
        return clean

    @validates("discount_type")
    def validate_type(self, key: str, value: str) -> str:
        clean = value.strip().lower()
        if clean not in ALLOWED_DISCOUNT_TYPES:
            raise ValueError(
                f"Invalid discount type {value!r}. Must be one of {sorted(ALLOWED_DISCOUNT_TYPES)}."
            )
        return clean
