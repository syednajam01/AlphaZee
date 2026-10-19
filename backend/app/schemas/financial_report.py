"""Pydantic V2 schemas for VF4 Comprehensive Financial Reports and Order Economics."""

import uuid
from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderEconomicsLineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_line_id: uuid.UUID
    variant_id: int
    title: str
    sku: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int
    unit_price_minor: int
    unit_cost_minor: int
    total_price_minor: int
    total_cost_minor: int
    line_contribution_minor: int
    ownership_source: str
    supplier_name: Optional[str] = None


class OrderEconomicsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: uuid.UUID
    order_number: str
    placed_at: datetime
    delivered_at: Optional[datetime] = None
    order_status: str
    payment_method: str
    payment_status: str
    customer_total_minor: int
    subtotal_minor: int
    shipping_fee_minor: int
    discount_minor: int
    cogs_minor: int
    outbound_shipping_cost_minor: int
    rto_courier_cost_minor: int
    total_logistics_cost_minor: int
    supplier_charges_minor: int
    supplier_payments_minor: int
    supplier_outstanding_minor: int
    estimated_contribution_minor: int
    lines: List[OrderEconomicsLineItem] = []


class OrderEconomicsListResponse(BaseModel):
    orders: List[OrderEconomicsItem]
    total_orders: int
    page: int
    limit: int


class RevenueBreakdown(BaseModel):
    gross_sales_minor: int
    shipping_revenue_minor: int
    discounts_minor: int
    sales_reversals_minor: int
    net_revenue_minor: int
    formatted_net_revenue: str


class CogsBreakdown(BaseModel):
    gross_cogs_minor: int
    cogs_reversals_minor: int
    net_cogs_minor: int
    formatted_net_cogs: str


class FreightBreakdown(BaseModel):
    outbound_freight_minor: int
    rto_freight_minor: int
    customer_return_freight_minor: int
    total_freight_minor: int
    formatted_total_freight: str
    policy_note: str = "AlphaZee strictly bears 100% of RTO and customer-return transport expenses."


class OverheadBreakdown(BaseModel):
    packaging_minor: int
    advertising_minor: int
    platform_hosting_minor: int
    salaries_minor: int
    office_supplies_minor: int
    other_overhead_minor: int
    total_overhead_minor: int
    formatted_total_overhead: str


class OperatingResultBreakdown(BaseModel):
    contribution_before_overhead_minor: int
    formatted_contribution_before_overhead: str
    contribution_margin_percent: float
    total_operating_costs_minor: int
    net_operating_result_minor: int
    formatted_net_operating_result: str
    disclaimer: str = (
        "Estimated operational snapshot based on recorded transactions and business expenses. "
        "Excludes unrecorded corporate income taxes and unallocated offline overhead."
    )


class CashReconciliationBreakdown(BaseModel):
    bank_customer_receipts_minor: int
    courier_cod_remitted_minor: int
    total_cash_inflow_minor: int
    refunds_paid_minor: int
    supplier_payments_paid_minor: int
    business_expenses_paid_cash_or_bank_minor: int
    courier_deductions_settled_minor: int
    total_cash_outflow_minor: int
    net_cash_movement_minor: int
    formatted_net_cash_movement: str
    courier_held_cod_outstanding_minor: int
    supplier_liabilities_outstanding_minor: int
    refund_liabilities_outstanding_minor: int


class PeriodFinancialReportResponse(BaseModel):
    timezone: str = "Asia/Karachi"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    date_basis: str = (
        "Delivered sales recognized by delivery date; expenses recognized by incurred date; "
        "cash movements recognized by settlement/payment date."
    )
    revenue: RevenueBreakdown
    cogs: CogsBreakdown
    freight: FreightBreakdown
    overhead: OverheadBreakdown
    operating_result: OperatingResultBreakdown
    cash_reconciliation: CashReconciliationBreakdown
    total_orders_count: int
    delivered_orders_count: int
    total_shipments_count: int
    delivered_shipments_count: int
    rto_shipments_count: int
    rto_rate_percent: float
