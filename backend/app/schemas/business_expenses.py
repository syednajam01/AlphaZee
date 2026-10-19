"""
business_expenses.py — Pydantic V2 schemas for categorized operating expenses, freight, packaging, and logistics overhead.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.business_expenses import (
    ALLOWED_EXPENSE_CATEGORIES,
    ALLOWED_EXPENSE_PAYMENT_METHODS,
)


class BusinessExpenseCreate(BaseModel):
    category: str = Field(..., description="Expense category e.g. packaging, advertising, outbound_delivery, rto_transport")
    amount_minor: int = Field(..., gt=0, description="Expense amount in integer paisas (minor units)")
    incurred_date: date = Field(..., description="Date expense was incurred (ISO 8601)")
    paid_date: date | None = Field(None, description="Date expense was paid (null if accrued/unpaid)")
    payee: str = Field(..., min_length=1, max_length=160, description="Name of vendor, supplier, or service provider paid")
    reference: str | None = Field(None, max_length=120, description="Invoice, receipt, or bank transfer reference")
    payment_method: str = Field("bank_transfer", description="Payment method: cash, bank_transfer, courier_deduction, credit_card, other")
    linked_shipment_id: uuid.UUID | None = Field(None, description="Optional link to shipment for delivery/RTO transport")
    linked_return_id: uuid.UUID | None = Field(None, description="Optional link to customer return for return transport")
    linked_courier_settlement_id: uuid.UUID | None = Field(None, description="Optional link to courier deduction entry to prevent double-counting")
    notes: str | None = Field(None, description="Operational notes or invoice line details")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_EXPENSE_CATEGORIES:
            raise ValueError(f"Invalid category {v!r}. Must be one of {sorted(ALLOWED_EXPENSE_CATEGORIES)}")
        return clean

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_EXPENSE_PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method {v!r}. Must be one of {sorted(ALLOWED_EXPENSE_PAYMENT_METHODS)}")
        return clean

    @field_validator("payee")
    @classmethod
    def validate_payee(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Payee cannot be blank.")
        return clean


class BusinessExpenseUpdate(BaseModel):
    category: str | None = None
    amount_minor: int | None = Field(None, gt=0)
    incurred_date: date | None = None
    paid_date: date | None = None
    payee: str | None = Field(None, min_length=1, max_length=160)
    reference: str | None = Field(None, max_length=120)
    payment_method: str | None = None
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in ALLOWED_EXPENSE_CATEGORIES:
            raise ValueError(f"Invalid category {v!r}. Must be one of {sorted(ALLOWED_EXPENSE_CATEGORIES)}")
        return clean

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in ALLOWED_EXPENSE_PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method {v!r}. Must be one of {sorted(ALLOWED_EXPENSE_PAYMENT_METHODS)}")
        return clean


class BusinessExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    amount_minor: int
    amount_pkr: float
    incurred_date: date
    paid_date: date | None
    payee: str
    reference: str | None
    payment_method: str
    linked_shipment_id: uuid.UUID | None
    linked_return_id: uuid.UUID | None
    linked_courier_settlement_id: uuid.UUID | None
    notes: str | None
    recorded_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class BusinessExpenseSummaryResponse(BaseModel):
    total_expenses_minor: int
    total_expenses_pkr: float
    paid_expenses_minor: int
    paid_expenses_pkr: float
    unpaid_expenses_minor: int
    unpaid_expenses_pkr: float
    category_totals: dict[str, int]
    category_totals_pkr: dict[str, float]
    count: int
