"""
returns.py — Pydantic schemas for order returns, size exchanges, and refund tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalog import CurrencyAmount


class OrderReturnCreateRequest(BaseModel):
    """Customer payload to submit a return or size exchange request."""

    order_id: uuid.UUID = Field(description="Order ID")
    order_line_id: uuid.UUID = Field(description="Purchased line item ID to return")
    customer_phone: Optional[str] = Field(default=None, description="Customer phone number for ownership verification")
    phone: Optional[str] = Field(default=None, description="Alias for customer_phone")
    return_type: str = Field(description="'refund_bank_transfer', 'size_exchange', or 'store_credit'")
    reason: str = Field(description="'size_too_small', 'size_too_large', 'damaged_defective', 'not_as_described', or 'changed_mind'")
    customer_notes: Optional[str] = Field(default=None, max_length=1000, description="Customer explanation")
    exchange_variant_id: Optional[int] = Field(default=None, ge=1, description="Desired variant ID for size exchanges")


class OrderReturnApproveRequest(BaseModel):
    """Admin payload to approve a return request."""

    refund_amount_minor: Optional[int] = Field(default=None, ge=0, description="Overridden refund amount in paisas")


class OrderReturnCompleteRequest(BaseModel):
    """Admin payload to finalize a return and optionally restock inventory."""

    refund_reference: Optional[str] = Field(default=None, max_length=100, description="Bank transfer reference / transaction ID")
    should_restock: bool = Field(default=True, description="Whether to add returned item back to supplier inventory count")


class OrderReturnResponseSchema(BaseModel):
    """Return representation for customer tracking and owner administration."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    order_line_id: uuid.UUID
    return_type: str
    reason: str
    customer_notes: Optional[str] = None
    status: str
    exchange_variant_id: Optional[int] = None
    refund_amount: CurrencyAmount
    refund_reference: Optional[str] = None
    restocked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
