"""Admin endpoints for provisioning vendor users and managing stock shortages."""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, require_owner_session
from app.schemas.vendor_portal import (
    ProvisionVendorUserRequest,
    ResetVendorPasswordRequest,
    ResolveShortageRequest,
    ToggleVendorUserStatusRequest,
    VendorShortageResponse,
    VendorUserResponse,
)
from app.services import vendor_portal as vp_service

router = APIRouter(
    prefix="/admin",
    tags=["Vendor Administration & Shortages"],
    dependencies=[Depends(require_owner_session)],
)


@router.post(
    "/suppliers/{vendor_id}/users",
    response_model=VendorUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision or update a vendor stock management user",
)
def provision_vendor_user_endpoint(
    vendor_id: uuid.UUID,
    payload: ProvisionVendorUserRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> VendorUserResponse:
    try:
        user = vp_service.provision_vendor_user(
            db,
            vendor_id=vendor_id,
            username=payload.username,
            password=payload.password,
            allow_short_local=payload.allow_short_local,
        )
        db.commit()
        return VendorUserResponse(
            id=user.id,
            user_id=user.user_id,
            vendor_id=user.vendor_id,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/suppliers/{vendor_id}/users",
    response_model=List[VendorUserResponse],
    summary="List all stock management users for a supplier",
)
def list_vendor_users_endpoint(
    vendor_id: uuid.UUID,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> List[VendorUserResponse]:
    users = vp_service.list_vendor_users(db, vendor_id)
    return [
        VendorUserResponse(
            id=u.id,
            user_id=u.user_id,
            vendor_id=u.vendor_id,
            username=u.username,
            is_active=u.is_active,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]


@router.post(
    "/vendor-users/{user_id}/reset-password",
    response_model=VendorUserResponse,
    summary="Reset vendor user password and revoke active sessions",
)
def reset_vendor_password_endpoint(
    user_id: uuid.UUID,
    payload: ResetVendorPasswordRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> VendorUserResponse:
    try:
        user = vp_service.reset_vendor_password(
            db,
            vendor_user_id=user_id,
            password=payload.password,
            allow_short_local=payload.allow_short_local,
        )
        db.commit()
        return VendorUserResponse(
            id=user.id,
            user_id=user.user_id,
            vendor_id=user.vendor_id,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/vendor-users/{user_id}/toggle-status",
    response_model=VendorUserResponse,
    summary="Enable or disable vendor user access",
)
def toggle_vendor_user_status_endpoint(
    user_id: uuid.UUID,
    payload: ToggleVendorUserStatusRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> VendorUserResponse:
    try:
        user = vp_service.toggle_vendor_user_status(
            db,
            vendor_user_id=user_id,
            is_active=payload.is_active,
        )
        db.commit()
        return VendorUserResponse(
            id=user.id,
            user_id=user.user_id,
            vendor_id=user.vendor_id,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/shortages",
    response_model=List[VendorShortageResponse],
    summary="List open vendor stock shortages awaiting owner review",
)
def list_open_shortages_endpoint(
    vendor_id: Optional[uuid.UUID] = Query(None),
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> List[VendorShortageResponse]:
    shortages = vp_service.list_open_shortages(db, vendor_id=vendor_id)
    return [
        VendorShortageResponse(
            id=s.id,
            variant_id=s.variant_id,
            vendor_id=s.vendor_id,
            reported_count=s.reported_count,
            held_reservations=s.held_reservations,
            physical_on_hand_snapshot=s.physical_on_hand_snapshot,
            status=s.status,
            notes=s.notes,
            reported_at=s.reported_at,
            resolved_at=s.resolved_at,
            resolution_note=s.resolution_note,
        )
        for s in shortages
    ]


@router.post(
    "/shortages/{shortage_id}/resolve",
    response_model=VendorShortageResponse,
    summary="Resolve or cancel an open vendor stock shortage",
)
def resolve_shortage_endpoint(
    shortage_id: uuid.UUID,
    payload: ResolveShortageRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
) -> VendorShortageResponse:
    try:
        s = vp_service.resolve_shortage(
            db,
            shortage_id=shortage_id,
            owner_user_id=principal.owner.user_id,
            resolution_action=payload.resolution_action,
            resolution_note=payload.resolution_note,
        )
        db.commit()
        return VendorShortageResponse(
            id=s.id,
            variant_id=s.variant_id,
            vendor_id=s.vendor_id,
            reported_count=s.reported_count,
            held_reservations=s.held_reservations,
            physical_on_hand_snapshot=s.physical_on_hand_snapshot,
            status=s.status,
            notes=s.notes,
            reported_at=s.reported_at,
            resolved_at=s.resolved_at,
            resolution_note=s.resolution_note,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
