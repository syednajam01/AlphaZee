"""
supplier_finance.py — Owner administrative endpoints for supplier agreements, manual liabilities, and ledger.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from datetime import date
from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, require_owner_session
from app.schemas.supplier_finance import (
    AllocatePaymentRequest,
    ManualChargeRequest,
    ManualCreditNoteRequest,
    OpeningBalancePreviewResponse,
    OpeningBalanceRequest,
    ReverseLedgerEntryRequest,
    SupplierAdvanceRequest,
    SupplierAgreementSchema,
    SupplierAgreementUpdateRequest,
    SupplierLedgerEntrySchema,
    SupplierLedgerListResponse,
    SupplierLedgerSummarySchema,
    SupplierPaymentAllocationSchema,
    SupplierPaymentRequest,
    SupplierRefundRequest,
    SupplierStatementResponse,
)
from app.services import supplier_finance as service

router = APIRouter(
    prefix="/admin/suppliers",
    tags=["Supplier Agreements & Finance"],
    dependencies=[Depends(require_owner_session)],
)


@router.get(
    "/{supplier_id}/agreement",
    response_model=SupplierAgreementSchema,
    summary="Get supplier settlement agreement",
)
def get_supplier_agreement_endpoint(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SupplierAgreementSchema:
    agreement = service.get_or_create_supplier_agreement(db, supplier_id)
    return SupplierAgreementSchema.model_validate(agreement)


@router.post(
    "/{supplier_id}/agreement",
    response_model=SupplierAgreementSchema,
    summary="Update supplier settlement agreement terms (POST)",
)
@router.put(
    "/{supplier_id}/agreement",
    response_model=SupplierAgreementSchema,
    summary="Update supplier settlement agreement terms (PUT)",
)
def update_supplier_agreement_endpoint(
    supplier_id: uuid.UUID,
    payload: SupplierAgreementUpdateRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierAgreementSchema:
    agreement = service.update_supplier_agreement(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierAgreementSchema.model_validate(agreement)


@router.get(
    "/{supplier_id}/ledger",
    response_model=SupplierLedgerListResponse,
    summary="List supplier ledger entries and summary balance",
)
def get_supplier_ledger_endpoint(
    supplier_id: uuid.UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
) -> SupplierLedgerListResponse:
    entries, total, summary = service.list_supplier_ledger_entries(
        db,
        supplier_id=supplier_id,
        page=page,
        page_size=page_size,
    )
    return SupplierLedgerListResponse(
        entries=[SupplierLedgerEntrySchema.model_validate(e) for e in entries],
        summary=summary,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{supplier_id}/ledger/charge",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Manually post an approved supplier charge",
)
def post_manual_charge_endpoint(
    supplier_id: uuid.UUID,
    payload: ManualChargeRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    entry = service.post_manual_charge(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(entry)


@router.post(
    "/{supplier_id}/ledger/credit-note",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Manually post an acknowledged vendor credit note",
)
def post_manual_credit_note_endpoint(
    supplier_id: uuid.UUID,
    payload: ManualCreditNoteRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    entry = service.post_manual_credit_note(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(entry)


@router.get(
    "/{supplier_id}/ledger/summary",
    response_model=SupplierLedgerSummarySchema,
    summary="Get real-time supplier liability and ledger summary balance",
)
def get_supplier_ledger_summary_endpoint(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SupplierLedgerSummarySchema:
    summary = service.get_supplier_ledger_summary(db, supplier_id)
    return SupplierLedgerSummarySchema.model_validate(summary)


@router.post(
    "/ledger/{entry_id}/reverse",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Immutably reverse a posted ledger entry",
)
@router.post(
    "/{supplier_id}/ledger/{entry_id}/reverse",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Immutably reverse a posted ledger entry (scoped)",
)
def reverse_ledger_entry_endpoint(
    entry_id: uuid.UUID,
    payload: ReverseLedgerEntryRequest,
    supplier_id: uuid.UUID | None = None,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    reversal = service.reverse_ledger_entry(
        db,
        entry_id=entry_id,
        reason=payload.reason,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(reversal)


@router.post(
    "/{supplier_id}/ledger/opening-balance/preview",
    response_model=OpeningBalancePreviewResponse,
    summary="Preview opening balance impact without writing to database",
)
def preview_opening_balance_endpoint(
    supplier_id: uuid.UUID,
    payload: OpeningBalanceRequest,
    db: Session = Depends(get_db),
) -> OpeningBalancePreviewResponse:
    preview = service.preview_opening_balance(
        db,
        supplier_id=supplier_id,
        payload=payload,
    )
    return OpeningBalancePreviewResponse.model_validate(preview)


@router.post(
    "/{supplier_id}/ledger/opening-balance",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Apply an opening balance entry with audit reference",
)
def apply_opening_balance_endpoint(
    supplier_id: uuid.UUID,
    payload: OpeningBalanceRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    entry = service.apply_opening_balance(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(entry)


@router.post(
    "/{supplier_id}/ledger/payment",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Record a supplier payment and allocate against charges",
)
def post_supplier_payment_endpoint(
    supplier_id: uuid.UUID,
    payload: SupplierPaymentRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    payment_entry, allocs = service.post_supplier_payment(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    alloc_sum = sum(a.allocated_amount_minor for a in allocs)
    d = {
        **payment_entry.__dict__,
        "allocated_amount_minor": alloc_sum,
        "unallocated_amount_minor": max(0, payment_entry.amount_minor - alloc_sum),
    }
    return SupplierLedgerEntrySchema.model_validate(d)


@router.post(
    "/{supplier_id}/ledger/advance",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Disburse an advance payment to a supplier",
)
def post_supplier_advance_endpoint(
    supplier_id: uuid.UUID,
    payload: SupplierAdvanceRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    advance_entry = service.post_supplier_advance(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(advance_entry)


@router.post(
    "/{supplier_id}/ledger/payments/{payment_id}/allocate",
    response_model=SupplierPaymentAllocationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate unallocated payment funds against a charge",
)
def allocate_payment_advance_endpoint(
    supplier_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: AllocatePaymentRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierPaymentAllocationSchema:
    alloc = service.allocate_payment_advance(
        db,
        supplier_id=supplier_id,
        payment_entry_id=payment_id,
        payload=payload,
    )
    return SupplierPaymentAllocationSchema.model_validate(alloc)


@router.post(
    "/{supplier_id}/ledger/refund",
    response_model=SupplierLedgerEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Record a cash refund received from a supplier",
)
def post_supplier_refund_endpoint(
    supplier_id: uuid.UUID,
    payload: SupplierRefundRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> SupplierLedgerEntrySchema:
    refund_entry = service.post_supplier_refund(
        db,
        supplier_id=supplier_id,
        payload=payload,
        actor_id=principal.owner.user_id,
    )
    return SupplierLedgerEntrySchema.model_validate(refund_entry)


@router.get(
    "/{supplier_id}/ledger/unpaid-and-advances",
    summary="Get unpaid charges and unallocated payments for allocation",
)
def get_unpaid_and_advances_endpoint(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    return service.get_unpaid_charges_and_advances(db, supplier_id=supplier_id)


@router.get(
    "/{supplier_id}/statement",
    response_model=SupplierStatementResponse,
    summary="Get supplier period statement with opening, movement, and closing reconciliation",
)
def get_supplier_statement_endpoint(
    supplier_id: uuid.UUID,
    start_date: Annotated[date, Query(description="Start date inclusive (YYYY-MM-DD)")],
    end_date: Annotated[date, Query(description="End date inclusive (YYYY-MM-DD)")],
    db: Session = Depends(get_db),
) -> SupplierStatementResponse:
    statement = service.get_supplier_statement(
        db,
        supplier_id=supplier_id,
        start_date=start_date,
        end_date=end_date,
    )
    return SupplierStatementResponse.model_validate(statement)

