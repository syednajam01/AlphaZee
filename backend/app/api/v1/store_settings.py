"""API endpoints for store settings, policies, audit history, and owner preferences."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, require_owner_session
from app.schemas.store_settings import (
    AdminStoreSettingsResponse,
    OwnerPreferencesResponse,
    PublicStoreSettingsResponse,
    PublishPolicyRequest,
    StoreSettingsAuditLogItem,
    UpdateOwnerPreferencesRequest,
    UpdateStoreSettingsRequest,
)
from app.services import store_settings as service

public_router = APIRouter(tags=['store-settings'])
admin_router = APIRouter(prefix='/admin', tags=['admin-settings'])


# ── Public Endpoints ──────────────────────────────────────────────────────────

@public_router.get('/store/settings', response_model=PublicStoreSettingsResponse)
def get_public_settings(db: Session = Depends(get_db)):
    """Fetch public-safe store branding, announcement banner, theme tokens, and published policies."""
    return service.get_public_store_settings(db)


# ── Admin Store Settings ──────────────────────────────────────────────────────

@admin_router.get('/settings', response_model=AdminStoreSettingsResponse)
def get_admin_settings(
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Fetch full admin store settings, policies (draft/published), and configuration."""
    return service.get_admin_store_settings(db)


@admin_router.put('/settings', response_model=AdminStoreSettingsResponse)
def update_admin_settings(
    payload: UpdateStoreSettingsRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Update store settings with validation, optimistic version tracking, and audit logging."""
    try:
        updated = service.update_store_settings(db, principal.owner.user_id, payload)
        db.commit()
        return updated
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise


@admin_router.post('/settings/policies/{policy_type}/publish', response_model=AdminStoreSettingsResponse)
def publish_store_policy(
    policy_type: str,
    payload: PublishPolicyRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Publish or unpublish a legal policy (delivery, return, terms, privacy)."""
    try:
        updated = service.publish_policy(db, principal.owner.user_id, policy_type, payload.publish)
        db.commit()
        return updated
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise


@admin_router.get('/settings/audit-logs', response_model=list[StoreSettingsAuditLogItem])
def get_settings_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """View chronological audit log of store settings changes."""
    return service.get_audit_logs(db, limit=limit)


# ── Admin Owner Preferences ───────────────────────────────────────────────────

@admin_router.get('/preferences', response_model=OwnerPreferencesResponse)
def get_preferences(
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Fetch personalized interface preferences for the authenticated owner."""
    pref = service.get_or_create_owner_preferences(db, principal.owner.user_id)
    return pref


@admin_router.put('/preferences', response_model=OwnerPreferencesResponse)
def update_preferences(
    payload: UpdateOwnerPreferencesRequest,
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Update personalized interface preferences (theme, density, date filters, layout)."""
    try:
        pref = service.update_owner_preferences(db, principal.owner.user_id, payload)
        db.commit()
        return pref
    except ValueError as error:
        db.rollback()
        raise HTTPException(400, str(error)) from error


@admin_router.post('/preferences/reset', response_model=OwnerPreferencesResponse)
def reset_preferences(
    principal: OwnerPrincipal = Depends(require_owner_session),
    db: Session = Depends(get_db),
):
    """Reset interface preferences to system defaults for the authenticated owner."""
    pref = service.reset_owner_preferences(db, principal.owner.user_id)
    db.commit()
    return pref
