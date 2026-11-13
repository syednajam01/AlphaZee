"""
Pydantic schemas for AlphaZee Owner Administration APIs (v1).

Covers:
- Inventory summary and real-time physical/held/available stock metrics.
- Optimistically-guarded inventory adjustments.
- Owner order management and payment verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.orders import OrderResponseSchema


class InventoryMetricResponse(BaseModel):
    """
    Real-time inventory metric triple (Physical | Held | Available)
    for a specific supplier variant.
    """

    supplier_variant_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    variant_id: int
    product_title: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    physical_on_hand: int = Field(description="Total physical units in warehouse/supplier premises")
    held_reservations: int = Field(description="Units held by held/confirmed reservations or unreconciled legacy stock holds")
    available_to_sell: int = Field(description="Net available units for new orders (Physical - Held)")
    version: int = Field(description="Optimistic concurrency control version")


class InventorySummaryResponse(BaseModel):
    """List of all active catalog inventory metrics."""

    items: list[InventoryMetricResponse]
    total_variants: int


class InventoryAdjustRequest(BaseModel):
    """Optimistically guarded stock adjustment request."""

    supplier_variant_id: uuid.UUID = Field(description="Supplier variant UUID")
    quantity_delta: int = Field(strict=True, ge=-2147483647, le=2147483647, description="Positive (stock received) or negative (damaged/shrinkage) delta")
    expected_version: int = Field(strict=True, ge=0, description="Expected concurrency version number")
    reason: str = Field(min_length=3, max_length=100, description="Reason for stock movement")
    reference_id: Optional[str] = Field(default=None, max_length=100, description="Optional invoice/PO/audit ref")
    notes: Optional[str] = Field(default=None, max_length=500)


class AdminOrderListResponse(BaseModel):
    """Paginated list of orders for owner dashboard."""

    orders: list[OrderResponseSchema]
    total: int
    page: int
    page_size: int


class SupplierCreateRequest(BaseModel):
    """Payload to create or update an approved supplier."""

    name: str = Field(min_length=2, max_length=200, description="Supplier trade name")
    slug: str = Field(min_length=2, max_length=100, description="URL/admin portal slug")
    status: str = Field(default="active", description="'active', 'inactive', or 'suspended'")
    notes: Optional[str] = Field(default=None, max_length=500, description="Contact/settlement notes")


class SupplierQuickProvisionRequest(BaseModel):
    """Payload to atomically create an approved supplier and vendor user login."""

    name: str = Field(min_length=2, max_length=200, description="Supplier trade name")
    whatsapp_number: str = Field(min_length=7, max_length=32, description="WhatsApp phone number")
    username: str = Field(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_\-\.]+$', description="Portal login handle")
    password: str = Field(min_length=6, max_length=128, description="Initial portal password")
    notes: Optional[str] = Field(default=None, max_length=500)


class VendorProfileUpdateRequest(BaseModel):
    """Payload submitted by vendor to complete onboarding and update business profile."""

    contact_person: str = Field(min_length=2, max_length=128)
    business_type: Optional[str] = Field(default=None, max_length=64)
    cnic: str = Field(min_length=13, max_length=32, description="CNIC number")
    ntn: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=128)
    alt_phone: Optional[str] = Field(default=None, max_length=32)
    warehouse_address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=64)
    bank_name: str = Field(min_length=2, max_length=64)
    account_title: str = Field(min_length=2, max_length=128)
    iban: str = Field(min_length=14, max_length=34)
    lead_time_days: Optional[int] = Field(default=2, ge=0, le=60)
    terms_accepted: bool = Field(default=True)


class SupplierResponseSchema(BaseModel):
    """Approved supplier details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    supplier_type: str = "external_vendor"
    whatsapp_number: Optional[str] = None
    contact_person: Optional[str] = None
    business_type: Optional[str] = None
    cnic: Optional[str] = None
    ntn: Optional[str] = None
    email: Optional[str] = None
    warehouse_address: Optional[str] = None
    city: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_title: Optional[str] = None
    bank_iban: Optional[str] = None
    lead_time_days: int = 2
    onboarding_status: str = "pending_profile"
    portal_username: Optional[str] = None
    main_products_count: int = 0
    total_stock_count: int = 0
    notes: Optional[str] = None


class SupplierListResponse(BaseModel):
    """List of all registered suppliers."""

    suppliers: list[SupplierResponseSchema]
    total: int


class SupplierVariantAssignRequest(BaseModel):
    """Assign or update a catalog variant supplier cost."""

    variant_id: int = Field(ge=1, description="Catalog variant ID")
    supplier_cost_minor: int = Field(strict=True, ge=0, le=2147483647, description="Wholesale cost in PKR minor units (paisas)")
    active: bool = Field(default=True, description="Whether this is the primary active supplying vendor")


class CatalogVariantAdminSchema(BaseModel):
    id: int
    product_title: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    active_supplier_id: Optional[uuid.UUID] = None
    supplier_cost_minor: Optional[int] = None


class SupplierVariantResponseSchema(BaseModel):
    """Supplier variant linkage details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    variant_id: int
    supplier_cost_minor: int
    active: bool


class AdminOverviewMetricsResponse(BaseModel):
    """Real-time store metrics for owner dashboard header."""

    gross_revenue_minor: int
    formatted_gross_revenue: str
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    delivered_orders: int
    total_skus: int
    low_stock_skus: int
    cash_received_minor: int = 0
    courier_held_cod_minor: int = 0
    refund_outstanding_minor: int = 0
    estimated_contribution_minor: int = 0


class ShipmentCreateRequest(BaseModel):
    """Payload to dispatch an order via courier."""

    courier_code: str = Field(description="Courier company: trax, leopards, call_courier, postex, tcs, mnp, manual")
    tracking_number: str = Field(min_length=3, max_length=64, description="Tracking number / waybill ID")
    shipping_cost_minor: int = Field(default=0, ge=0, description="Actual courier shipping fee in paisas")
    tracking_url: Optional[str] = Field(default=None, max_length=512, description="Direct web tracking link")


class RtoReceivedLine(BaseModel):
    order_line_id: uuid.UUID
    received_quantity: int = Field(ge=0)


class RtoReceivedRequest(BaseModel):
    lines: list[RtoReceivedLine] = Field(min_length=1)


class ShipmentStatusUpdateRequest(BaseModel):
    """Payload to update delivery status or record RTO."""

    status: str = Field(description="New status: in_transit, out_for_delivery, delivered, rto_initiated, rto_delivered")
    rto_reason: Optional[str] = Field(default=None, max_length=200, description="Customer refusal or address issue reason")
    rto_courier_cost_minor: int = Field(default=0, ge=0, description="Courier return penalty charge in paisas")
    received_lines: Optional[list[RtoReceivedLine]] = None


class OrderRtoInitiateRequest(BaseModel):
    """Payload to initiate RTO on a dispatched order."""

    reason: Optional[str] = Field(default=None, max_length=200, description="Customer refusal or courier issue reason")
    rto_courier_cost_minor: int = Field(default=0, ge=0, description="Estimated or charged RTO courier shipping fee in paisas")


class RtoInspectionLine(BaseModel):
    order_line_id: uuid.UUID
    sellable_quantity: int = Field(ge=0)
    damaged_quantity: int = Field(ge=0)


class RtoInspectionRequest(BaseModel):
    """Cumulative line dispositions; any remainder stays quarantined."""

    lines: list[RtoInspectionLine] = Field(min_length=1)
    notes: Optional[str] = Field(default=None, max_length=500, description="Inspection findings or defect/damage notes")


class LegacyStockDecision(BaseModel):
    reservation_id: uuid.UUID
    physical_deducted: bool
    received_quantity: Optional[int] = Field(default=None, ge=0)


class LegacyShipmentReconcileRequest(BaseModel):
    lines: list[LegacyStockDecision] = Field(min_length=1)
    note: str = Field(min_length=5, max_length=500)


class SettlementDeductionRequest(BaseModel):
    entry_type: Literal['outbound_shipping', 'rto_shipping', 'other_deduction']
    amount_minor: int = Field(ge=1)
    reference: str = Field(min_length=3, max_length=120)
    note: str = Field(min_length=5, max_length=500)


class CodRemittanceRequest(BaseModel):
    """Payload to record courier COD cash remittance into bank account."""

    remitted_amount_minor: int = Field(ge=0, description="Actual cash received in bank in paisas; zero for deduction-only")
    reference: Optional[str] = Field(default=None, max_length=120, description="Bank deposit ref / courier payout invoice number")
    deductions: list[SettlementDeductionRequest] = []
    final_statement: bool = False
    is_partial: bool = Field(default=False, description="Flag explicitly confirming this is a partial remittance")
    partial: Optional[bool] = Field(default=None, description="Alias for is_partial")
    partial_reason: Optional[str] = Field(default=None, max_length=255, description="Reason for short remittance from courier")


class ShipmentAdminResponseSchema(BaseModel):
    """Full courier shipment details for owner console."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    replacement_return_id: Optional[uuid.UUID] = None
    order_id: uuid.UUID
    courier_code: str
    tracking_number: str
    tracking_url: Optional[str] = None
    shipping_cost_minor: int
    status: str
    stock_reconciliation_status: str = 'ready'
    cod_amount_minor: int
    cod_remitted_amount_minor: int
    settlement_deductions_minor: int = 0
    settlement_outstanding_minor: int = 0
    settlement_entries: list['SettlementEntryResponseSchema'] = []
    remittance_amount_minor: int = 0
    cod_remittance_status: str
    is_partial_remittance: bool = False
    cod_remittance_reference: Optional[str] = None
    cod_remitted_at: Optional[datetime] = None
    rto_reason: Optional[str] = None
    rto_courier_cost_minor: int
    rto_restocked_at: Optional[datetime] = None
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class SettlementEntryResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entry_type: str
    amount_minor: int
    reference: str
    note: Optional[str] = None
    final_statement: bool
    recorded_at: datetime


class ProfitLossResponseSchema(BaseModel):
    """Financial gross profit, COGS, courier expenses, and unit economics report."""

    gross_revenue_minor: int
    order_value_minor: int = 0
    delivered_sales_minor: int = 0
    bank_customer_payments_minor: int = 0
    cod_collected_minor: int = 0
    courier_held_cod_minor: int = 0
    courier_deductions_minor: int = 0
    other_deductions_minor: int = 0
    business_cash_received_minor: int = 0
    refund_paid_minor: int = 0
    refund_outstanding_minor: int = 0
    sales_reversals_minor: int = 0
    cogs_reversals_minor: int = 0
    formatted_gross_revenue: str
    net_revenue_minor: int = 0
    formatted_net_revenue: Optional[str] = None
    refund_total_minor: int = 0
    formatted_refund_total: Optional[str] = None
    subtotal_revenue_minor: int
    shipping_revenue_minor: int
    cogs_minor: int
    formatted_cogs: str
    outbound_courier_cost_minor: int
    rto_courier_cost_minor: int
    total_courier_expenses_minor: int
    formatted_courier_expenses: str
    gross_profit_minor: int
    formatted_gross_profit: str
    gross_margin_percent: float
    total_orders_count: int
    total_shipments_count: int
    delivered_shipments_count: int
    rto_shipments_count: int
    rto_rate_percent: float
    cod_pending_remittance_minor: int
    cod_remitted_minor: int


class MarketingAttributionItemSchema(BaseModel):
    """UTM campaign performance item."""

    utm_source: str
    utm_medium: str
    utm_campaign: str
    orders_count: int
    revenue_minor: int
    formatted_revenue: str
    discount_minor: int
    formatted_discount: str


class MarketingAttributionResponseSchema(BaseModel):
    """Marketing campaign attribution performance summary."""

    channels: list[MarketingAttributionItemSchema]
    total_campaigns: int


class SupplierAcceptanceRequest(BaseModel):
    """Payload to record operational supplier acceptance for order fulfillment."""

    notes: Optional[str] = Field(default=None, max_length=500, description="Supplier / warehouse acceptance notes")


class PaymentInstructionsSentRequest(BaseModel):
    confirmed_sent: Literal[True] = Field(description='Owner confirms the instructions reached the customer')
    channel: Literal['whatsapp', 'sms', 'email', 'phone', 'other']
    reference: str = Field(min_length=3, max_length=200,
                           description='Message ID, recipient or other handoff reference')


class PaymentReviewResolutionRequest(BaseModel):
    funds_checked: Literal[True] = Field(description='Owner checked received and pending bank funds')
    resolution: Literal['payment_received', 'release_unpaid']
    note: str = Field(min_length=5, max_length=500)




