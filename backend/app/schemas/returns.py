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
    return_type: str = Field(description="'refund_bank_transfer', 'size_exchange', or 'store_credit'")
    reason: str = Field(description="'size_too_small', 'size_too_large', 'damaged_defective', 'not_as_described', or 'changed_mind'")
    customer_notes: Optional[str] = Field(default=None, max_length=1000, description="Customer explanation")
    exchange_variant_id: Optional[int] = Field(default=None, ge=1, description="Desired variant ID for size exchanges")
    quantity: int = Field(ge=1, description='Number of purchased units to return')


class OrderReturnApproveRequest(BaseModel):
    """Admin payload to approve a return request."""

    refund_amount_minor: Optional[int] = Field(default=None, ge=0, description="Overridden refund amount in paisas")
    replacement_charge_minor: int = Field(default=0, ge=0, le=2147483647,
                                           description='Separate exchange charge in paisas')


class RefundExecutionRequest(BaseModel):
    amount_minor: int = Field(ge=1, le=2147483647)
    reference: str = Field(min_length=3, max_length=120)
    channel: str = Field(default='bank_transfer')
    note: Optional[str] = Field(default=None, max_length=500)


class RefundExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    amount_minor: int
    reference: str
    channel: str
    executed_at: datetime


class OrderReturnCompleteRequest(BaseModel):
    """Admin payload to finalize a fully inspected return; restock occurred at inspection."""

    refund_reference: Optional[str] = Field(default=None, max_length=100,
        description="Deprecated input, ignored. Record an executed refund via the refund-executions endpoint.")
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
    replacement_charge: CurrencyAmount = Field(default_factory=lambda: CurrencyAmount.from_minor(0))
    replacement_shipment_id: Optional[uuid.UUID] = None
    replacement_shipment_status: Optional[str] = None
    replacement_rto_inspected_at: Optional[datetime] = None
    replacement_stock_reconciliation_status: Optional[str] = None
    replacement_line_id: Optional[uuid.UUID] = None
    refund_amount: CurrencyAmount
    refund_paid: CurrencyAmount = Field(default_factory=lambda: CurrencyAmount.from_minor(0))
    refund_outstanding: CurrencyAmount = Field(default_factory=lambda: CurrencyAmount.from_minor(0))
    refund_executions: list[RefundExecutionResponse] = []
    refund_reference: Optional[str] = None
    restocked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_return(cls, ret: Any) -> 'OrderReturnResponseSchema':
        shipment = next((s for s in ret.order.shipments if s.replacement_return_id == ret.id), None)
        replacement_line = next((line for line in ret.order.lines if line.replacement_return_id == ret.id), None)
        paid = sum(item.amount_minor for item in ret.refund_executions)
        return cls(
            id=ret.id, order_id=ret.order_id, order_line_id=ret.order_line_id,
            return_type=ret.return_type, reason=ret.reason, customer_notes=ret.customer_notes,
            status=ret.status, quantity=ret.quantity, received_quantity=ret.received_quantity,
            sellable_quantity=ret.sellable_quantity, damaged_quantity=ret.damaged_quantity,
            inspection_state=ret.inspection_state, exchange_variant_id=ret.exchange_variant_id,
            replacement_charge=CurrencyAmount.from_minor(ret.replacement_charge_minor),
            replacement_shipment_id=shipment.id if shipment else None,
            replacement_shipment_status=shipment.status if shipment else None,
            replacement_rto_inspected_at=shipment.rto_restocked_at if shipment else None,
            replacement_stock_reconciliation_status=shipment.stock_reconciliation_status if shipment else None,
            replacement_line_id=replacement_line.id if replacement_line else None,
            inspection_notes=ret.inspection_notes, inspected_at=ret.inspected_at,
            refund_amount=CurrencyAmount.from_minor(ret.refund_amount_minor),
            refund_paid=CurrencyAmount.from_minor(paid),
            refund_outstanding=CurrencyAmount.from_minor(max(0, ret.refund_amount_minor - paid)),
            refund_executions=[RefundExecutionResponse.model_validate(item) for item in ret.refund_executions],
            refund_reference=ret.refund_reference, restocked_at=ret.restocked_at,
            created_at=ret.created_at, updated_at=ret.updated_at,
        )
