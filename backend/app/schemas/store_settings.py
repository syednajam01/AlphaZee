"""Pydantic schemas for store settings, policies, audit logs, and owner preferences."""
from __future__ import annotations

from datetime import datetime
import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicStoreSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_name: str
    tagline: str
    announcement_banner_enabled: bool
    announcement_banner_text: str
    announcement_banner_link: str | None
    logo_url: str | None
    accent_color: str
    font_family: str
    border_radius: str
    spacing_density: str
    section_order: list[str]
    support_email: str | None
    support_phone: str | None
    support_hours: str | None
    delivery_policy: str | None
    return_policy: str | None
    terms_policy: str | None
    privacy_policy: str | None
    shipping_coverage_area: str
    standard_shipping_fee_minor: int
    shipping_rules_configured: bool
    free_shipping_threshold_minor: int | None


class AdminStoreSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_name: str
    tagline: str
    announcement_banner_enabled: bool
    announcement_banner_text: str
    announcement_banner_link: str | None
    logo_media_id: str | None
    logo_url: str | None
    accent_color: str
    font_family: str
    border_radius: str
    spacing_density: str
    section_order: list[str]
    support_email: str | None
    support_phone: str | None
    support_hours: str | None
    delivery_policy_content: str | None
    delivery_policy_status: str
    delivery_policy_published_at: datetime | None
    return_policy_content: str | None
    return_policy_status: str
    return_policy_published_at: datetime | None
    terms_policy_content: str | None
    terms_policy_status: str
    terms_policy_published_at: datetime | None
    privacy_policy_content: str | None
    privacy_policy_status: str
    privacy_policy_published_at: datetime | None
    shipping_coverage_area: str
    standard_shipping_fee_minor: int
    shipping_rules_configured: bool
    free_shipping_threshold_minor: int | None
    low_stock_threshold: int
    stock_staleness_threshold_days: int
    version: int
    updated_at: datetime
    updated_by_user_id: uuid.UUID | None


VALID_FONTS = {
    'Inter, sans-serif',
    'Outfit, sans-serif',
    'Playfair Display, serif',
    'System-UI, sans-serif',
}
VALID_BORDER_RADII = {'none', 'sm', 'md', 'lg', 'full'}
VALID_SPACING = {'compact', 'comfortable', 'spacious'}


class UpdateStoreSettingsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    shipping_rules_configured: bool | None = None
    expected_version: int | None = Field(default=None, ge=1)

    brand_name: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=255)
    announcement_banner_enabled: bool | None = None
    announcement_banner_text: str | None = Field(default=None, min_length=1, max_length=255)
    announcement_banner_link: str | None = Field(default=None, max_length=255)
    logo_media_id: str | None = Field(default=None, max_length=32)
    accent_color: str | None = Field(default=None, max_length=32)
    font_family: str | None = Field(default=None, max_length=64)
    border_radius: str | None = Field(default=None, max_length=32)
    spacing_density: str | None = Field(default=None, max_length=32)
    section_order: list[str] | None = None
    support_email: str | None = Field(default=None, max_length=120)
    support_phone: str | None = Field(default=None, max_length=50)
    support_hours: str | None = Field(default=None, max_length=120)
    delivery_policy_content: str | None = None
    return_policy_content: str | None = None
    terms_policy_content: str | None = None
    privacy_policy_content: str | None = None
    shipping_coverage_area: str | None = Field(default=None, min_length=1, max_length=100)
    standard_shipping_fee_minor: int | None = Field(default=None, ge=0)
    free_shipping_threshold_minor: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    stock_staleness_threshold_days: int | None = Field(default=None, ge=1)
    change_reason: str | None = Field(default=None, max_length=255)

    @field_validator('accent_color')
    @classmethod
    def validate_accent_color(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not re.match(r'^#[0-9a-fA-F]{6}$', v):
                raise ValueError('accent_color must be a valid 6-character hex code, e.g. #111827')
        return v

    @field_validator('font_family')
    @classmethod
    def validate_font(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_FONTS:
            raise ValueError(f'font_family must be one of: {", ".join(sorted(VALID_FONTS))}')
        return v

    @field_validator('border_radius')
    @classmethod
    def validate_border_radius(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_BORDER_RADII:
            raise ValueError(f'border_radius must be one of: {", ".join(sorted(VALID_BORDER_RADII))}')
        return v

    @field_validator('spacing_density')
    @classmethod
    def validate_spacing(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SPACING:
            raise ValueError(f'spacing_density must be one of: {", ".join(sorted(VALID_SPACING))}')
        return v


class PublishPolicyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    publish: bool = Field(..., description='True to publish, False to revert to draft')


class StoreSettingsAuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    changed_fields: dict[str, Any]
    changed_by_user_id: uuid.UUID | None
    change_reason: str | None
    created_at: datetime


class OwnerPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    theme: Literal['system', 'light', 'dark']
    table_density: Literal['comfortable', 'compact']
    default_date_range: str
    nav_order: list[str]
    dashboard_layout: dict[str, Any]
    updated_at: datetime


class UpdateOwnerPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    theme: Literal['system', 'light', 'dark'] | None = None
    table_density: Literal['comfortable', 'compact'] | None = None
    default_date_range: str | None = Field(default=None, max_length=32)
    nav_order: list[str] | None = None
    dashboard_layout: dict[str, Any] | None = None
