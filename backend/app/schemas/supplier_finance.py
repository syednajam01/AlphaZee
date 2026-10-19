"""
supplier_finance.py — Pydantic schemas for supplier agreements, manual ledger entries, and statements.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


PayableTriggerType = Literal["manual", "confirmed_pickup", "dispatch", "delivery"]
LedgerEntryTypeLiteral = Literal[
    "charge", "credit_note", "payment", "advance", "refund_received", "opening_balance", "adjustment"
]
LedgerDirectionLiteral = Literal["credit", "debit"]


class SupplierAgreementSchema(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    payable_trigger: PayableTriggerType
    payment_terms_days: int
    is_active: bool
    effective_from: datetime
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierAgreementUpdateRequest(BaseModel):
    payable_trigger: PayableTriggerType = Field(default="manual")
    payment_terms_days: int = Field(default=0, ge=0, le=365)
    notes: Optional[str] = Field(default=None, max_length=500)


class SupplierLedgerEntrySchema(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    entry_type: str
    amount_minor: int
    direction: str
    source_event_key: Optional[str] = None
    order_id: Optional[uuid.UUID] = None
    order_line_id: Optional[uuid.UUID] = None
    shipment_id: Optional[uuid.UUID] = None
    reference: str
    effective_date: date
    status: str
    reversal_entry_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    recorded_by_user_id: Optional[uuid.UUID] = None
    recorded_at: datetime
    allocated_amount_minor: int = 0
    unallocated_amount_minor: int = 0

    model_config = {"from_attributes": True}


class ManualChargeRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Amount in paisas (positive)")
    reference: str = Field(min_length=1, max_length=120, description="Invoice or reference number")
    effective_date: date = Field(description="Date the charge was incurred")
    notes: Optional[str] = Field(default=None, max_length=500)
    order_id: Optional[uuid.UUID] = None
    order_line_id: Optional[uuid.UUID] = None


class ManualCreditNoteRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Credit amount in paisas (positive)")
    reference: str = Field(min_length=1, max_length=120, description="Credit note or agreement reference")
    effective_date: date = Field(description="Date credit was accepted by vendor")
    notes: Optional[str] = Field(default=None, max_length=500)
    order_id: Optional[uuid.UUID] = None


class ReverseLedgerEntryRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=250, description="Detailed reason for reversing this posted entry")


class OpeningBalanceRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Opening balance in paisas (positive)")
    direction: LedgerDirectionLiteral = Field(
        default="credit",
        description="'credit' if AlphaZee owes the supplier (liability), 'debit' if supplier owes AlphaZee (advance)",
    )
    as_of_date: date = Field(description="As-of cut-off date")
    reference: str = Field(min_length=1, max_length=120, description="Source statement or audit reference")
    notes: Optional[str] = Field(default=None, max_length=500)


class OpeningBalancePreviewResponse(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    amount_minor: int
    direction: str
    as_of_date: date
    reference: str
    notes: Optional[str] = None
    current_outstanding_minor: int
    projected_outstanding_minor: int


class SupplierLedgerSummarySchema(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    agreement_trigger: str
    payment_terms_days: int
    total_charges_minor: int
    total_credits_minor: int
    total_payments_minor: int
    outstanding_payable_minor: int
    unallocated_advances_minor: int


class SupplierLedgerListResponse(BaseModel):
    entries: list[SupplierLedgerEntrySchema]
    summary: SupplierLedgerSummarySchema
    total: int
    page: int
    page_size: int


class SupplierPaymentAllocationItem(BaseModel):
    charge_entry_id: uuid.UUID
    allocated_amount_minor: int = Field(gt=0, description="Amount allocated to this charge in paisas")


class SupplierPaymentRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Payment amount in paisas (positive)")
    payment_method: str = Field(default="bank_transfer", max_length=32)
    reference: str = Field(min_length=1, max_length=120, description="Bank transfer reference / cheque # / cash voucher")
    effective_date: date = Field(description="Date payment was disbursed")
    notes: Optional[str] = Field(default=None, max_length=500)
    auto_allocate_fifo: bool = Field(default=True, description="Automatically allocate payment against oldest unpaid charges")
    allocations: list[SupplierPaymentAllocationItem] = Field(default_factory=list, description="Specific charge allocations")
    idempotency_key: Optional[str] = Field(default=None, max_length=100, description="Unique key to prevent duplicate payment on retry")


class SupplierAdvanceRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Advance disbursement amount in paisas")
    payment_method: str = Field(default="bank_transfer", max_length=32)
    reference: str = Field(min_length=1, max_length=120)
    effective_date: date = Field(description="Date advance was paid")
    notes: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class AllocatePaymentRequest(BaseModel):
    charge_entry_id: uuid.UUID = Field(description="Charge to allocate against")
    amount_minor: int = Field(gt=0, description="Amount to allocate in paisas")


class SupplierRefundRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Refund amount received in paisas")
    refund_method: str = Field(default="bank_transfer", max_length=32)
    reference: str = Field(min_length=1, max_length=120, description="Vendor refund transaction or voucher reference")
    effective_date: date = Field(description="Date refund was received into AlphaZee account")
    notes: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class SupplierPaymentAllocationSchema(BaseModel):
    id: uuid.UUID
    payment_entry_id: uuid.UUID
    charge_entry_id: uuid.UUID
    allocated_amount_minor: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UnpaidChargeItemSchema(BaseModel):
    id: uuid.UUID
    reference: str
    effective_date: date
    amount_minor: int
    allocated_amount_minor: int
    unpaid_amount_minor: int


class UnallocatedPaymentItemSchema(BaseModel):
    id: uuid.UUID
    reference: str
    effective_date: date
    amount_minor: int
    allocated_amount_minor: int
    unallocated_amount_minor: int


class SupplierStatementEntrySchema(BaseModel):
    id: uuid.UUID
    effective_date: date
    entry_type: str
    direction: str
    reference: str
    amount_minor: int
    running_payable_minor: int
    notes: Optional[str] = None
    status: str


class SupplierStatementResponse(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    start_date: date
    end_date: date
    opening_payable_minor: int
    charges_in_period_minor: int
    credits_in_period_minor: int
    payments_in_period_minor: int
    refunds_in_period_minor: int
    net_movement_minor: int
    closing_payable_minor: int
    unallocated_advances_minor: int
    entries: list[SupplierStatementEntrySchema]

