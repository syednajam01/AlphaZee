"""
returns.py — Pydantic schemas for order returns, size exchanges, and refund tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any

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
    quantity: int = Field(ge=1, description='Number of purchased units to return')


class OrderReturnApproveRequest(BaseModel):
    """Admin payload to approve a return request."""

    refund_amount_minor: Optional[int] = Field(default=None, ge=0, description="Overridden refund amount in paisas")


class OrderReturnCompleteRequest(BaseModel):
    """Admin payload to finalize a fully inspected return; restock occurred at inspection."""

    refund_reference: Optional[str] = Field(default=None, max_length=100, description="Bank transfer reference / transaction ID")
    should_restock: bool = Field(default=True, description="Legacy compatibility flag; no stock movement occurs at completion")


class OrderReturnReceiveRequest(BaseModel):
    received_quantity: int = Field(ge=0)


class OrderReturnInspectRequest(BaseModel):
    sellable_quantity: int = Field(ge=0)
    damaged_quantity: int = Field(ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


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
    quantity: Optional[int] = None
    received_quantity: int = 0
    sellable_quantity: int = 0
    damaged_quantity: int = 0
    inspection_state: str = 'pending'
    inspection_notes: Optional[str] = None
    inspected_at: Optional[datetime] = None
    exchange_variant_id: Optional[int] = None
    refund_amount: CurrencyAmount
    refund_reference: Optional[str] = None
    restocked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_return(cls, ret: Any) -> 'OrderReturnResponseSchema':
        return cls(
            id=ret.id, order_id=ret.order_id, order_line_id=ret.order_line_id,
            return_type=ret.return_type, reason=ret.reason, customer_notes=ret.customer_notes,
            status=ret.status, quantity=ret.quantity, received_quantity=ret.received_quantity,
            sellable_quantity=ret.sellable_quantity, damaged_quantity=ret.damaged_quantity,
            inspection_state=ret.inspection_state, exchange_variant_id=ret.exchange_variant_id,
            inspection_notes=ret.inspection_notes, inspected_at=ret.inspected_at,
            refund_amount=CurrencyAmount.from_minor(ret.refund_amount_minor),
            refund_reference=ret.refund_reference, restocked_at=ret.restocked_at,
            created_at=ret.created_at, updated_at=ret.updated_at,
        )
