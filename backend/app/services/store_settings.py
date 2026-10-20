"""Service layer for store settings, policies, audit history, and owner preferences."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.store_settings import StoreSettings, StoreSettingsAuditLog, OwnerPreference
from app.models.media import MediaAsset
from app.schemas.store_settings import (
    AdminStoreSettingsResponse,
    PublicStoreSettingsResponse,
    UpdateStoreSettingsRequest,
    UpdateOwnerPreferencesRequest,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_logo_url(logo_media_id: str | None, db: Session) -> str | None:
    if not logo_media_id:
        return None
    asset = db.get(MediaAsset, logo_media_id)
    if asset and asset.state == 'ready':
        return f'/api/v1/media/{asset.id}/content'
    return None


def get_or_create_store_settings(db: Session) -> StoreSettings:
    settings = db.scalar(select(StoreSettings).order_by(StoreSettings.version.desc()))
    if settings is None:
        settings = StoreSettings(
            brand_name='AlphaZee',
            tagline='Modern Apparel & Curated Essentials',
            announcement_banner_enabled=True,
            announcement_banner_text='AlphaZee Concept Preview • Public ordering is not open yet',
            accent_color='#111827',
            font_family='Inter, sans-serif',
            border_radius='md',
            spacing_density='comfortable',
            section_order=['hero', 'collections', 'featured', 'reassurance', 'faq'],
            shipping_coverage_area='All Pakistan',
            standard_shipping_fee_minor=20000,
            low_stock_threshold=3,
            stock_staleness_threshold_days=7,
            version=1,
            updated_at=utcnow(),
        )
        db.add(settings)
        db.flush()
    return settings


def get_public_store_settings(db: Session) -> PublicStoreSettingsResponse:
    settings = get_or_create_store_settings(db)
    logo_url = _resolve_logo_url(settings.logo_media_id, db)
    return PublicStoreSettingsResponse(
        brand_name=settings.brand_name,
        tagline=settings.tagline,
        announcement_banner_enabled=settings.announcement_banner_enabled,
        announcement_banner_text=settings.announcement_banner_text,
        announcement_banner_link=settings.announcement_banner_link,
        logo_url=logo_url,
        accent_color=settings.accent_color,
        font_family=settings.font_family,
        border_radius=settings.border_radius,
        spacing_density=settings.spacing_density,
        section_order=list(settings.section_order or []),
        support_email=settings.support_email,
        support_phone=settings.support_phone,
        support_hours=settings.support_hours,
        delivery_policy=settings.delivery_policy_content if settings.delivery_policy_status == 'published' else None,
        return_policy=settings.return_policy_content if settings.return_policy_status == 'published' else None,
        terms_policy=settings.terms_policy_content if settings.terms_policy_status == 'published' else None,
        privacy_policy=settings.privacy_policy_content if settings.privacy_policy_status == 'published' else None,
        shipping_coverage_area=settings.shipping_coverage_area,
        standard_shipping_fee_minor=settings.standard_shipping_fee_minor,
        free_shipping_threshold_minor=settings.free_shipping_threshold_minor,
    )


def get_admin_store_settings(db: Session) -> AdminStoreSettingsResponse:
    settings = get_or_create_store_settings(db)
    logo_url = _resolve_logo_url(settings.logo_media_id, db)
    return AdminStoreSettingsResponse(
        id=settings.id,
        brand_name=settings.brand_name,
        tagline=settings.tagline,
        announcement_banner_enabled=settings.announcement_banner_enabled,
        announcement_banner_text=settings.announcement_banner_text,
        announcement_banner_link=settings.announcement_banner_link,
        logo_media_id=settings.logo_media_id,
        logo_url=logo_url,
        accent_color=settings.accent_color,
        font_family=settings.font_family,
        border_radius=settings.border_radius,
        spacing_density=settings.spacing_density,
        section_order=list(settings.section_order or []),
        support_email=settings.support_email,
        support_phone=settings.support_phone,
        support_hours=settings.support_hours,
        delivery_policy_content=settings.delivery_policy_content,
        delivery_policy_status=settings.delivery_policy_status,
        delivery_policy_published_at=settings.delivery_policy_published_at,
        return_policy_content=settings.return_policy_content,
        return_policy_status=settings.return_policy_status,
        return_policy_published_at=settings.return_policy_published_at,
        terms_policy_content=settings.terms_policy_content,
        terms_policy_status=settings.terms_policy_status,
        terms_policy_published_at=settings.terms_policy_published_at,
        privacy_policy_content=settings.privacy_policy_content,
        privacy_policy_status=settings.privacy_policy_status,
        privacy_policy_published_at=settings.privacy_policy_published_at,
        shipping_coverage_area=settings.shipping_coverage_area,
        standard_shipping_fee_minor=settings.standard_shipping_fee_minor,
        free_shipping_threshold_minor=settings.free_shipping_threshold_minor,
        low_stock_threshold=settings.low_stock_threshold,
        stock_staleness_threshold_days=settings.stock_staleness_threshold_days,
        version=settings.version,
        updated_at=settings.updated_at,
        updated_by_user_id=settings.updated_by_user_id,
    )


def update_store_settings(
    db: Session,
    user_id: uuid.UUID,
    req: UpdateStoreSettingsRequest,
) -> AdminStoreSettingsResponse:
    settings = get_or_create_store_settings(db)
    req_dict = req.model_dump(exclude_unset=True)
    change_reason = req_dict.pop('change_reason', None)

    if not req_dict:
        return get_admin_store_settings(db)

    # Validate logo_media_id if provided
    if 'logo_media_id' in req_dict and req_dict['logo_media_id'] is not None:
        asset = db.get(MediaAsset, req_dict['logo_media_id'])
        if asset is None or asset.state != 'ready':
            raise ValueError(f"Media asset '{req_dict['logo_media_id']}' not found or not ready")

    changed_fields: dict[str, Any] = {}
    for key, value in req_dict.items():
        old_val = getattr(settings, key)
        if old_val != value:
            changed_fields[key] = {'old': old_val, 'new': value}
            setattr(settings, key, value)

    if changed_fields:
        settings.version += 1
        settings.updated_at = utcnow()
        settings.updated_by_user_id = user_id

        # Build snapshot for audit log
        snapshot = {
            'brand_name': settings.brand_name,
            'tagline': settings.tagline,
            'announcement_banner_enabled': settings.announcement_banner_enabled,
            'announcement_banner_text': settings.announcement_banner_text,
            'accent_color': settings.accent_color,
            'font_family': settings.font_family,
            'border_radius': settings.border_radius,
            'spacing_density': settings.spacing_density,
            'shipping_coverage_area': settings.shipping_coverage_area,
            'standard_shipping_fee_minor': settings.standard_shipping_fee_minor,
            'free_shipping_threshold_minor': settings.free_shipping_threshold_minor,
            'low_stock_threshold': settings.low_stock_threshold,
            'stock_staleness_threshold_days': settings.stock_staleness_threshold_days,
        }
        audit_log = StoreSettingsAuditLog(
            version=settings.version,
            changed_fields=changed_fields,
            full_snapshot=snapshot,
            changed_by_user_id=user_id,
            change_reason=change_reason,
            created_at=utcnow(),
        )
        db.add(audit_log)
        db.flush()

    return get_admin_store_settings(db)


def publish_policy(
    db: Session,
    user_id: uuid.UUID,
    policy_type: str,
    publish: bool,
) -> AdminStoreSettingsResponse:
    if policy_type not in {'delivery', 'return', 'terms', 'privacy'}:
        raise ValueError(f"Invalid policy type '{policy_type}'. Must be delivery, return, terms, or privacy.")

    settings = get_or_create_store_settings(db)
    status_field = f'{policy_type}_policy_status'
    pub_at_field = f'{policy_type}_policy_published_at'
    content_field = f'{policy_type}_policy_content'

    content = getattr(settings, content_field)
    if publish and not (content and content.strip()):
        raise ValueError(f"Cannot publish empty {policy_type} policy. Content is required.")

    old_status = getattr(settings, status_field)
    new_status = 'published' if publish else 'draft'

    if old_status != new_status:
        setattr(settings, status_field, new_status)
        if publish:
            setattr(settings, pub_at_field, utcnow())
        settings.version += 1
        settings.updated_at = utcnow()
        settings.updated_by_user_id = user_id

        audit_log = StoreSettingsAuditLog(
            version=settings.version,
            changed_fields={
                status_field: {'old': old_status, 'new': new_status},
                pub_at_field: {'published': publish},
            },
            full_snapshot={'action': f'Policy {policy_type} set to {new_status}'},
            changed_by_user_id=user_id,
            change_reason=f'Policy {policy_type} status set to {new_status}',
            created_at=utcnow(),
        )
        db.add(audit_log)
        db.flush()

    return get_admin_store_settings(db)


def get_audit_logs(db: Session, limit: int = 50) -> list[StoreSettingsAuditLog]:
    return list(db.scalars(
        select(StoreSettingsAuditLog)
        .order_by(desc(StoreSettingsAuditLog.created_at))
        .limit(limit)
    ).all())


DEFAULT_NAV_ORDER = [
    'products', 'collections', 'hero', 'media', 'inventory',
    'suppliers', 'orders', 'returns', 'coupons', 'expenses',
    'analytics', 'settings'
]

DEFAULT_DASHBOARD_LAYOUT = {
    'cards': [
        {'id': 'sales', 'visible': True},
        {'id': 'inventory', 'visible': True},
        {'id': 'liabilities', 'visible': True},
        {'id': 'expenses', 'visible': True},
    ]
}


def get_or_create_owner_preferences(db: Session, user_id: uuid.UUID) -> OwnerPreference:
    pref = db.get(OwnerPreference, user_id)
    if pref is None:
        pref = OwnerPreference(
            user_id=user_id,
            theme='system',
            table_density='comfortable',
            default_date_range='this_month',
            nav_order=list(DEFAULT_NAV_ORDER),
            dashboard_layout=dict(DEFAULT_DASHBOARD_LAYOUT),
            updated_at=utcnow(),
        )
        db.add(pref)
        db.flush()
    return pref


def update_owner_preferences(
    db: Session,
    user_id: uuid.UUID,
    req: UpdateOwnerPreferencesRequest,
) -> OwnerPreference:
    pref = get_or_create_owner_preferences(db, user_id)
    req_dict = req.model_dump(exclude_unset=True)
    for key, value in req_dict.items():
        setattr(pref, key, value)
    pref.updated_at = utcnow()
    db.flush()
    return pref


def reset_owner_preferences(db: Session, user_id: uuid.UUID) -> OwnerPreference:
    pref = get_or_create_owner_preferences(db, user_id)
    pref.theme = 'system'
    pref.table_density = 'comfortable'
    pref.default_date_range = 'this_month'
    pref.nav_order = list(DEFAULT_NAV_ORDER)
    pref.dashboard_layout = dict(DEFAULT_DASHBOARD_LAYOUT)
    pref.updated_at = utcnow()
    db.flush()
    return pref
