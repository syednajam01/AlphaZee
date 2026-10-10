"""
coupons.py — Storefront API endpoints for promotional coupon validation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.catalog import CurrencyAmount
from app.schemas.promotions import CouponValidateRequest, CouponValidateResponse
from app.services.promotions import validate_coupon

router = APIRouter(prefix="/coupons", tags=["Storefront Promotions"])


@router.post(
    "/validate",
    response_model=CouponValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate coupon code against current cart",
)
def validate_customer_coupon(
    payload: CouponValidateRequest,
    db: Session = Depends(get_db),
) -> CouponValidateResponse:
    try:
        res = validate_coupon(
            db,
            code=payload.code,
            subtotal_minor=payload.subtotal_minor,
            shipping_fee_minor=payload.shipping_fee_minor,
        )
        return CouponValidateResponse(
            valid=res.valid,
            code=res.code,
            discount_type=res.discount_type,
            discount_value=res.discount_value,
            discount_amount=CurrencyAmount.from_minor(res.discount_amount_minor),
            is_free_shipping=res.is_free_shipping,
            message=res.message,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
