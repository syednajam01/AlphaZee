"""
returns.py — Storefront API endpoints for customer return requests and size exchanges.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalog import CurrencyAmount
from app.schemas.returns import OrderReturnCreateRequest, OrderReturnResponseSchema
from app.services.returns import create_return_request
from app.services.order_access import require_order_access
from app.dependencies.auth import require_trusted_origin

router = APIRouter(prefix="/returns", tags=["Storefront Returns"])


@router.post(
    "/request",
    response_model=OrderReturnResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit return or size exchange request for an ordered item",
    dependencies=[Depends(require_trusted_origin)],
)
def submit_return_request(
    payload: OrderReturnCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderReturnResponseSchema:
    require_order_access(db, request, order_id=payload.order_id)
    try:
        ret = create_return_request(
            db,
            order_id=payload.order_id,
            order_line_id=payload.order_line_id,
            return_type=payload.return_type,
            reason=payload.reason,
            customer_notes=payload.customer_notes,
            exchange_variant_id=payload.exchange_variant_id,
            quantity=payload.quantity,
        )
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema.from_return(ret)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
