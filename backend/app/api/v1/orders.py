"""
Customer order routes for AlphaZee Storefront API (v1).

Handles:
- POST /api/v1/orders: Authoritative order placement and atomic stock reservations.
- POST /api/v1/orders/{order_number}/receipt: Payment proof submission for Bank Transfer orders.
- GET /api/v1/orders/{order_number}: Customer order status and tracking.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.checkout import require_checkout_enabled
from app.dependencies.auth import require_trusted_origin
from app.services.checkout_attempts import mint_checkout_session, require_checkout_session
from app.models.orders import Order, normalize_pakistan_phone
from app.queries.reservations import InsufficientStockError
from app.schemas.catalog import CurrencyAmount
from app.schemas.orders import (
    BankInstructionsSchema,
    OrderCreateRequest,
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


@router.get('/checkout-session', dependencies=[Depends(require_checkout_enabled)])
def start_checkout_session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return mint_checkout_session(request, response)


def _order_to_response(order: Order) -> OrderResponseSchema:
    """Serialize SQLAlchemy Order into detailed Pydantic response."""
    lines = [
        OrderLineResponseSchema(
            id=line.id,
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
    response_model=OrderResponseSchema,
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
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=64,
                                  pattern=r'^[A-Za-z0-9_-]+$'),
    checkout_session_hash: str = Depends(require_checkout_session),
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    if payload.idempotency_key and payload.idempotency_key != idempotency_key:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Checkout attempt keys do not match.')
    effective_idemp = idempotency_key

    dto = CreateOrderDTO(
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

    return _order_to_response(order)


@router.post(
    "/{order_number}/receipt",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Upload bank transfer payment proof",
)
def upload_order_receipt(
    order_number: str,
    payload: PaymentReceiptUploadRequest,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    stmt = select(Order).where(Order.order_number == order_number.strip())
    order = db.scalars(stmt).first()

    if order is None or order.customer_phone != payload.customer_phone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_number!r} not found for this customer phone number.",
        )

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
    summary="Track order status by order number and verified phone",
)
def track_order(
    order_number: str,
    phone: str = Query(..., description="Customer phone number used when placing order"),
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    try:
        clean_phone = normalize_pakistan_phone(phone)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    stmt = (
        select(Order)
        .where(
            Order.order_number == order_number.strip(),
            Order.customer_phone == clean_phone,
        )
        .options(
            selectinload(Order.lines),
            selectinload(Order.receipts),
            selectinload(Order.shipments),
            selectinload(Order.returns),
        )
    )
    order = db.scalars(stmt).first()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_number!r} not found for phone number {clean_phone}.",
        )

    return _order_to_response(order)
