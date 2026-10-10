"""
promotions.py — Business logic and validation services for discount vouchers and coupon codes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.promotions import Coupon


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CouponValidationResult:
    valid: bool
    code: str
    discount_type: str
    discount_value: int
    discount_amount_minor: int
    is_free_shipping: bool
    message: str


def validate_coupon(
    db: Session,
    *,
    code: str,
    subtotal_minor: int,
    shipping_fee_minor: int = 0,
) -> CouponValidationResult:
    """
    Validate a coupon against the current cart subtotal and calculate discount in integer paisas.
    
    Raises ValueError on invalid, expired, or non-applicable coupons.
    """
    clean_code = code.strip().upper()
    if not clean_code:
        raise ValueError("Coupon code cannot be empty.")

    stmt = select(Coupon).where(Coupon.code == clean_code)
    coupon = db.scalars(stmt).first()

    if coupon is None:
        raise ValueError(f"Coupon code '{clean_code}' does not exist.")

    if not coupon.is_active:
        raise ValueError(f"Coupon code '{clean_code}' is no longer active.")

    now = _utcnow()
    if coupon.valid_from and now < coupon.valid_from:
        raise ValueError(f"Coupon code '{clean_code}' is not valid yet.")

    if coupon.valid_until and now > coupon.valid_until:
        raise ValueError(f"Coupon code '{clean_code}' has expired.")

    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        raise ValueError(f"Coupon code '{clean_code}' usage limit has been reached.")

    if subtotal_minor < coupon.min_subtotal_minor:
        min_pkr = coupon.min_subtotal_minor // 100
        raise ValueError(
            f"Minimum order subtotal of PKR {min_pkr:,} required to use coupon '{clean_code}'."
        )

    discount_minor = 0
    is_free_shipping = False

    if coupon.discount_type == "percentage":
        calculated = (subtotal_minor * coupon.discount_value) // 100
        if coupon.max_discount_minor is not None and coupon.max_discount_minor > 0:
            calculated = min(calculated, coupon.max_discount_minor)
        discount_minor = min(calculated, subtotal_minor)
    elif coupon.discount_type == "fixed_amount":
        discount_minor = min(coupon.discount_value, subtotal_minor)
    elif coupon.discount_type == "free_shipping":
        is_free_shipping = True
        discount_minor = min(shipping_fee_minor, shipping_fee_minor)
    else:
        raise ValueError(f"Unsupported discount type: {coupon.discount_type}")

    return CouponValidationResult(
        valid=True,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        discount_amount_minor=discount_minor,
        is_free_shipping=is_free_shipping,
        message="Coupon successfully applied.",
    )


def record_coupon_usage(db: Session, code: str) -> None:
    """Increment the usage counter on an applied coupon."""
    clean_code = code.strip().upper()
    stmt = select(Coupon).where(Coupon.code == clean_code)
    coupon = db.scalars(stmt).first()
    if coupon is not None:
        coupon.times_used += 1
        db.flush()


def create_coupon(
    db: Session,
    *,
    code: str,
    discount_type: str,
    discount_value: int,
    min_subtotal_minor: int = 0,
    max_discount_minor: int | None = None,
    usage_limit: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    is_active: bool = True,
) -> Coupon:
    """Create a new promotional coupon."""
    clean_code = code.strip().upper()
    existing = db.scalars(select(Coupon).where(Coupon.code == clean_code)).first()
    if existing is not None:
        raise ValueError(f"Coupon code '{clean_code}' already exists.")

    coupon = Coupon(
        code=clean_code,
        discount_type=discount_type.strip().lower(),
        discount_value=discount_value,
        min_subtotal_minor=min_subtotal_minor,
        max_discount_minor=max_discount_minor,
        usage_limit=usage_limit,
        valid_from=valid_from or _utcnow(),
        valid_until=valid_until,
        is_active=is_active,
    )
    db.add(coupon)
    db.flush()
    return coupon


def list_coupons(
    db: Session,
    *,
    active_only: bool = False,
) -> Sequence[Coupon]:
    """List all coupons for administrative management."""
    stmt = select(Coupon)
    if active_only:
        stmt = stmt.where(Coupon.is_active.is_(True))
    stmt = stmt.order_by(Coupon.created_at.desc())
    return db.scalars(stmt).all()


def delete_coupon(db: Session, coupon_id: uuid.UUID) -> bool:
    """Delete a coupon by ID."""
    coupon = db.get(Coupon, coupon_id)
    if coupon is None:
        return False
    db.delete(coupon)
    db.flush()
    return True
