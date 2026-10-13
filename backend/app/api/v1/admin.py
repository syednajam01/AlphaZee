"""
Owner administrative routes for AlphaZee API (v1).

Handles:
- Inventory summary and stock metrics (Physical | Held | Available).
- Concurrency-guarded physical inventory adjustments.
- Order management, manual payment verification, dispatch/delivery, and cancellation.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.v1.orders import _order_to_response
from app.database import get_db
from app.models.catalog import Variant
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.orders import Order
from app.models.suppliers import Supplier, UserAccount
from app.queries.inventory import StaleInventoryError, adjust_inventory
from app.queries.reservations import InsufficientStockError, get_inventory_summary as get_stock_summary
from app.schemas.admin import (
    AdminOrderListResponse,
    AdminOverviewMetricsResponse,
    CodRemittanceRequest,
    InventoryAdjustRequest,
    InventoryMetricResponse,
    InventorySummaryResponse,
    MarketingAttributionItemSchema,
    MarketingAttributionResponseSchema,
    OrderRtoInitiateRequest,
    ProfitLossResponseSchema,
    RtoInspectionRequest,
    RtoReceivedRequest,
    LegacyShipmentReconcileRequest,
    ShipmentAdminResponseSchema,
    ShipmentCreateRequest,
    ShipmentStatusUpdateRequest,
    SupplierCreateRequest,
    SupplierListResponse,
    SupplierResponseSchema,
    SupplierVariantAssignRequest,
    SupplierVariantResponseSchema,
    SupplierAcceptanceRequest,
    PaymentInstructionsSentRequest,
    PaymentReviewResolutionRequest,
)
from app.schemas.catalog import CurrencyAmount
from app.schemas.orders import OrderResponseSchema
from app.schemas.promotions import CouponCreateRequest, CouponResponseSchema
from app.schemas.returns import (
    OrderReturnApproveRequest,
    OrderReturnCompleteRequest,
    OrderReturnReceiveRequest,
    OrderReturnInspectRequest,
    OrderReturnResponseSchema,
)
from app.services.analytics import get_marketing_attribution_summary, get_profit_loss_summary
from app.services.orders import (
    OrderNotCancellableError,
    mark_expired_bank_orders_for_review,
    cancel_order,
    confirm_supplier_acceptance,
    deliver_order,
    preview_bank_instructions,
    record_payment_instructions_sent,
    resolve_payment_review,
    verify_bank_payment,
)
from app.services.promotions import create_coupon, delete_coupon, list_coupons
from app.services.returns import (
    approve_return_request,
    complete_return_and_restock,
    receive_return_items,
    inspect_return_items,
    list_order_returns,
    reject_return_request,
)
from app.services.shipments import (
    OrderNotDispatchableError,
    InvalidRemittanceError,
    ShipmentError,
    ShipmentNotFoundError,
    create_shipment,
    initiate_rto_order,
    inspect_and_restock_order,
    mark_cod_remitted,
    receive_rto_parcel,
    record_cod_remittance,
    update_shipment_status,
    preview_legacy_stock,
    reconcile_legacy_stock,
)
from app.dependencies.auth import OwnerPrincipal, require_owner_session

router = APIRouter(
    prefix="/admin",
    tags=["Owner Administration"],
    dependencies=[Depends(require_owner_session)],
)


@router.get(
    "/inventory/summary",
    response_model=InventorySummaryResponse,
    summary="Get real-time inventory metrics across all active supplier variants",
)
def get_inventory_summary_endpoint(db: Session = Depends(get_db)) -> InventorySummaryResponse:
    stmt = (
        select(SupplierVariant)
        .where(SupplierVariant.active.is_(True))
        .options(
            joinedload(SupplierVariant.variant),
        )
    )
    supplier_variants = db.scalars(stmt).unique().all()

    items = []
    for sv in supplier_variants:
        summary = get_stock_summary(db, sv.id)
        balance = db.get(InventoryBalance, sv.id)
        variant = sv.variant
        product = variant.product if variant else None

        items.append(
            InventoryMetricResponse(
                supplier_variant_id=sv.id,
                variant_id=sv.variant_id,
                product_title=product.title if product else "Unknown Product",
                sku=variant.sku if variant else "UNKNOWN",
                size=variant.size if variant else None,
                color=variant.color if variant else None,
                physical_on_hand=summary.physical,
                held_reservations=summary.held,
                available_to_sell=summary.available,
                version=balance.version if balance else 1,
            )
        )

    return InventorySummaryResponse(
        items=items,
        total_variants=len(items),
    )



@router.post(
    "/inventory/adjust",
    response_model=InventoryMetricResponse,
    status_code=status.HTTP_200_OK,
    summary="Adjust physical inventory with optimistic concurrency check",
)
def adjust_inventory_endpoint(
    payload: InventoryAdjustRequest,
    db: Session = Depends(get_db),
    principal: OwnerPrincipal = Depends(require_owner_session),
) -> InventoryMetricResponse:
    current_balance = db.get(InventoryBalance, payload.supplier_variant_id)
    if current_balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory balance not found for supplier variant {payload.supplier_variant_id}",
        )

    new_on_hand = current_balance.on_hand + payload.quantity_delta
    if new_on_hand < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment would result in negative stock ({new_on_hand})",
        )

    try:
        _event = adjust_inventory(
            db,
            supplier_variant_id=payload.supplier_variant_id,
            actor_user_id=principal.owner.user_id,
            new_on_hand=new_on_hand,
            reason=payload.reason,
            expected_version=payload.expected_version,
            notes=payload.reference_id,
        )
        db.commit()
    except StaleInventoryError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inventory was modified concurrently: {err}",
        ) from err
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    summary = get_stock_summary(db, payload.supplier_variant_id)
    balance = db.get(InventoryBalance, payload.supplier_variant_id)
    sv = db.get(SupplierVariant, payload.supplier_variant_id)
    variant = sv.variant if sv else None
    product = variant.product if variant else None

    return InventoryMetricResponse(
        supplier_variant_id=payload.supplier_variant_id,
        variant_id=sv.variant_id if sv else 0,
        product_title=product.title if product else "Unknown Product",
        sku=variant.sku if variant else "UNKNOWN",
        size=variant.size if variant else None,
        color=variant.color if variant else None,
        physical_on_hand=summary.physical,
        held_reservations=summary.held,
        available_to_sell=summary.available,
        version=balance.version if balance else 1,
    )


@router.get(
    "/orders",
    response_model=AdminOrderListResponse,
    summary="List all customer orders with status filtering and pagination",
)
def list_admin_orders(
    order_status: Optional[str] = Query(None, description="Filter by status: placed, confirmed, delivered, cancelled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminOrderListResponse:
    base_stmt = select(Order)
    if order_status:
        base_stmt = base_stmt.where(Order.order_status == order_status.strip().lower())

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.scalar(count_stmt) or 0

    stmt = (
        base_stmt.order_by(Order.placed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = db.scalars(stmt).unique().all()

    return AdminOrderListResponse(
        orders=[_order_to_response(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/orders/{order_id}/verify-payment",
    response_model=OrderResponseSchema,
    summary="Owner verifies received bank transfer payment funds",
)
def verify_payment_endpoint(
    order_id: uuid.UUID,
    receipt_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    principal: OwnerPrincipal = Depends(require_owner_session),
) -> OrderResponseSchema:
    try:
        order = verify_bank_payment(
            db,
            order_id=order_id,
            verified_by_user_id=principal.owner.user_id,
            receipt_id=receipt_id,
        )
        db.commit()
        db.refresh(order)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return _order_to_response(order)


@router.post(
    "/orders/{order_id}/confirm-supplier",
    response_model=OrderResponseSchema,
    summary="Record operational supplier acceptance and allocate inventory for fulfillment",
)
def confirm_supplier_endpoint(
    order_id: uuid.UUID,
    payload: Optional[SupplierAcceptanceRequest] = None,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    notes = payload.notes if payload else None
    try:
        order = confirm_supplier_acceptance(
            db,
            order_id=order_id,
            supplier_notes=notes,
        )
        db.commit()
        db.refresh(order)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return _order_to_response(order)


@router.get('/orders/{order_id}/payment-instructions-preview')
def payment_instructions_preview_endpoint(order_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    try:
        return preview_bank_instructions(db, order_id)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post('/orders/{order_id}/instructions-sent', response_model=OrderResponseSchema)
def instructions_sent_endpoint(order_id: uuid.UUID, payload: PaymentInstructionsSentRequest,
                               db: Session = Depends(get_db),
                               principal: OwnerPrincipal = Depends(require_owner_session)) -> OrderResponseSchema:
    try:
        order = record_payment_instructions_sent(db, order_id=order_id,
            actor_user_id=principal.owner.user_id, channel=payload.channel, reference=payload.reference)
        db.commit()
        db.refresh(order)
        return _order_to_response(order)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post('/orders/review-expired', summary='Flag expired unpaid bank transfers for owner review')
def review_expired_orders_endpoint(
    db: Session = Depends(get_db),
) -> dict:
    review_orders = mark_expired_bank_orders_for_review(db)
    db.commit()
    return {
        'review_count': len(review_orders),
        'review_order_ids': [str(order.id) for order in review_orders],
    }


@router.post('/orders/{order_id}/payment-review', response_model=OrderResponseSchema)
def resolve_payment_review_endpoint(order_id: uuid.UUID, payload: PaymentReviewResolutionRequest,
                                    db: Session = Depends(get_db),
                                    principal: OwnerPrincipal = Depends(require_owner_session)) -> OrderResponseSchema:
    try:
        order = resolve_payment_review(db, order_id=order_id,
            actor_user_id=principal.owner.user_id, resolution=payload.resolution,
            funds_checked=payload.funds_checked, note=payload.note)
        db.commit()
        db.refresh(order)
        return _order_to_response(order)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post(
    "/orders/{order_id}/deliver",
    response_model=OrderResponseSchema,
    summary="Mark order as delivered, fulfilling reservations and decrementing inventory",
)
def deliver_order_endpoint(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    try:
        order = deliver_order(db, order_id=order_id)
        db.commit()
        db.refresh(order)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return _order_to_response(order)


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponseSchema,
    summary="Cancel order and immediately release all held reservations",
)
def cancel_order_endpoint(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    try:
        order = cancel_order(db, order_id=order_id)
        db.commit()
        db.refresh(order)
    except OrderNotCancellableError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return _order_to_response(order)


@router.post(
    "/orders/{order_id}/rto",
    response_model=OrderResponseSchema,
    summary="Initiate RTO return for a dispatched order in transit with courier",
)
def initiate_rto_endpoint(
    order_id: uuid.UUID,
    payload: Optional[OrderRtoInitiateRequest] = None,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    reason = payload.reason if payload else None
    courier_cost = payload.rto_courier_cost_minor if payload else 0
    try:
        shipment = initiate_rto_order(
            db,
            order_id=order_id,
            rto_reason=reason,
            rto_courier_cost_minor=courier_cost,
        )
        db.commit()
        db.refresh(shipment.order)
        return _order_to_response(shipment.order)
    except OrderNotDispatchableError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except ShipmentError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/orders/{order_id}/rto-received",
    response_model=OrderResponseSchema,
    summary="Record received RTO quantities in quarantine",
)
def receive_rto_endpoint(
    order_id: uuid.UUID,
    payload: RtoReceivedRequest,
    db: Session = Depends(get_db),
) -> OrderResponseSchema:
    try:
        received = {line.order_line_id: line.received_quantity for line in payload.lines}
        if len(received) != len(payload.lines):
            raise ShipmentError('Each order line must appear once in the receipt.')
        shipment = receive_rto_parcel(db, order_id=order_id, received_quantities=received)
        db.commit()
        db.refresh(shipment.order)
        return _order_to_response(shipment.order)
    except ShipmentError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/orders/{order_id}/rto-inspect",
    response_model=OrderResponseSchema,
    summary="Record physical condition inspection and restock resalable RTO inventory",
)
def inspect_rto_endpoint(
    order_id: uuid.UUID,
    payload: RtoInspectionRequest,
    db: Session = Depends(get_db),
    principal: OwnerPrincipal = Depends(require_owner_session),
) -> OrderResponseSchema:
    try:
        lines = {line.order_line_id: (line.sellable_quantity, line.damaged_quantity)
                 for line in payload.lines}
        if len(lines) != len(payload.lines):
            raise ShipmentError('Each order line must appear once in the inspection.')
        shipment = inspect_and_restock_order(
            db,
            order_id=order_id,
            lines=lines,
            notes=payload.notes,
            actor_user_id=principal.owner.user_id,
        )
        db.commit()
        db.refresh(shipment.order)
        return _order_to_response(shipment.order)
    except ShipmentError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err




@router.get(
    "/overview",
    response_model=AdminOverviewMetricsResponse,
    summary="Get high-level business metrics for owner dashboard",
)
def get_admin_overview(db: Session = Depends(get_db)) -> AdminOverviewMetricsResponse:
    # 1. Total Gross Revenue (Verified payments)
    rev_stmt = select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.payment_status == "verified")
    gross_rev_minor = db.scalar(rev_stmt) or 0

    # 2. Orders breakdown
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    pending_orders = db.scalar(select(func.count(Order.id)).where(Order.order_status == "placed")) or 0
    confirmed_orders = db.scalar(select(func.count(Order.id)).where(Order.order_status == "confirmed")) or 0
    delivered_orders = db.scalar(select(func.count(Order.id)).where(Order.order_status == "delivered")) or 0

    # 3. Catalog inventory summary & low stock (< 3 units available)
    sv_stmt = select(SupplierVariant).where(SupplierVariant.active.is_(True))
    active_svs = db.scalars(sv_stmt).all()
    total_skus = len(active_svs)
    low_stock_count = 0
    for sv in active_svs:
        sumry = get_stock_summary(db, sv.id)
        if sumry.available <= 2:
            low_stock_count += 1

    formatted_rev = (
        f"PKR {gross_rev_minor // 100:,}"
        if gross_rev_minor % 100 == 0
        else f"PKR {gross_rev_minor / 100:,.2f}"
    )

    return AdminOverviewMetricsResponse(
        gross_revenue_minor=gross_rev_minor,
        formatted_gross_revenue=formatted_rev,
        total_orders=total_orders,
        pending_orders=pending_orders,
        confirmed_orders=confirmed_orders,
        delivered_orders=delivered_orders,
        total_skus=total_skus,
        low_stock_skus=low_stock_count,
    )


@router.get(
    "/suppliers",
    response_model=SupplierListResponse,
    summary="List all registered suppliers",
)
def list_suppliers_endpoint(db: Session = Depends(get_db)) -> SupplierListResponse:
    stmt = select(Supplier).order_by(Supplier.name.asc())
    suppliers = db.scalars(stmt).all()
    return SupplierListResponse(
        suppliers=[
            SupplierResponseSchema(
                id=s.id,
                name=s.name,
                slug=s.slug,
                status=s.status,
                notes=s.notes,
            )
            for s in suppliers
        ],
        total=len(suppliers),
    )


@router.post(
    "/suppliers",
    response_model=SupplierResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new supplier",
)
def create_supplier_endpoint(
    payload: SupplierCreateRequest,
    db: Session = Depends(get_db),
) -> SupplierResponseSchema:
    existing = db.scalars(select(Supplier).where(Supplier.slug == payload.slug.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Supplier slug {payload.slug!r} is already in use.",
        )

    try:
        supplier = Supplier(
            name=payload.name.strip(),
            slug=payload.slug.strip(),
            status=payload.status.strip(),
            notes=payload.notes.strip() if payload.notes else None,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return SupplierResponseSchema(
        id=supplier.id,
        name=supplier.name,
        slug=supplier.slug,
        status=supplier.status,
        notes=supplier.notes,
    )


@router.post(
    "/suppliers/{supplier_id}/variants",
    response_model=SupplierVariantResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Assign a catalog variant to a supplier and set wholesale cost",
)
def assign_supplier_variant_endpoint(
    supplier_id: uuid.UUID,
    payload: SupplierVariantAssignRequest,
    db: Session = Depends(get_db),
) -> SupplierVariantResponseSchema:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier {supplier_id} not found.",
        )

    variant = db.get(Variant, payload.variant_id)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant {payload.variant_id} not found in catalog.",
        )

    # If setting as active, deactivate other supplier variants for this variant_id
    if payload.active:
        stmt = (
            select(SupplierVariant)
            .where(
                SupplierVariant.variant_id == payload.variant_id,
                SupplierVariant.active.is_(True),
            )
        )
        existing_actives = db.scalars(stmt).all()
        for sv in existing_actives:
            if sv.supplier_id != supplier_id:
                sv.active = False

    # Check if a link already exists between this supplier and variant
    existing_sv = db.scalars(
        select(SupplierVariant).where(
            SupplierVariant.supplier_id == supplier_id,
            SupplierVariant.variant_id == payload.variant_id,
        )
    ).first()

    if existing_sv:
        existing_sv.supplier_cost_minor = payload.supplier_cost_minor
        existing_sv.active = payload.active
        target_sv = existing_sv
    else:
        target_sv = SupplierVariant(
            supplier_id=supplier_id,
            variant_id=payload.variant_id,
            supplier_cost_minor=payload.supplier_cost_minor,
            active=payload.active,
        )
        db.add(target_sv)
        db.flush()

        # Ensure an inventory balance exists
        bal = db.get(InventoryBalance, target_sv.id)
        if not bal:
            bal = InventoryBalance(supplier_variant_id=target_sv.id, on_hand=0, version=1)
            db.add(bal)

    db.commit()
    db.refresh(target_sv)

    return SupplierVariantResponseSchema(
        id=target_sv.id,
        supplier_id=target_sv.supplier_id,
        variant_id=target_sv.variant_id,
        supplier_cost_minor=target_sv.supplier_cost_minor or 0,
        active=target_sv.active,
    )


@router.post(
    "/orders/{order_id}/dispatch",
    response_model=ShipmentAdminResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch an order via courier with tracking number and shipping cost",
)
def dispatch_order_endpoint(
    order_id: uuid.UUID,
    payload: ShipmentCreateRequest,
    db: Session = Depends(get_db),
    principal: OwnerPrincipal = Depends(require_owner_session),
) -> ShipmentAdminResponseSchema:
    try:
        shipment = create_shipment(
            db,
            order_id=order_id,
            courier_code=payload.courier_code,
            tracking_number=payload.tracking_number,
            shipping_cost_minor=payload.shipping_cost_minor,
            tracking_url=payload.tracking_url,
            actor_user_id=principal.owner.user_id,
        )
        db.commit()
        db.refresh(shipment)
        return ShipmentAdminResponseSchema.model_validate(shipment)
    except ShipmentError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post(
    "/shipments/{shipment_id}/status",
    response_model=ShipmentAdminResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update courier shipment delivery status or record RTO return",
)
def update_shipment_status_endpoint(
    shipment_id: uuid.UUID,
    payload: ShipmentStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> ShipmentAdminResponseSchema:
    try:
        if payload.received_lines is not None and len({line.order_line_id for line in payload.received_lines}) != len(payload.received_lines):
            raise ShipmentError('Each order line must appear once in the receipt.')
        shipment = update_shipment_status(
            db,
            shipment_id=shipment_id,
            status=payload.status,
            rto_reason=payload.rto_reason,
            rto_courier_cost_minor=payload.rto_courier_cost_minor,
            received_quantities=({line.order_line_id: line.received_quantity
                                  for line in payload.received_lines}
                                 if payload.received_lines is not None else None),
        )
        db.commit()
        db.refresh(shipment)
        return ShipmentAdminResponseSchema.model_validate(shipment)
    except ShipmentNotFoundError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (ShipmentError, ValueError) as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get('/shipments/{shipment_id}/stock-reconciliation')
def preview_legacy_stock_endpoint(shipment_id: uuid.UUID,
                                  db: Session = Depends(get_db)) -> dict:
    try:
        return preview_legacy_stock(db, shipment_id)
    except ShipmentError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post('/shipments/{shipment_id}/stock-reconciliation',
             response_model=ShipmentAdminResponseSchema)
def reconcile_legacy_stock_endpoint(shipment_id: uuid.UUID,
                                    payload: LegacyShipmentReconcileRequest,
                                    db: Session = Depends(get_db),
                                    principal: OwnerPrincipal = Depends(require_owner_session)) -> ShipmentAdminResponseSchema:
    decisions = {line.reservation_id: (line.physical_deducted, line.received_quantity)
                 for line in payload.lines}
    if len(decisions) != len(payload.lines):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Each reservation must appear once.')
    try:
        shipment = reconcile_legacy_stock(db, shipment_id=shipment_id,
            decisions=decisions, note=payload.note, actor_user_id=principal.owner.user_id)
        db.commit()
        db.refresh(shipment)
        return ShipmentAdminResponseSchema.model_validate(shipment)
    except (ShipmentError, ValueError) as error:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post(
    "/shipments/{shipment_id}/remittance",
    response_model=ShipmentAdminResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Record courier COD cash remittance into bank account",
)
def record_cod_remittance_endpoint(
    shipment_id: uuid.UUID,
    payload: CodRemittanceRequest,
    db: Session = Depends(get_db),
) -> ShipmentAdminResponseSchema:
    try:
        shipment = record_cod_remittance(
            db,
            shipment_id=shipment_id,
            remitted_amount_minor=payload.remitted_amount_minor,
            reference=payload.reference,
            is_partial=payload.is_partial or bool(payload.partial),
            partial_reason=payload.partial_reason,
        )
        db.commit()
        db.refresh(shipment)
        return ShipmentAdminResponseSchema.model_validate(shipment)
    except InvalidRemittanceError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ShipmentNotFoundError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ShipmentError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/orders/{order_id}/remittance",
    response_model=ShipmentAdminResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Record courier COD cash remittance for an order by order ID",
)
def record_order_cod_remittance_endpoint(
    order_id: uuid.UUID,
    payload: CodRemittanceRequest,
    db: Session = Depends(get_db),
) -> ShipmentAdminResponseSchema:
    try:
        shipment = mark_cod_remitted(
            db,
            order_id=order_id,
            amount_minor=payload.remitted_amount_minor,
            reference=payload.reference,
            is_partial=payload.is_partial or bool(payload.partial),
            partial_reason=payload.partial_reason,
        )
        db.commit()
        db.refresh(shipment)
        return ShipmentAdminResponseSchema.model_validate(shipment)
    except InvalidRemittanceError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ShipmentNotFoundError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ShipmentError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/analytics/profit-loss",
    response_model=ProfitLossResponseSchema,
    summary="Get owner gross profit, COGS, courier costs, and unit economics report",
)
def get_profit_loss_endpoint(db: Session = Depends(get_db)) -> ProfitLossResponseSchema:
    data = get_profit_loss_summary(db)

    gross_rev = data["gross_revenue_minor"]
    net_rev = data.get("net_revenue_minor", gross_rev)
    refund_tot = data.get("refund_total_minor", 0)
    gross_prof = data["gross_profit_minor"]

    if net_rev > 0:
        margin_pct = round((gross_prof / net_rev) * 100.0, 2)
    elif gross_rev > 0:
        margin_pct = round((gross_prof / gross_rev) * 100.0, 2)
    else:
        margin_pct = 0.0

    return ProfitLossResponseSchema(
        gross_revenue_minor=gross_rev,
        formatted_gross_revenue=CurrencyAmount.from_minor(gross_rev).formatted,
        net_revenue_minor=net_rev,
        formatted_net_revenue=CurrencyAmount.from_minor(net_rev).formatted,
        refund_total_minor=refund_tot,
        formatted_refund_total=CurrencyAmount.from_minor(refund_tot).formatted,
        subtotal_revenue_minor=data["subtotal_revenue_minor"],
        shipping_revenue_minor=data["shipping_revenue_minor"],
        cogs_minor=data["cogs_minor"],
        formatted_cogs=CurrencyAmount.from_minor(data["cogs_minor"]).formatted,
        outbound_courier_cost_minor=data["outbound_courier_cost_minor"],
        rto_courier_cost_minor=data["rto_courier_cost_minor"],
        total_courier_expenses_minor=data["total_courier_expenses_minor"],
        formatted_courier_expenses=CurrencyAmount.from_minor(data["total_courier_expenses_minor"]).formatted,
        gross_profit_minor=gross_prof,
        formatted_gross_profit=CurrencyAmount.from_minor(gross_prof).formatted,
        gross_margin_percent=margin_pct,
        total_orders_count=data["total_orders_count"],
        total_shipments_count=data["total_shipments_count"],
        delivered_shipments_count=data["delivered_shipments_count"],
        rto_shipments_count=data["rto_shipments_count"],
        rto_rate_percent=data["rto_rate_percent"],
        cod_pending_remittance_minor=data["cod_pending_remittance_minor"],
        cod_remitted_minor=data["cod_remitted_minor"],
    )


@router.get(
    "/analytics/marketing",
    response_model=MarketingAttributionResponseSchema,
    summary="Get marketing UTM campaigns performance and discount breakdown",
)
def get_marketing_attribution_endpoint(
    db: Session = Depends(get_db),
) -> MarketingAttributionResponseSchema:
    channels_raw = get_marketing_attribution_summary(db)
    items = [
        MarketingAttributionItemSchema(
            utm_source=c["utm_source"],
            utm_medium=c["utm_medium"],
            utm_campaign=c["utm_campaign"],
            orders_count=c["orders_count"],
            revenue_minor=c["revenue_minor"],
            formatted_revenue=CurrencyAmount.from_minor(c["revenue_minor"]).formatted,
            discount_minor=c["discount_minor"],
            formatted_discount=CurrencyAmount.from_minor(c["discount_minor"]).formatted,
        )
        for c in channels_raw
    ]
    return MarketingAttributionResponseSchema(
        channels=items,
        total_campaigns=len(items),
    )


# --- Coupon Management ---


@router.get(
    "/coupons",
    response_model=list[CouponResponseSchema],
    summary="List all promotional coupons",
)
def list_admin_coupons_endpoint(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CouponResponseSchema]:
    coupons = list_coupons(db, active_only=active_only)
    return [
        CouponResponseSchema(
            id=c.id,
            code=c.code,
            discount_type=c.discount_type,
            discount_value=c.discount_value,
            min_subtotal=CurrencyAmount.from_minor(c.min_subtotal_minor),
            max_discount=CurrencyAmount.from_minor(c.max_discount_minor) if c.max_discount_minor else None,
            usage_limit=c.usage_limit,
            times_used=c.times_used,
            valid_from=c.valid_from,
            valid_until=c.valid_until,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in coupons
    ]


@router.post(
    "/coupons",
    response_model=CouponResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new promotional discount coupon",
)
def create_admin_coupon_endpoint(
    payload: CouponCreateRequest,
    db: Session = Depends(get_db),
) -> CouponResponseSchema:
    try:
        coupon = create_coupon(
            db,
            code=payload.code,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            min_subtotal_minor=payload.min_subtotal_minor,
            max_discount_minor=payload.max_discount_minor,
            usage_limit=payload.usage_limit,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            is_active=payload.is_active,
        )
        db.commit()
        db.refresh(coupon)
        return CouponResponseSchema(
            id=coupon.id,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            min_subtotal=CurrencyAmount.from_minor(coupon.min_subtotal_minor),
            max_discount=CurrencyAmount.from_minor(coupon.max_discount_minor) if coupon.max_discount_minor else None,
            usage_limit=coupon.usage_limit,
            times_used=coupon.times_used,
            valid_from=coupon.valid_from,
            valid_until=coupon.valid_until,
            is_active=coupon.is_active,
            created_at=coupon.created_at,
        )
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.delete(
    "/coupons/{coupon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a coupon",
)
def delete_admin_coupon_endpoint(
    coupon_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Response:
    deleted = delete_coupon(db, coupon_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon {coupon_id} not found.",
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Order Return & Size Exchange Management ---


@router.get(
    "/returns",
    response_model=list[OrderReturnResponseSchema],
    summary="List all customer return and size exchange requests",
)
def list_admin_returns_endpoint(
    order_id: Optional[uuid.UUID] = Query(default=None),
    return_status: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[OrderReturnResponseSchema]:
    returns = list_order_returns(db, order_id=order_id, status=return_status)
    return [
        OrderReturnResponseSchema.from_return(r)
        for r in returns
    ]


@router.post(
    "/returns/{return_id}/approve",
    response_model=OrderReturnResponseSchema,
    summary="Approve customer return request",
)
def approve_admin_return_endpoint(
    return_id: uuid.UUID,
    payload: Optional[OrderReturnApproveRequest] = None,
    db: Session = Depends(get_db),
) -> OrderReturnResponseSchema:
    refund_minor = payload.refund_amount_minor if payload else None
    try:
        ret = approve_return_request(db, return_id=return_id, refund_amount_minor=refund_minor)
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema.from_return(ret)
    except InsufficientStockError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post('/returns/{return_id}/receive', response_model=OrderReturnResponseSchema)
def receive_admin_return_endpoint(return_id: uuid.UUID, payload: OrderReturnReceiveRequest,
                                  db: Session = Depends(get_db)) -> OrderReturnResponseSchema:
    try:
        ret = receive_return_items(db, return_id=return_id,
                                   received_quantity=payload.received_quantity)
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema.from_return(ret)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post('/returns/{return_id}/inspect', response_model=OrderReturnResponseSchema)
def inspect_admin_return_endpoint(return_id: uuid.UUID, payload: OrderReturnInspectRequest,
                                  db: Session = Depends(get_db),
                                  principal: OwnerPrincipal = Depends(require_owner_session)) -> OrderReturnResponseSchema:
    try:
        ret = inspect_return_items(db, return_id=return_id,
            sellable_quantity=payload.sellable_quantity, damaged_quantity=payload.damaged_quantity,
            notes=payload.notes, actor_user_id=principal.owner.user_id)
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema.from_return(ret)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.post(
    "/returns/{return_id}/complete",
    response_model=OrderReturnResponseSchema,
    summary="Complete return, record bank refund ref, and restock inventory",
)
def complete_admin_return_endpoint(
    return_id: uuid.UUID,
    payload: OrderReturnCompleteRequest,
    db: Session = Depends(get_db),
) -> OrderReturnResponseSchema:
    try:
        ret = complete_return_and_restock(
            db,
            return_id=return_id,
            refund_reference=payload.refund_reference,
            should_restock=payload.should_restock,
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


@router.post(
    "/returns/{return_id}/reject",
    response_model=OrderReturnResponseSchema,
    summary="Reject customer return request",
)
def reject_admin_return_endpoint(
    return_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> OrderReturnResponseSchema:
    try:
        ret = reject_return_request(db, return_id=return_id)
        db.commit()
        db.refresh(ret)
        return OrderReturnResponseSchema.from_return(ret)
    except ValueError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err



