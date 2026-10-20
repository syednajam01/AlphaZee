"""Store settings, policy publication, audit history, and per-owner preferences."""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StoreSettings(Base):
    __tablename__ = 'store_settings'
    __table_args__ = (
        CheckConstraint("delivery_policy_status IN ('draft', 'published')", name='ck_store_settings_delivery_status'),
        CheckConstraint("return_policy_status IN ('draft', 'published')", name='ck_store_settings_return_status'),
        CheckConstraint("terms_policy_status IN ('draft', 'published')", name='ck_store_settings_terms_status'),
        CheckConstraint("privacy_policy_status IN ('draft', 'published')", name='ck_store_settings_privacy_status'),
        CheckConstraint('standard_shipping_fee_minor >= 0', name='ck_store_settings_standard_shipping_non_neg'),
        CheckConstraint('low_stock_threshold >= 0', name='ck_store_settings_low_stock_pos'),
        CheckConstraint('stock_staleness_threshold_days >= 1', name='ck_store_settings_staleness_pos'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Branding & Copy
    brand_name: Mapped[str] = mapped_column(String(100), default='AlphaZee', nullable=False)
    tagline: Mapped[str] = mapped_column(String(255), default='Modern Apparel & Curated Essentials', nullable=False)
    announcement_banner_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    announcement_banner_text: Mapped[str] = mapped_column(
        String(255),
        default='AlphaZee Concept Preview • Public ordering is not open yet',
        nullable=False,
    )
    announcement_banner_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_media_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey('media_assets.id', ondelete='SET NULL'),
        nullable=True,
    )

    # Theme & Curated Presentation Tokens
    accent_color: Mapped[str] = mapped_column(String(32), default='#111827', nullable=False)
    font_family: Mapped[str] = mapped_column(String(64), default='Inter, sans-serif', nullable=False)
    border_radius: Mapped[str] = mapped_column(String(32), default='md', nullable=False)
    spacing_density: Mapped[str] = mapped_column(String(32), default='comfortable', nullable=False)
    section_order: Mapped[list[str]] = mapped_column(
        JSONB,
        default=lambda: ['hero', 'collections', 'featured', 'reassurance', 'faq'],
        nullable=False,
    )

    # Support Contacts
    support_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    support_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    support_hours: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Legal & Policies (Draft vs Published)
    delivery_policy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_policy_status: Mapped[str] = mapped_column(String(20), default='draft', nullable=False)
    delivery_policy_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_policy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_policy_status: Mapped[str] = mapped_column(String(20), default='draft', nullable=False)
    return_policy_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    terms_policy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_policy_status: Mapped[str] = mapped_column(String(20), default='draft', nullable=False)
    terms_policy_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    privacy_policy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy_policy_status: Mapped[str] = mapped_column(String(20), default='draft', nullable=False)
    privacy_policy_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Shipping & Operations Rules
    shipping_coverage_area: Mapped[str] = mapped_column(String(100), default='All Pakistan', nullable=False)
    standard_shipping_fee_minor: Mapped[int] = mapped_column(Integer, default=20000, nullable=False)  # PKR 200
    free_shipping_threshold_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g. PKR 5,000 = 500000
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    stock_staleness_threshold_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)

    # Versioning & Audit
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('user_accounts.id', ondelete='SET NULL'),
        nullable=True,
    )


class StoreSettingsAuditLog(Base):
    __tablename__ = 'store_settings_audit_logs'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    changed_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    full_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('user_accounts.id', ondelete='SET NULL'),
        nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)


class OwnerPreference(Base):
    __tablename__ = 'owner_preferences'
    __table_args__ = (
        CheckConstraint("theme IN ('system', 'light', 'dark')", name='ck_owner_preferences_theme'),
        CheckConstraint("table_density IN ('comfortable', 'compact')", name='ck_owner_preferences_density'),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('user_accounts.id', ondelete='CASCADE'),
        primary_key=True,
    )
    theme: Mapped[str] = mapped_column(String(20), default='system', nullable=False)
    table_density: Mapped[str] = mapped_column(String(20), default='comfortable', nullable=False)
    default_date_range: Mapped[str] = mapped_column(String(32), default='this_month', nullable=False)
    nav_order: Mapped[list[str]] = mapped_column(
        JSONB,
        default=lambda: [
            'products', 'collections', 'hero', 'media', 'inventory',
            'suppliers', 'orders', 'returns', 'coupons', 'expenses',
            'analytics', 'settings'
        ],
        nullable=False,
    )
    dashboard_layout: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {
            'cards': [
                {'id': 'sales', 'visible': True},
                {'id': 'inventory', 'visible': True},
                {'id': 'liabilities', 'visible': True},
                {'id': 'expenses', 'visible': True},
            ]
        },
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
