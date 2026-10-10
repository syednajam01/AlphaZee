"""
returns.py — Storefront API endpoints for customer return requests and size exchanges.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalog import CurrencyAmount
from app.schemas.returns import OrderReturnCreateRequest, OrderReturnResponseSchema
from app.services.returns import create_return_request

router = APIRouter(prefix="/returns", tags=["Storefront Returns"])


@router.post(
    "/request",
    response_model=OrderReturnResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit return or size exchange request for an ordered item",
)
def submit_return_request(
    payload: OrderReturnCreateRequest,
    db: Session = Depends(get_db),
) -> OrderReturnResponseSchema:
    try:
        ret = create_return_request(
            db,
            order_id=payload.order_id,
            order_line_id=payload.order_line_id,
            return_type=payload.return_type,
            reason=payload.reason,
            customer_notes=payload.customer_notes,
            exchange_variant_id=payload.exchange_variant_id,
        )
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema(
            id=ret.id,
            order_id=ret.order_id,
            order_line_id=ret.order_line_id,
            return_type=ret.return_type,
            reason=ret.reason,
            customer_notes=ret.customer_notes,
            status=ret.status,
            exchange_variant_id=ret.exchange_variant_id,
            refund_amount=CurrencyAmount.from_minor(ret.refund_amount_minor),
            refund_reference=ret.refund_reference,
            restocked_at=ret.restocked_at,
            created_at=ret.created_at,
            updated_at=ret.updated_at,
        )
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
