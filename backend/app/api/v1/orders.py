"""
Customer order routes for AlphaZee Storefront API (v1).

Handles:
- POST /api/v1/orders: Authoritative order placement and atomic stock reservations.
- POST /api/v1/orders/{order_number}/receipt: Payment proof submission for Bank Transfer orders.
- GET /api/v1/orders/{order_number}: Customer order status and tracking.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.orders import OrderItemRequest
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.checkout import require_checkout_enabled
from app.dependencies.auth import require_trusted_origin
from app.services.checkout_attempts import mint_checkout_session, require_checkout_session
from app.models.orders import Order
from app.models.catalog import Variant
from app.services.order_access import exchange_access_code, issue_access, require_order_access, set_order_session_cookie
from app.queries.reservations import InsufficientStockError
from app.schemas.catalog import CurrencyAmount
from app.schemas.orders import (
    BankInstructionsSchema,
    OrderCreateRequest,
    OrderCreateResponseSchema,
    OrderAccessExchangeRequest,
    OrderLineResponseSchema,
    OrderResponseSchema,
    PaymentReceiptResponseSchema,
    PaymentReceiptUploadRequest,
    ShipmentInfoSchema,
)
from app.schemas.returns import OrderReturnResponseSchema
from app.services.orders import (
    CreateOrderDTO,
    CheckoutAttemptConflict,
    OrderItemDTO,
    place_order,
    upload_payment_receipt,
)

router = APIRouter(prefix="/orders", tags=["Storefront Orders"])


class CheckoutQuoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[OrderItemRequest] = Field(min_length=1, max_length=100)
    shipping_city: str = Field(min_length=2, max_length=60)
    shipping_province: str = Field(min_length=2, max_length=60)
    coupon_code: str | None = None


@router.post('/quote', dependencies=[Depends(require_checkout_enabled), Depends(require_trusted_origin)])
def checkout_quote(payload: CheckoutQuoteRequest, db: Session = Depends(get_db)):
    from app.services.shipping import quote_shipping
    from app.services.promotions import validate_coupon
    quantities = {}
    for item in payload.items:
        quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity
    subtotal = 0
    try:
        for variant_id, quantity in quantities.items():
            variant = db.get(Variant, variant_id)
            if not variant or not variant.is_active or variant.price_minor is None:
                raise ValueError('A cart item is unavailable. Refresh your cart.')
            subtotal += variant.price_minor * quantity
        fee, rule = quote_shipping(db, subtotal, payload.shipping_city.strip(), payload.shipping_province.strip())
        discount = validate_coupon(db, code=payload.coupon_code, subtotal_minor=subtotal,
            shipping_fee_minor=fee).discount_amount_minor if payload.coupon_code else 0
        return {'subtotal_minor': subtotal, 'shipping_fee_minor': fee,
                'discount_minor': discount, 'total_minor': max(0, subtotal - discount + fee),
                'shipping_rule': rule}
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get('/checkout-session', dependencies=[Depends(require_checkout_enabled)])
def start_checkout_session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return mint_checkout_session(request, response)


def _order_to_response(order: Order) -> OrderResponseSchema:
    """Serialize SQLAlchemy Order into detailed Pydantic response."""
    lines = [
        OrderLineResponseSchema(
            id=line.id,
            fulfillment_kind=line.fulfillment_kind,
            replacement_return_id=line.replacement_return_id,
            variant_id=line.variant_id,
            product_title=line.product_title_snapshot,
            variant_sku=line.variant_sku_snapshot,
            size=line.variant_size_snapshot,
            color=line.variant_color_snapshot,
            unit_price=CurrencyAmount.from_minor(line.unit_price_minor),
            quantity=line.quantity,
            line_total=CurrencyAmount.from_minor(line.line_total_minor),
        )
        for line in order.lines
    ]

    receipts = [
        PaymentReceiptResponseSchema(
            id=rec.id,
            receipt_image_url=rec.receipt_image_url,
            bank_reference=rec.bank_reference,
            uploaded_at=rec.uploaded_at,
            verified_at=rec.verified_at,
        )
        for rec in order.receipts
    ]

    shipments = [
        ShipmentInfoSchema.from_orm_model(s)
        for s in getattr(order, "shipments", [])
    ]

    returns = [
        OrderReturnResponseSchema.from_return(r)
        for r in getattr(order, "returns", [])
    ]

    bank_instructions = None
    if (order.payment_method == 'bank_transfer' and order.payment_instructions_sent_at
            and all((order.payment_bank_name_snapshot, order.payment_account_title_snapshot,
                     order.payment_account_number_snapshot, order.payment_iban_snapshot))):
        bank_instructions = BankInstructionsSchema(
            bank_name=order.payment_bank_name_snapshot,
            account_title=order.payment_account_title_snapshot,
            account_number=order.payment_account_number_snapshot,
            iban=order.payment_iban_snapshot,
        )

    return OrderResponseSchema(
        supplier_picked_up_at=order.supplier_picked_up_at,
        id=order.id,
        order_number=order.order_number,
        idempotency_key=order.idempotency_key,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        shipping_address_line1=order.shipping_address_line1,
        shipping_address_line2=order.shipping_address_line2,
        shipping_city=order.shipping_city,
        shipping_province=order.shipping_province,
        shipping_postal_code=order.shipping_postal_code,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        order_status=order.order_status,
        subtotal=CurrencyAmount.from_minor(order.subtotal_minor),
        discount_amount=CurrencyAmount.from_minor(order.discount_amount_minor),
        coupon_code=order.coupon_code_snapshot,
        shipping_fee=CurrencyAmount.from_minor(order.shipping_fee_minor),
        total=CurrencyAmount.from_minor(order.total_minor),
        utm_source=order.utm_source,
        utm_medium=order.utm_medium,
        utm_campaign=order.utm_campaign,
        customer_notes=order.customer_notes,
        payment_deadline_at=order.payment_deadline_at,
        payment_instructions_sent_at=order.payment_instructions_sent_at,
        payment_instructions_channel=order.payment_instructions_channel,
        payment_verified_at=order.payment_verified_at,
        payment_review_status=order.payment_review_status,
        payment_review_started_at=order.payment_review_started_at,
        payment_reviewed_at=order.payment_reviewed_at,
        supplier_confirmed_at=order.supplier_confirmed_at,
        supplier_notes=order.supplier_notes,
        placed_at=order.placed_at,
        lines=lines,
        receipts=receipts,
        shipments=shipments,
        returns=returns,
        bank_instructions=bank_instructions,
    )


@router.post(
    "",
    response_model=OrderCreateResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new customer order",
    dependencies=[Depends(require_checkout_enabled), Depends(require_trusted_origin)],
    description=(
        "Authoritatively recalculates prices from catalog, holds required stock "
        "reservations, and creates immutable purchase snapshots."
    ),
)
def create_customer_order(
    payload: OrderCreateRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=64,
                                  pattern=r'^[A-Za-z0-9_-]+$'),
    checkout_session_hash: str = Depends(require_checkout_session),
    db: Session = Depends(get_db),
) -> OrderCreateResponseSchema:
    if payload.idempotency_key and payload.idempotency_key != idempotency_key:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Checkout attempt keys do not match.')
    effective_idemp = idempotency_key

    dto = CreateOrderDTO(
        expected_total_minor=payload.expected_total_minor,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        shipping_address_line1=payload.shipping_address_line1,
        shipping_address_line2=payload.shipping_address_line2,
        shipping_city=payload.shipping_city,
        shipping_province=payload.shipping_province,
        shipping_postal_code=payload.shipping_postal_code,
        payment_method=payload.payment_method,
        coupon_code=payload.coupon_code,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        customer_notes=payload.customer_notes,
        idempotency_key=effective_idemp,
        checkout_session_hash=checkout_session_hash,
        items=[
            OrderItemDTO(variant_id=item.variant_id, quantity=item.quantity)
            for item in payload.items
        ],
    )

    try:
        order = place_order(db, dto)
        access_code, session_token = issue_access(db, order)
        db.commit()
        db.refresh(order)
    except CheckoutAttemptConflict as err:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(err)) from err
    except InsufficientStockError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unable to place order: {err}",
        ) from err
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    set_order_session_cookie(response, session_token)
    return OrderCreateResponseSchema(**_order_to_response(order).model_dump(), access_code=access_code)


@router.post('/access', response_model=OrderResponseSchema,
             dependencies=[Depends(require_trusted_origin)])
def access_customer_order(payload: OrderAccessExchangeRequest, request: Request,
                          response: Response, db: Session = Depends(get_db)) -> OrderResponseSchema:
    order = exchange_access_code(db, order_number=payload.order_number,
                                 code=payload.access_code, request=request, response=response)
    return _order_to_response(order)


@router.get('/{order_number}/exchange-options/{line_id}')
def exchange_options(order_number: str, line_id: uuid.UUID, request: Request,
                     db: Session = Depends(get_db)) -> list[dict]:
    order = require_order_access(db, request, order_number=order_number)
    line = next((item for item in order.lines if item.id == line_id and item.fulfillment_kind == 'original'), None)
    if line is None:
        raise HTTPException(404, 'Order access unavailable')
    variants = db.scalars(select(Variant).where(Variant.product_id == line.variant.product_id,
        Variant.id != line.variant_id, Variant.is_active.is_(True)).order_by(Variant.id)).all()
    return [{'id': v.id, 'size': v.size, 'color': v.color, 'sku': v.sku} for v in variants]


@router.post(
    "/{order_number}/receipt",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Upload bank transfer payment proof",
    dependencies=[Depends(require_trusted_origin)],
)
def upload_order_receipt(
    order_number: str,
    payload: PaymentReceiptUploadRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    order = require_order_access(db, request, order_number=order_number)

    if order.payment_method != "bank_transfer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt upload is only applicable for Bank Transfer orders.",
        )

    upload_payment_receipt(
        db,
        order_id=order.id,
        receipt_image_url=payload.receipt_image_url,
        bank_reference=payload.bank_reference,
    )
    db.commit()
    db.refresh(order)

    return _order_to_response(order)


@router.get(
    "/{order_number}",
    response_model=OrderResponseSchema,
    summary="Track order status with an order-scoped session",
)
def track_order(
    order_number: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    order = require_order_access(db, request, order_number=order_number)
    return _order_to_response(order)
