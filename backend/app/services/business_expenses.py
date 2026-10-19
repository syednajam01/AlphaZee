"""
business_expenses.py — Service layer for recording, filtering, and summarizing categorized business expenses.
Guarantees:
- Zero double counting when courier deductions settle recorded courier/delivery expenses.
- Strict tracking of AlphaZee-borne outbound, RTO, and customer-return transport expenses.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business_expenses import BusinessExpense
from app.models.finance import CourierSettlementEntry
from app.models.returns import OrderReturn
from app.models.shipments import Shipment
from app.schemas.business_expenses import (
    BusinessExpenseCreate,
    BusinessExpenseSummaryResponse,
    BusinessExpenseUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_business_expense(
    db: Session,
    payload: BusinessExpenseCreate,
    actor_user_id: uuid.UUID | None = None,
) -> BusinessExpense:
    """
    Record an immutable categorized business expense.
    """
    # Validate linked entities if provided
    if payload.linked_shipment_id:
        shipment = db.get(Shipment, payload.linked_shipment_id)
        if not shipment:
            raise ValueError(f"Linked shipment {payload.linked_shipment_id} does not exist.")

    if payload.linked_return_id:
        ret = db.get(OrderReturn, payload.linked_return_id)
        if not ret:
            raise ValueError(f"Linked order return {payload.linked_return_id} does not exist.")

    if payload.linked_courier_settlement_id:
        settlement = db.get(CourierSettlementEntry, payload.linked_courier_settlement_id)
        if not settlement:
            raise ValueError(f"Linked courier settlement {payload.linked_courier_settlement_id} does not exist.")

    expense = BusinessExpense(
        category=payload.category,
        amount_minor=payload.amount_minor,
        incurred_date=payload.incurred_date,
        paid_date=payload.paid_date,
        payee=payload.payee,
        reference=payload.reference,
        payment_method=payload.payment_method,
        linked_shipment_id=payload.linked_shipment_id,
        linked_return_id=payload.linked_return_id,
        linked_courier_settlement_id=payload.linked_courier_settlement_id,
        notes=payload.notes,
        recorded_by_user_id=actor_user_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(expense)
    db.flush()
    return expense


def get_business_expenses(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    payment_method: str | None = None,
    is_paid: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[BusinessExpense], int]:
    """
    List business expenses with optional filters and pagination.
    """
    stmt = select(BusinessExpense)

    if start_date:
        stmt = stmt.where(BusinessExpense.incurred_date >= start_date)
    if end_date:
        stmt = stmt.where(BusinessExpense.incurred_date <= end_date)
    if category:
        stmt = stmt.where(BusinessExpense.category == category.strip().lower())
    if payment_method:
        stmt = stmt.where(BusinessExpense.payment_method == payment_method.strip().lower())
    if is_paid is True:
        stmt = stmt.where(BusinessExpense.paid_date.is_not(None))
    elif is_paid is False:
        stmt = stmt.where(BusinessExpense.paid_date.is_(None))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(BusinessExpense.incurred_date.desc(), BusinessExpense.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    rows = list(db.scalars(stmt).all())
    return rows, total


def get_expense_summary(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> BusinessExpenseSummaryResponse:
    """
    Compute aggregate expense statistics for period reports.
    """
    base_filter = []
    if start_date:
        base_filter.append(BusinessExpense.incurred_date >= start_date)
    if end_date:
        base_filter.append(BusinessExpense.incurred_date <= end_date)

    # Total expenses
    total_stmt = select(
        func.coalesce(func.sum(BusinessExpense.amount_minor), 0),
        func.count(BusinessExpense.id),
    ).where(*base_filter)
    total_minor, count = db.execute(total_stmt).one()

    # Paid expenses
    paid_stmt = select(
        func.coalesce(func.sum(BusinessExpense.amount_minor), 0)
    ).where(*base_filter, BusinessExpense.paid_date.is_not(None))
    paid_minor = db.scalar(paid_stmt) or 0

    unpaid_minor = total_minor - paid_minor

    # Category breakdown
    cat_stmt = (
        select(
            BusinessExpense.category,
            func.coalesce(func.sum(BusinessExpense.amount_minor), 0),
        )
        .where(*base_filter)
        .group_by(BusinessExpense.category)
    )
    category_totals = {cat: int(amount) for cat, amount in db.execute(cat_stmt).all()}
    category_totals_pkr = {cat: round(amount / 100.0, 2) for cat, amount in category_totals.items()}

    return BusinessExpenseSummaryResponse(
        total_expenses_minor=total_minor,
        total_expenses_pkr=round(total_minor / 100.0, 2),
        paid_expenses_minor=paid_minor,
        paid_expenses_pkr=round(paid_minor / 100.0, 2),
        unpaid_expenses_minor=unpaid_minor,
        unpaid_expenses_pkr=round(unpaid_minor / 100.0, 2),
        category_totals=category_totals,
        category_totals_pkr=category_totals_pkr,
        count=count,
    )
