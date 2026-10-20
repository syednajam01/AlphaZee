"""API endpoints for Vendor Stock Portal & Authentication (VS2-VS3)."""
from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.vendor_auth import (
    VendorPrincipal,
    require_vendor_session,
    vendor_cookie_name,
)
from app.models.suppliers import Supplier
from app.models.vendor_portal import VendorSession, VendorUser
from app.queries.inventory import StaleInventoryError
from app.schemas.vendor_portal import (
    ReportShortageRequest,
    VendorAuditHistoryResponse,
    VendorLoginRequest,
    VendorSessionResponse,
    VendorShortageResponse,
    VendorStockCountUpdateRequest,
    VendorStockCountUpdateResponse,
    VendorStockListResponse,
)
from app.services import vendor_portal as vp_service
from app.services.passwords import DUMMY_HASH, verify_password
from app.services.vendor_session_store import (
    consume_vendor_login_attempt,
    csrf_token,
    issue_vendor_session,
    token_hash,
    utcnow,
)

router = APIRouter(
    prefix="/vendor",
    tags=["Vendor Stock Portal"],
)


@router.post(
    "/auth/login",
    response_model=VendorSessionResponse,
    summary="Authenticate vendor user and set session cookie",
)
def vendor_login_endpoint(
    payload: VendorLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> VendorSessionResponse:
    client_ip = request.client.host if request.client else "unknown"
    if consume_vendor_login_attempt(db, payload.username, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 15 minutes before trying again.",
        )

    clean_username = payload.username.strip().lower()
    vendor_user = db.scalar(
        select(VendorUser)
        .where(VendorUser.username == clean_username)
        .with_for_update()
    )

    valid_password = False
    if vendor_user and vendor_user.is_active:
        valid_password = verify_password(payload.password, vendor_user.password_hash)
    else:
        # Constant-time dummy work to prevent timing side-channels
        verify_password(payload.password, DUMMY_HASH)

    if not vendor_user or not vendor_user.is_active or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid vendor username or password",
        )

    vendor = db.get(Supplier, vendor_user.vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor shop record not found.",
        )

    # Issue session
    token, session_obj = issue_vendor_session(db, vendor_user)
    db.commit()

    # Set cookie
    c_name = vendor_cookie_name()
    response.set_cookie(
        key=c_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )

    c_token = csrf_token(token)
    return VendorSessionResponse(
        username=vendor_user.username,
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        vendor_slug=vendor.slug,
        csrf_token=c_token,
        authenticated=True,
    )


@router.get(
    "/auth/session",
    response_model=VendorSessionResponse,
    summary="Validate existing vendor session and return active shop profile",
)
def vendor_session_endpoint(
    principal: VendorPrincipal = Depends(require_vendor_session),
) -> VendorSessionResponse:
    c_token = csrf_token(principal.token)
    return VendorSessionResponse(
        username=principal.vendor_user.username,
        vendor_id=principal.vendor.id,
        vendor_name=principal.vendor.name,
        vendor_slug=principal.vendor.slug,
        csrf_token=c_token,
        authenticated=True,
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke active vendor session and clear cookie",
)
def vendor_logout_endpoint(
    response: Response,
    principal: VendorPrincipal = Depends(require_vendor_session),
    db: Session = Depends(get_db),
):
    principal.session.revoked_at = utcnow()
    db.commit()

    response.delete_cookie(key=vendor_cookie_name(), path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/stock",
    response_model=VendorStockListResponse,
    summary="List paginated products and variants assigned to authenticated vendor",
)
def get_vendor_stock_endpoint(
    search: Optional[str] = Query(None, description="Search by title, SKU, size, or color"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: VendorPrincipal = Depends(require_vendor_session),
    db: Session = Depends(get_db),
) -> VendorStockListResponse:
    items, total = vp_service.get_vendor_stock_list(
        db,
        vendor_id=principal.vendor_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return VendorStockListResponse(
        items=items,
        total_items=total,
        page=(offset // limit) + 1,
        limit=limit,
    )


@router.post(
    "/stock/{variant_id}/count",
    response_model=VendorStockCountUpdateResponse,
    summary="Update vendor allocated on-hand count with optimistic concurrency check",
)
def update_vendor_count_endpoint(
    variant_id: int,
    payload: VendorStockCountUpdateRequest,
    principal: VendorPrincipal = Depends(require_vendor_session),
    db: Session = Depends(get_db),
) -> VendorStockCountUpdateResponse:
    try:
        res = vp_service.update_vendor_counted_quantity(
            db,
            vendor_id=principal.vendor_id,
            vendor_user=principal.vendor_user,
            variant_id=variant_id,
            counted_quantity=payload.counted_quantity,
            expected_version=payload.expected_version,
            reason=payload.reason,
            note=payload.note,
            request_ref=payload.request_ref,
        )
        db.commit()
        return VendorStockCountUpdateResponse(**res)
    except StaleInventoryError as stale_err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(stale_err),
        )
    except ValueError as val_err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )


@router.post(
    "/stock/{variant_id}/shortage",
    response_model=VendorShortageResponse,
    summary="Report stock shortage for an assigned variant",
)
def report_shortage_endpoint(
    variant_id: int,
    payload: ReportShortageRequest,
    principal: VendorPrincipal = Depends(require_vendor_session),
    db: Session = Depends(get_db),
) -> VendorShortageResponse:
    try:
        shortage = vp_service.report_vendor_shortage(
            db,
            vendor_id=principal.vendor_id,
            vendor_user=principal.vendor_user,
            variant_id=variant_id,
            reported_count=payload.reported_count,
            note=payload.note,
        )
        db.commit()
        return VendorShortageResponse(
            id=shortage.id,
            variant_id=shortage.variant_id,
            vendor_id=shortage.vendor_id,
            reported_count=shortage.reported_count,
            held_reservations=shortage.held_reservations,
            physical_on_hand_snapshot=shortage.physical_on_hand_snapshot,
            status=shortage.status,
            notes=shortage.notes,
            reported_at=shortage.reported_at,
            resolved_at=shortage.resolved_at,
            resolution_note=shortage.resolution_note,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/stock/history",
    response_model=VendorAuditHistoryResponse,
    summary="Get recent count update audit events for authenticated vendor",
)
def get_vendor_history_endpoint(
    limit: int = Query(30, ge=1, le=100),
    principal: VendorPrincipal = Depends(require_vendor_session),
    db: Session = Depends(get_db),
) -> VendorAuditHistoryResponse:
    history, total = vp_service.get_vendor_update_history(
        db,
        vendor_id=principal.vendor_id,
        limit=limit,
    )
    return VendorAuditHistoryResponse(
        history=history,
        total=total,
    )
