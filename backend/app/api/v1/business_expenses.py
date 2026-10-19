"""
business_expenses.py — Owner administrative endpoints for categorized business expenses, freight, and logistics overhead.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, require_owner_session
from app.schemas.business_expenses import (
    BusinessExpenseCreate,
    BusinessExpenseResponse,
    BusinessExpenseSummaryResponse,
)
from app.services import business_expenses as service

router = APIRouter(
    prefix="/admin/expenses",
    tags=["Business Expenses"],
    dependencies=[Depends(require_owner_session)],
)


class BusinessExpenseListResponse(BaseModel):
    expenses: list[BusinessExpenseResponse]
    total: int


@router.post(
    "",
    response_model=BusinessExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new business expense",
)
def create_expense_endpoint(
    payload: BusinessExpenseCreate,
    current_user: Annotated[OwnerPrincipal, Depends(require_owner_session)],
    db: Session = Depends(get_db),
) -> BusinessExpenseResponse:
    try:
        expense = service.create_business_expense(
            db,
            payload=payload,
            actor_user_id=current_user.session.user_id,
        )
        db.commit()
        db.refresh(expense)
        return BusinessExpenseResponse(
            id=expense.id,
            category=expense.category,
            amount_minor=expense.amount_minor,
            amount_pkr=round(expense.amount_minor / 100.0, 2),
            incurred_date=expense.incurred_date,
            paid_date=expense.paid_date,
            payee=expense.payee,
            reference=expense.reference,
            payment_method=expense.payment_method,
            linked_shipment_id=expense.linked_shipment_id,
            linked_return_id=expense.linked_return_id,
            linked_courier_settlement_id=expense.linked_courier_settlement_id,
            notes=expense.notes,
            recorded_by_user_id=expense.recorded_by_user_id,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=BusinessExpenseListResponse,
    summary="List business expenses with filters",
)
def list_expenses_endpoint(
    start_date: date | None = Query(None, description="Start date (inclusive, YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (inclusive, YYYY-MM-DD)"),
    category: str | None = Query(None, description="Filter by category"),
    payment_method: str | None = Query(None, description="Filter by payment method"),
    is_paid: bool | None = Query(None, description="Filter by paid (true) or accrued/unpaid (false)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> BusinessExpenseListResponse:
    rows, total = service.get_business_expenses(
        db,
        start_date=start_date,
        end_date=end_date,
        category=category,
        payment_method=payment_method,
        is_paid=is_paid,
        limit=limit,
        offset=offset,
    )
    return BusinessExpenseListResponse(
        expenses=[
            BusinessExpenseResponse(
                id=e.id,
                category=e.category,
                amount_minor=e.amount_minor,
                amount_pkr=round(e.amount_minor / 100.0, 2),
                incurred_date=e.incurred_date,
                paid_date=e.paid_date,
                payee=e.payee,
                reference=e.reference,
                payment_method=e.payment_method,
                linked_shipment_id=e.linked_shipment_id,
                linked_return_id=e.linked_return_id,
                linked_courier_settlement_id=e.linked_courier_settlement_id,
                notes=e.notes,
                recorded_by_user_id=e.recorded_by_user_id,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in rows
        ],
        total=total,
    )


@router.get(
    "/summary",
    response_model=BusinessExpenseSummaryResponse,
    summary="Get business expense summary and category breakdown",
)
def get_expense_summary_endpoint(
    start_date: date | None = Query(None, description="Start date (inclusive, YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (inclusive, YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> BusinessExpenseSummaryResponse:
    return service.get_expense_summary(
        db,
        start_date=start_date,
        end_date=end_date,
    )
