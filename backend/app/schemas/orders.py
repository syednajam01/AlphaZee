"""
Pydantic schemas for AlphaZee Order APIs (v1).

Enforces:
- Non-negative integer minor unit serialization for financial amounts.
- Strict validation of Pakistan phone numbers and allowed payment methods.
- Purchase-time snapshot representations.
- Honest bank transfer payment instructions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings
from app.models.orders import ALLOWED_PAYMENT_METHODS, normalize_pakistan_phone
from app.schemas.catalog import CurrencyAmount
from app.schemas.returns import OrderReturnResponseSchema


class OrderItemRequest(BaseModel):
    """Line item requested by customer at checkout."""

    variant_id: int = Field(ge=1, description="Catalog variant ID")
    quantity: int = Field(ge=1, le=50, description="Quantity to purchase (1-50)")


class OrderCreateRequest(BaseModel):
    """Customer checkout payload."""

    customer_name: str = Field(min_length=2, max_length=100, description="Full recipient name")
    customer_phone: str = Field(description="Pakistan mobile phone number (e.g. 0300-1234567)")
    customer_email: Optional[str] = Field(default=None, max_length=120, description="Optional email for receipts")
    shipping_address_line1: str = Field(min_length=5, max_length=200, description="Street address")
    shipping_address_line2: Optional[str] = Field(default=None, max_length=200, description="Apartment/Floor/Area")
    shipping_city: str = Field(min_length=2, max_length=60, description="Destination city")
    shipping_province: str = Field(min_length=2, max_length=60, description="Province/Region")
    shipping_postal_code: Optional[str] = Field(default=None, max_length=12, description="Postal code")
    payment_method: str = Field(description="Payment method: 'cod' or 'bank_transfer'")
    coupon_code: Optional[str] = Field(default=None, max_length=50, description="Promotional voucher code")
    utm_source: Optional[str] = Field(default=None, max_length=100, description="Marketing source")
    utm_medium: Optional[str] = Field(default=None, max_length=100, description="Marketing medium")
    utm_campaign: Optional[str] = Field(default=None, max_length=100, description="Marketing campaign")
    customer_notes: Optional[str] = Field(default=None, max_length=500, description="Special delivery instructions")
    idempotency_key: Optional[str] = Field(default=None, max_length=64, description="Must match Idempotency-Key header if supplied")
    items: list[OrderItemRequest] = Field(min_length=1, description="Cart items to purchase")

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_pakistan_phone(v)

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method {v!r}. Must be one of {sorted(ALLOWED_PAYMENT_METHODS)}"
            )
        return v_clean


class OrderLineResponseSchema(BaseModel):
    """Immutable line item snapshot as captured at order placement time."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fulfillment_kind: str = 'original'
    replacement_return_id: Optional[uuid.UUID] = None
    variant_id: int
    product_title: str = Field(description="Product title snapshot at purchase time")
    variant_sku: str = Field(description="Variant SKU snapshot")
    size: Optional[str] = None
    color: Optional[str] = None
    unit_price: CurrencyAmount
    quantity: int
    line_total: CurrencyAmount


class PaymentReceiptResponseSchema(BaseModel):
    """Payment proof uploaded for bank transfer orders."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_image_url: str
    bank_reference: Optional[str] = None
    uploaded_at: datetime
    verified_at: Optional[datetime] = None


class BankInstructionsSchema(BaseModel):
    """Bank details captured when instructions were actually sent."""

    bank_name: str
    account_title: str
    account_number: str
    iban: str
    instructions: str = (
        "Please transfer the total order amount to the bank account above and upload "
        "a screenshot of the transaction receipt. Funds will be verified by the owner "
        "before dispatching your order."
    )


COURIER_DISPLAY_NAMES = {
    "trax": "Trax Logistics",
    "leopards": "Leopards Courier",
    "call_courier": "Call Courier",
    "postex": "PostEx",
    "tcs": "TCS Express",
    "mnp": "M&P Express",
    "manual": "AlphaZee Direct Dispatch",
}


class ShipmentAllocationInfoSchema(BaseModel):
    order_line_id: uuid.UUID
    quantity: int
    received_quantity: int
    sellable_quantity: int
    damaged_quantity: int
    inspection_notes: Optional[str] = None


class ShipmentInfoSchema(BaseModel):
    """Customer-facing courier tracking details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    replacement_return_id: Optional[uuid.UUID] = None
    courier_code: str
    courier_name: str = ""
    tracking_number: str
    tracking_url: Optional[str] = None
    status: str
    cod_amount_minor: int = 0
    settlement_outstanding_minor: int = 0
    cod_remittance_status: str = 'not_applicable'
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    rto_restocked_at: Optional[datetime] = None
    stock_reconciliation_status: str = 'ready'
    allocations: list[ShipmentAllocationInfoSchema] = []

    @classmethod
    def from_orm_model(cls, s: Any) -> ShipmentInfoSchema:
        code = getattr(s, "courier_code", "manual")
        return cls(
            id=s.id,
            replacement_return_id=s.replacement_return_id,
            courier_code=code,
            courier_name=COURIER_DISPLAY_NAMES.get(code, code.title()),
            tracking_number=s.tracking_number,
            tracking_url=s.tracking_url,
            status=s.status,
            cod_amount_minor=s.cod_amount_minor,
            settlement_outstanding_minor=s.settlement_outstanding_minor,
            cod_remittance_status=s.cod_remittance_status,
            dispatched_at=s.dispatched_at,
            delivered_at=s.delivered_at,
            rto_restocked_at=s.rto_restocked_at,
            stock_reconciliation_status=s.stock_reconciliation_status,
            allocations=[ShipmentAllocationInfoSchema(
                order_line_id=a.reservation.order_line_id,
                quantity=a.quantity,
                received_quantity=a.received_quantity,
                sellable_quantity=a.sellable_quantity,
                damaged_quantity=a.damaged_quantity,
                inspection_notes=a.inspection_notes,
            ) for a in s.allocations],
        )


class OrderResponseSchema(BaseModel):
    """Comprehensive order response for storefront confirmation and customer tracking."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    idempotency_key: Optional[str] = None
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    shipping_address_line1: str
    shipping_address_line2: Optional[str] = None
    shipping_city: str
    shipping_province: str
    shipping_postal_code: Optional[str] = None
    payment_method: str
    payment_status: str
    order_status: str
    subtotal: CurrencyAmount
    discount_amount: CurrencyAmount
    coupon_code: Optional[str] = None
    shipping_fee: CurrencyAmount
    total: CurrencyAmount
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    customer_notes: Optional[str] = None
    payment_deadline_at: Optional[datetime] = None
    payment_instructions_sent_at: Optional[datetime] = None
    payment_instructions_channel: Optional[str] = None
    payment_verified_at: Optional[datetime] = None
    payment_review_status: str = 'none'
    payment_review_started_at: Optional[datetime] = None
    payment_reviewed_at: Optional[datetime] = None
    supplier_confirmed_at: Optional[datetime] = None
    supplier_notes: Optional[str] = None
    placed_at: datetime
    lines: list[OrderLineResponseSchema]
    receipts: list[PaymentReceiptResponseSchema] = []
    shipments: list[ShipmentInfoSchema] = []
    returns: list[OrderReturnResponseSchema] = []
    bank_instructions: Optional[BankInstructionsSchema] = None


class OrderCreateResponseSchema(OrderResponseSchema):
    access_code: str = Field(description='Save this private code to regain access on another device')


class OrderAccessExchangeRequest(BaseModel):
    order_number: str = Field(min_length=3, max_length=50)
    access_code: str = Field(min_length=43, max_length=43)


class PaymentReceiptUploadRequest(BaseModel):
    """Payload for uploading bank transfer transaction proof."""

    receipt_image_url: str = Field(min_length=5, max_length=500, description="Screenshot URL")
    bank_reference: Optional[str] = Field(default=None, max_length=64, description="Bank transaction ref / transaction ID")
