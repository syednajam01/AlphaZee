"""
promotions.py — Pydantic schemas for discount coupons and promotional campaign endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalog import CurrencyAmount


class CouponValidateRequest(BaseModel):
    """Payload to validate a coupon against current subtotal."""

    code: str = Field(min_length=1, max_length=50, description="Coupon code")
    subtotal_minor: int = Field(ge=0, description="Current cart subtotal in minor units (paisas)")
    shipping_fee_minor: int = Field(default=0, ge=0, description="Current shipping fee in paisas")


class CouponValidateResponse(BaseModel):
    """Result of coupon validation."""

    valid: bool
    code: str
    discount_type: str
    discount_value: int
    discount_amount: CurrencyAmount
    is_free_shipping: bool
    message: str


class CouponCreateRequest(BaseModel):
    """Admin payload to create a new promotional coupon."""

    code: str = Field(min_length=2, max_length=50, description="Coupon code string")
    discount_type: str = Field(description="'percentage', 'fixed_amount', or 'free_shipping'")
    discount_value: int = Field(ge=0, description="Percentage (e.g. 10) or minor paisas (e.g. 50000)")
    min_subtotal_minor: int = Field(default=0, ge=0, description="Minimum order subtotal in minor paisas")
    max_discount_minor: Optional[int] = Field(default=None, ge=0, description="Cap on percentage discounts in minor paisas")
    usage_limit: Optional[int] = Field(default=None, ge=1, description="Total number of times coupon can be redeemed")
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True


class CouponResponseSchema(BaseModel):
    """Coupon representation for owner admin console."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    discount_type: str
    discount_value: int
    min_subtotal: CurrencyAmount
    max_discount: Optional[CurrencyAmount] = None
    usage_limit: Optional[int] = None
    times_used: int
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool
    created_at: datetime
