"""Pydantic schemas for Vendor Stock Portal (VS2-VS3)."""
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, ConfigDict


# --- Auth Schemas ---
class VendorLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class VendorSessionResponse(BaseModel):
    username: str
    vendor_id: uuid.UUID
    vendor_name: str
    vendor_slug: str
    csrf_token: str
    authenticated: bool = True


# --- Owner Administration of Vendor Users ---
class ProvisionVendorUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    allow_short_local: bool = False


class ResetVendorPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=128)
    allow_short_local: bool = False


class ToggleVendorUserStatusRequest(BaseModel):
    is_active: bool


class VendorUserResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    vendor_id: uuid.UUID
    username: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


# --- Vendor Stock Item & Update Schemas ---
class VendorStockItem(BaseModel):
    variant_id: int
    product_id: str
    product_title: str
    product_slug: str
    thumbnail_url: Optional[str] = None
    variant_sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    allocated_on_hand: int
    held_quantity: int
    available_quantity: int
    version: int
    last_updated_at: Optional[datetime] = None


class VendorStockListResponse(BaseModel):
    items: List[VendorStockItem]
    total_items: int
    page: int
    limit: int


class VendorStockCountUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    counted_quantity: int = Field(..., ge=0, description="Count allocated to AlphaZee (includes reserved units)")
    expected_version: int = Field(..., description="Optimistic concurrency control balance version")
    reason: str = Field("shop_sale", description="Reason: shop_sale, restock, inventory_count_correction, other")
    note: Optional[str] = Field(None, max_length=500)
    request_ref: Optional[str] = Field(None, max_length=160)


class VendorStockCountUpdateResponse(BaseModel):
    variant_id: int
    allocated_on_hand: int
    held_quantity: int
    available_quantity: int
    version: int
    shortage_detected: bool = False
    message: str


class ReportShortageRequest(BaseModel):
    variant_id: int
    reported_count: int = Field(..., ge=0)
    note: Optional[str] = Field(None, max_length=500)


class VendorShortageResponse(BaseModel):
    id: uuid.UUID
    variant_id: int
    vendor_id: uuid.UUID
    reported_count: int
    held_reservations: int
    physical_on_hand_snapshot: int
    status: str
    notes: Optional[str] = None
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class ResolveShortageRequest(BaseModel):
    resolution_action: str = Field(..., description="resolved, cancelled")
    resolution_note: str = Field(..., min_length=3, max_length=500)


class VendorAuditHistoryItem(BaseModel):
    event_id: uuid.UUID
    variant_id: int
    product_title: str
    variant_sku: str
    actor_username: str
    previous_on_hand: int
    new_on_hand: int
    delta: int
    reason: str
    notes: Optional[str] = None
    occurred_at: datetime


class VendorAuditHistoryResponse(BaseModel):
    history: List[VendorAuditHistoryItem]
    total: int
