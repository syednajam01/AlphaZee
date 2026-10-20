"""Owner financial reporting, period P&L, per-order economics, and CSV exports.

All internal amounts use integer paisas (PKR minor units).
Explicitly separates delivered sales, wholesale COGS, AlphaZee-borne transport expenses,
operating expenses, and cash reconciliation movements.
"""

from datetime import date, datetime, time, timezone, timedelta
import io
import csv
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import Session

from app.models.business_expenses import BusinessExpense
from app.models.catalog import Product, Variant
from app.models.finance import CourierSettlementEntry, RefundExecution
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment, ShipmentAllocation
from app.models.inventory import StockReservation
from app.models.supplier_finance import (
    SupplierAgreement,
    SupplierLedgerEntry,
    SupplierPaymentAllocation,
)
from app.models.suppliers import Supplier

try:
    from zoneinfo import ZoneInfo
    KARACHI_TZ = ZoneInfo("Asia/Karachi")
except Exception:
    from datetime import timedelta
    KARACHI_TZ = timezone(timedelta(hours=5))


def _sum(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def rto_writeoff_cost(db, start_dt=None, end_dt=None):
    from app.services.stock_ownership import returned_cost
    query = select(ShipmentAllocation, OrderLine).join(StockReservation,
        StockReservation.id == ShipmentAllocation.reservation_id).join(OrderLine,
        OrderLine.id == StockReservation.order_line_id).where(ShipmentAllocation.damaged_quantity > 0)
    if start_dt:
        query = query.where(ShipmentAllocation.inspected_at >= start_dt)
    if end_dt:
        query = query.where(ShipmentAllocation.inspected_at < end_dt)
    return sum(returned_cost(line, allocation.damaged_quantity, allocation.sellable_quantity)
               for allocation, line in db.execute(query))


def _format_pkr(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    abs_minor = abs(minor)
    rupees = abs_minor // 100
    paisa = abs_minor % 100
    if paisa == 0:
        return f"{sign}PKR {rupees:,}"
    return f"{sign}PKR {rupees:,}.{paisa:02d}"


def escape_csv_cell(value: Any) -> str:
    """Guard against CSV spreadsheet formula injection (=, +, -, @, \\t, \\r)."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def get_financial_summary(db: Session) -> dict:
    """All-time operational snapshot preserving legacy dashboard compatibility."""
    valid_order = Order.order_status != "cancelled"
    delivered = Order.order_status == "delivered"
    order_value = _sum(db, select(func.sum(Order.total_minor)).where(valid_order))
    original_sales = _sum(db, select(func.sum(Order.total_minor)).where(delivered))
    replacement_sales = _sum(
        db,
        select(func.sum(Shipment.cod_amount_minor)).where(
            Shipment.replacement_return_id.is_not(None), Shipment.status == "delivered"
        ),
    )
    delivered_sales = original_sales + replacement_sales
    bank_payments = _sum(
        db,
        select(func.sum(Order.total_minor)).where(
            Order.payment_method == "bank_transfer",
            or_(
                Order.payment_verified_at.is_not(None),
                Order.payment_status.in_(["verified", "refunded"]),
            ),
        ),
    )
    cod_collected = _sum(
        db,
        select(func.sum(Shipment.cod_amount_minor)).where(
            Shipment.cod_amount_minor > 0,
            or_(Shipment.delivered_at.is_not(None), Shipment.status == "delivered"),
        ),
    )
    courier_cash = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            CourierSettlementEntry.entry_type == "receipt"
        ),
    )
    courier_deductions = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            CourierSettlementEntry.entry_type != "receipt"
        ),
    )
    other_deductions = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            CourierSettlementEntry.entry_type == "other_deduction"
        ),
    )
    cod_outstanding = max(0, cod_collected - courier_cash - courier_deductions)

    sales_reversals = _sum(
        db,
        select(func.sum(OrderReturn.refund_amount_minor)).where(
            OrderReturn.status == "completed",
            OrderReturn.return_type == "refund_bank_transfer",
        ),
    )
    refund_paid = _sum(db, select(func.sum(RefundExecution.amount_minor)))
    refund_outstanding = max(0, sales_reversals - refund_paid)

    original_cogs = _sum(
        db,
        select(func.sum(func.coalesce(OrderLine.acquisition_cost_minor, OrderLine.unit_cost_minor * OrderLine.quantity)))
        .join(Order, OrderLine.order_id == Order.id)
        .where(delivered, OrderLine.fulfillment_kind == "original"),
    )
    from app.services.stock_ownership import returned_cost
    return_cogs_reversal = sum(ret.restocked_cost_minor if ret.restocked_cost_minor is not None
        else returned_cost(line, ret.sellable_quantity)
        for ret, line in db.execute(select(OrderReturn, OrderLine).join(OrderLine,
            OrderLine.id == OrderReturn.order_line_id).join(Order, Order.id == OrderLine.order_id)
            .where(delivered, OrderReturn.status == 'completed')))
    replacement_cogs = _sum(
        db,
        select(func.sum(func.coalesce(OrderLine.acquisition_cost_minor, OrderLine.unit_cost_minor * OrderLine.quantity)))
        .join(
            Shipment,
            Shipment.replacement_return_id == OrderLine.replacement_return_id,
        )
        .where(
            OrderLine.fulfillment_kind == "replacement",
            Shipment.status == "delivered",
        ),
    )
    cogs = original_cogs - return_cogs_reversal + replacement_cogs + rto_writeoff_cost(db)
    outbound_cost = _sum(db, select(func.sum(Shipment.shipping_cost_minor)))
    rto_cost = _sum(db, select(func.sum(Shipment.rto_courier_cost_minor)))
    courier_expenses = outbound_cost + rto_cost
    net_sales = delivered_sales - sales_reversals
    contribution = net_sales - cogs - courier_expenses - other_deductions
    total_shipments = _sum(db, select(func.count(Shipment.id)))
    rto_shipments = _sum(
        db,
        select(func.count(Shipment.id)).where(
            Shipment.status.in_(["rto_initiated", "rto_delivered"])
        ),
    )
    delivered_shipments = _sum(
        db, select(func.count(Shipment.id)).where(Shipment.status == "delivered")
    )
    return {
        "order_value_minor": order_value,
        "delivered_sales_minor": delivered_sales,
        "bank_customer_payments_minor": bank_payments,
        "cod_collected_minor": cod_collected,
        "courier_held_cod_minor": cod_outstanding,
        "courier_deductions_minor": courier_deductions,
        "other_deductions_minor": other_deductions,
        "business_cash_received_minor": bank_payments + courier_cash - refund_paid,
        "refund_paid_minor": refund_paid,
        "refund_outstanding_minor": refund_outstanding,
        "sales_reversals_minor": sales_reversals,
        "cogs_reversals_minor": return_cogs_reversal,
        "gross_revenue_minor": delivered_sales,
        "net_revenue_minor": net_sales,
        "refund_total_minor": sales_reversals,
        "subtotal_revenue_minor": _sum(
            db, select(func.sum(Order.subtotal_minor)).where(delivered)
        ),
        "shipping_revenue_minor": _sum(
            db, select(func.sum(Order.shipping_fee_minor)).where(delivered)
        ),
        "cogs_minor": cogs,
        "outbound_courier_cost_minor": outbound_cost,
        "rto_courier_cost_minor": rto_cost,
        "total_courier_expenses_minor": courier_expenses,
        "gross_profit_minor": contribution,
        "total_orders_count": _sum(
            db, select(func.count(Order.id)).where(valid_order)
        ),
        "total_shipments_count": total_shipments,
        "delivered_shipments_count": delivered_shipments,
        "rto_shipments_count": rto_shipments,
        "rto_rate_percent": (
            round(rto_shipments / total_shipments * 100, 2)
            if total_shipments
            else 0.0
        ),
        "cod_pending_remittance_minor": cod_outstanding,
        "cod_remitted_minor": courier_cash,
    }


def get_period_financial_report(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    timezone_str: str = "Asia/Karachi",
) -> Dict[str, Any]:
    """Calculate date-bounded financial report & P&L according to Asia/Karachi boundaries."""
    tz = KARACHI_TZ
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=tz).astimezone(
            timezone.utc
        )
    if end_date:
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz).astimezone(
            timezone.utc
        )

    # 1. Orders & Sales Recognition
    valid_order = Order.order_status != "cancelled"
    delivered = Order.order_status == "delivered"

    order_filter = [valid_order]
    delivery_date = select(func.min(Shipment.delivered_at)).where(
        Shipment.order_id == Order.id, Shipment.replacement_return_id.is_(None)).correlate(Order).scalar_subquery()
    delivered_filter = [delivered]
    if start_dt:
        order_filter.append(Order.placed_at >= start_dt)
        delivered_filter.append(delivery_date >= start_dt)
    if end_dt:
        order_filter.append(Order.placed_at < end_dt)
        delivered_filter.append(delivery_date < end_dt)

    total_orders_count = _sum(db, select(func.count(Order.id)).where(and_(*order_filter)))
    delivered_orders_count = _sum(
        db, select(func.count(Order.id)).where(and_(*delivered_filter))
    )

    gross_sales_minor = _sum(
        db, select(func.sum(Order.subtotal_minor)).where(and_(*delivered_filter))
    )
    subtotal_minor = _sum(
        db, select(func.sum(Order.subtotal_minor)).where(and_(*delivered_filter))
    )
    shipping_revenue_minor = _sum(
        db, select(func.sum(Order.shipping_fee_minor)).where(and_(*delivered_filter))
    )
    discounts_minor = _sum(
        db, select(func.sum(Order.discount_amount_minor)).where(and_(*delivered_filter))
    )

    # Replacement delivered sales
    rep_filter = [
        Shipment.replacement_return_id.is_not(None),
        Shipment.status == "delivered",
    ]
    if start_dt:
        rep_filter.append(Shipment.delivered_at >= start_dt)
    if end_dt:
        rep_filter.append(Shipment.delivered_at < end_dt)
    replacement_sales = _sum(
        db, select(func.sum(Shipment.cod_amount_minor)).where(and_(*rep_filter))
    )
    gross_sales_minor += replacement_sales

    # Customer returns (sales reversals)
    return_filter = [
        OrderReturn.status == "completed",
        OrderReturn.return_type == "refund_bank_transfer",
    ]
    if start_dt:
        return_filter.append(OrderReturn.inspected_at >= start_dt)
    if end_dt:
        return_filter.append(OrderReturn.inspected_at < end_dt)
    sales_reversals_minor = _sum(
        db, select(func.sum(OrderReturn.refund_amount_minor)).where(and_(*return_filter))
    )
    net_revenue_minor = gross_sales_minor - discounts_minor + shipping_revenue_minor - sales_reversals_minor

    # 2. COGS (Cost of Goods Sold)
    cogs_stmt = (
        select(func.sum(func.coalesce(OrderLine.acquisition_cost_minor, OrderLine.unit_cost_minor * OrderLine.quantity)))
        .join(Order, OrderLine.order_id == Order.id)
        .where(and_(*delivered_filter), OrderLine.fulfillment_kind == "original")
    )
    gross_cogs_minor = _sum(db, cogs_stmt)

    # Return recognition is independent of the original sale's period.
    reversal_rows = select(OrderReturn, OrderLine).join(OrderLine, OrderLine.id == OrderReturn.order_line_id).where(
        OrderReturn.status == 'completed')
    if start_dt:
        reversal_rows = reversal_rows.where(OrderReturn.inspected_at >= start_dt)
    if end_dt:
        reversal_rows = reversal_rows.where(OrderReturn.inspected_at < end_dt)
    from app.services.stock_ownership import returned_cost
    cogs_reversals_minor = sum(ret.restocked_cost_minor if ret.restocked_cost_minor is not None else returned_cost(line, ret.sellable_quantity)
                              for ret, line in db.execute(reversal_rows))
    replacement_costs = select(func.sum(func.coalesce(OrderLine.acquisition_cost_minor,
        OrderLine.unit_cost_minor * OrderLine.quantity))).join(Shipment,
        Shipment.replacement_return_id == OrderLine.replacement_return_id).where(*rep_filter)
    gross_cogs_minor += _sum(db, replacement_costs)
    writeoffs_minor = rto_writeoff_cost(db, start_dt, end_dt)
    gross_cogs_minor += writeoffs_minor
    net_cogs_minor = gross_cogs_minor - cogs_reversals_minor

    # 3. Freight Expenses (AlphaZee strictly bears outbound, RTO & customer return transport)
    shipment_filter = []
    if start_dt:
        shipment_filter.append(Shipment.created_at >= start_dt)
    if end_dt:
        shipment_filter.append(Shipment.created_at < end_dt)

    total_shipments_count = _sum(
        db,
        select(func.count(Shipment.id)).where(and_(*shipment_filter))
        if shipment_filter
        else select(func.count(Shipment.id)),
    )
    delivered_shipments_count = _sum(
        db,
        select(func.count(Shipment.id)).where(
            and_(*(shipment_filter + [Shipment.status == "delivered"]))
        ),
    )
    rto_shipments_count = _sum(
        db,
        select(func.count(Shipment.id)).where(
            and_(
                *(
                    shipment_filter
                    + [Shipment.status.in_(["rto_initiated", "rto_delivered"])]
                )
            )
        ),
    )
    rto_rate_percent = (
        round(rto_shipments_count / total_shipments_count * 100, 2)
        if total_shipments_count
        else 0.0
    )

    outbound_freight_minor = _sum(
        db,
        select(func.sum(Shipment.shipping_cost_minor)).where(and_(*shipment_filter))
        if shipment_filter
        else select(func.sum(Shipment.shipping_cost_minor)),
    )
    rto_cost_date = func.coalesce(Shipment.rto_cost_recorded_at, Shipment.created_at)
    rto_filter = []
    if start_dt:
        rto_filter.append(rto_cost_date >= start_dt)
    if end_dt:
        rto_filter.append(rto_cost_date < end_dt)
    rto_freight_minor = _sum(db, select(func.sum(Shipment.rto_courier_cost_minor)).where(*rto_filter))

    # Customer return freight and additional courier expenses recorded in business_expenses
    exp_filter = []
    if start_date:
        exp_filter.append(BusinessExpense.incurred_date >= start_date)
    if end_date:
        exp_filter.append(BusinessExpense.incurred_date <= end_date)

    exp_query = select(
        BusinessExpense.category, func.sum(BusinessExpense.amount_minor)
    )
    if exp_filter:
        exp_query = exp_query.where(and_(*exp_filter))
    exp_query = exp_query.where(BusinessExpense.linked_courier_settlement_id.is_(None)).group_by(BusinessExpense.category)
    exp_rows = db.execute(exp_query).all()
    exp_by_cat = {row[0]: int(row[1] or 0) for row in exp_rows}

    # Add extra return/rto transport recorded in business expenses
    customer_return_freight_minor = exp_by_cat.get("customer_return_transport", 0)
    extra_rto_expense = exp_by_cat.get("rto_transport", 0)
    extra_outbound_expense = exp_by_cat.get("outbound_delivery", 0)

    # Linked rows are evidence for one existing shipment charge; unrelated rows add.
    def extra_freight(category):
        return _sum(db, select(func.sum(BusinessExpense.amount_minor)).where(
            *exp_filter, BusinessExpense.category == category,
            BusinessExpense.linked_shipment_id.is_(None),
            BusinessExpense.linked_courier_settlement_id.is_(None)))
    total_rto_freight_minor = rto_freight_minor + extra_freight('rto_transport')
    total_outbound_freight_minor = outbound_freight_minor + extra_freight('outbound_delivery')
    total_freight_minor = (
        total_outbound_freight_minor
        + total_rto_freight_minor
        + customer_return_freight_minor
    )

    # 4. Overhead Expenses
    packaging_minor = exp_by_cat.get("packaging", 0)
    advertising_minor = exp_by_cat.get("advertising", 0)
    platform_hosting_minor = exp_by_cat.get("platform_hosting", 0)
    salaries_minor = exp_by_cat.get("salaries", 0)
    office_supplies_minor = exp_by_cat.get("office_supplies", 0)
    other_deduction_query = select(func.sum(CourierSettlementEntry.amount_minor)).where(CourierSettlementEntry.entry_type == 'other_deduction')
    if start_dt:
        other_deduction_query = other_deduction_query.where(CourierSettlementEntry.recorded_at >= start_dt)
    if end_dt:
        other_deduction_query = other_deduction_query.where(CourierSettlementEntry.recorded_at < end_dt)
    other_overhead_minor = exp_by_cat.get("other_overhead", 0) + _sum(db, other_deduction_query)
    total_overhead_minor = (
        packaging_minor
        + advertising_minor
        + platform_hosting_minor
        + salaries_minor
        + office_supplies_minor
        + other_overhead_minor
    )

    # 5. Contribution & Operating Results
    # Contribution before overhead = net revenue - net cogs - freight - packaging
    contribution_before_overhead_minor = (
        net_revenue_minor - net_cogs_minor - total_freight_minor - packaging_minor
    )
    contribution_margin_pct = (
        round((contribution_before_overhead_minor / net_revenue_minor) * 100, 2)
        if net_revenue_minor > 0
        else 0.0
    )
    total_operating_costs_minor = (
        net_cogs_minor + total_freight_minor + total_overhead_minor
    )
    net_operating_result_minor = net_revenue_minor - total_operating_costs_minor

    # 6. Cash Reconciliation
    # Inflow
    bank_pmt_filter = [
        Order.payment_method == "bank_transfer",
        or_(
            Order.payment_verified_at.is_not(None),
            Order.payment_status.in_(["verified", "refunded"]),
        ),
    ]
    if start_dt:
        bank_pmt_filter.append(Order.payment_verified_at >= start_dt)
    if end_dt:
        bank_pmt_filter.append(Order.payment_verified_at < end_dt)
    bank_customer_receipts_minor = _sum(
        db, select(func.sum(Order.total_minor)).where(and_(*bank_pmt_filter))
    )

    courier_receipt_filter = [CourierSettlementEntry.entry_type == "receipt"]
    if start_dt:
        courier_receipt_filter.append(CourierSettlementEntry.recorded_at >= start_dt)
    if end_dt:
        courier_receipt_filter.append(CourierSettlementEntry.recorded_at < end_dt)
    courier_cod_remitted_minor = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            and_(*courier_receipt_filter)
        ),
    )
    period_ledger_query = select(SupplierLedgerEntry)
    if start_date:
        period_ledger_query = period_ledger_query.where(SupplierLedgerEntry.effective_date >= start_date)
    if end_date:
        period_ledger_query = period_ledger_query.where(SupplierLedgerEntry.effective_date <= end_date)
    ledger_cash = []
    for entry in db.scalars(period_ledger_query):
        original = db.get(SupplierLedgerEntry, entry.reversal_entry_id) if entry.reversal_entry_id else entry
        ledger_cash.append((original.entry_type, entry.amount_minor if entry.direction == 'credit' else -entry.amount_minor))
    supplier_refund_cash = sum(amount for kind, amount in ledger_cash if kind == 'refund_received')
    total_cash_inflow_minor = bank_customer_receipts_minor + courier_cod_remitted_minor + supplier_refund_cash

    # Outflow
    refund_exec_filter = []
    if start_dt:
        refund_exec_filter.append(RefundExecution.executed_at >= start_dt)
    if end_dt:
        refund_exec_filter.append(RefundExecution.executed_at < end_dt)
    refunds_paid_minor = _sum(
        db,
        select(func.sum(RefundExecution.amount_minor)).where(
            and_(*refund_exec_filter)
        )
        if refund_exec_filter
        else select(func.sum(RefundExecution.amount_minor)),
    )

    supplier_payments_paid_minor = -sum(amount for kind, amount in ledger_cash if kind in {'payment', 'advance'})

    # Paid business expenses via bank/cash (not courier deductions)
    paid_exp_filter = [
        BusinessExpense.paid_date.is_not(None),
        BusinessExpense.payment_method != "courier_deduction",
    ]
    if start_date:
        paid_exp_filter.append(BusinessExpense.paid_date >= start_date)
    if end_date:
        paid_exp_filter.append(BusinessExpense.paid_date <= end_date)
    business_expenses_paid_cash_or_bank_minor = _sum(
        db,
        select(func.sum(BusinessExpense.amount_minor)).where(and_(*paid_exp_filter)),
    )

    # Courier deductions settled
    ded_filter = [CourierSettlementEntry.entry_type != "receipt"]
    if start_dt:
        ded_filter.append(CourierSettlementEntry.recorded_at >= start_dt)
    if end_dt:
        ded_filter.append(CourierSettlementEntry.recorded_at < end_dt)
    courier_deductions_settled_minor = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            and_(*ded_filter)
        ),
    )

    total_cash_outflow_minor = (
        refunds_paid_minor
        + supplier_payments_paid_minor
        + business_expenses_paid_cash_or_bank_minor
    )
    net_cash_movement_minor = total_cash_inflow_minor - total_cash_outflow_minor

    # Outstanding / Unsettled Balances
    # Courier held COD
    cod_collected_stmt = select(func.sum(Shipment.cod_amount_minor)).where(
        Shipment.cod_amount_minor > 0,
        or_(Shipment.delivered_at.is_not(None), Shipment.status == "delivered"),
    )
    total_cod_collected = _sum(db, cod_collected_stmt)
    total_cod_cleared = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            CourierSettlementEntry.entry_type == "receipt"
        ),
    )
    total_cod_deducted = _sum(
        db,
        select(func.sum(CourierSettlementEntry.amount_minor)).where(
            CourierSettlementEntry.entry_type != "receipt"
        ),
    )
    courier_held_cod_outstanding_minor = max(
        0, total_cod_collected - total_cod_cleared - total_cod_deducted
    )

    # Outstanding balances are current, not falsely presented as period-closing balances.
    from app.services.supplier_finance import get_supplier_ledger_summary
    supplier_liabilities_outstanding_minor = sum(get_supplier_ledger_summary(db, supplier_id)['outstanding_payable_minor']
        for supplier_id in db.scalars(select(SupplierLedgerEntry.supplier_id).distinct()))

    # Refund liabilities outstanding
    total_refund_liabilities = _sum(
        db,
        select(func.sum(OrderReturn.refund_amount_minor)).where(
            OrderReturn.status == "completed",
            OrderReturn.return_type == "refund_bank_transfer",
        ),
    )
    total_refund_paid = _sum(db, select(func.sum(RefundExecution.amount_minor)))
    refund_liabilities_outstanding_minor = max(
        0, total_refund_liabilities - total_refund_paid
    )

    return {
        "timezone": timezone_str,
        "start_date": start_date,
        "end_date": end_date,
        "date_basis": (
            "Delivered sales recognized by delivery date; expenses recognized by incurred date; "
            "cash movements recognized by settlement/payment date. Outstanding balances are current, not historical period closing balances. Order-list filters use placement date."
        ),
        "revenue": {
            "gross_sales_minor": gross_sales_minor,
            "shipping_revenue_minor": shipping_revenue_minor,
            "discounts_minor": discounts_minor,
            "sales_reversals_minor": sales_reversals_minor,
            "net_revenue_minor": net_revenue_minor,
            "formatted_net_revenue": _format_pkr(net_revenue_minor),
        },
        "cogs": {
            "inventory_writeoffs_minor": writeoffs_minor,
            "gross_cogs_minor": gross_cogs_minor,
            "cogs_reversals_minor": cogs_reversals_minor,
            "net_cogs_minor": net_cogs_minor,
            "formatted_net_cogs": _format_pkr(net_cogs_minor),
        },
        "freight": {
            "outbound_freight_minor": total_outbound_freight_minor,
            "rto_freight_minor": total_rto_freight_minor,
            "customer_return_freight_minor": customer_return_freight_minor,
            "total_freight_minor": total_freight_minor,
            "formatted_total_freight": _format_pkr(total_freight_minor),
            "policy_note": "AlphaZee strictly bears 100% of RTO and customer-return transport expenses.",
        },
        "overhead": {
            "packaging_minor": packaging_minor,
            "advertising_minor": advertising_minor,
            "platform_hosting_minor": platform_hosting_minor,
            "salaries_minor": salaries_minor,
            "office_supplies_minor": office_supplies_minor,
            "other_overhead_minor": other_overhead_minor,
            "total_overhead_minor": total_overhead_minor,
            "formatted_total_overhead": _format_pkr(total_overhead_minor),
        },
        "operating_result": {
            "contribution_before_overhead_minor": contribution_before_overhead_minor,
            "formatted_contribution_before_overhead": _format_pkr(
                contribution_before_overhead_minor
            ),
            "contribution_margin_percent": contribution_margin_pct,
            "total_operating_costs_minor": total_operating_costs_minor,
            "net_operating_result_minor": net_operating_result_minor,
            "formatted_net_operating_result": _format_pkr(
                net_operating_result_minor
            ),
            "disclaimer": (
                "Estimated operational snapshot based on recorded transactions and business expenses. "
                "Excludes unrecorded corporate income taxes and unallocated offline overhead."
            ),
        },
        "cash_reconciliation": {
            "bank_customer_receipts_minor": bank_customer_receipts_minor,
            "courier_cod_remitted_minor": courier_cod_remitted_minor,
            "total_cash_inflow_minor": total_cash_inflow_minor,
            "refunds_paid_minor": refunds_paid_minor,
            "supplier_payments_paid_minor": supplier_payments_paid_minor,
            "business_expenses_paid_cash_or_bank_minor": business_expenses_paid_cash_or_bank_minor,
            "courier_deductions_settled_minor": courier_deductions_settled_minor,
            "total_cash_outflow_minor": total_cash_outflow_minor,
            "net_cash_movement_minor": net_cash_movement_minor,
            "formatted_net_cash_movement": _format_pkr(net_cash_movement_minor),
            "courier_held_cod_outstanding_minor": courier_held_cod_outstanding_minor,
            "supplier_liabilities_outstanding_minor": supplier_liabilities_outstanding_minor,
            "refund_liabilities_outstanding_minor": refund_liabilities_outstanding_minor,
        },
        "total_orders_count": total_orders_count,
        "delivered_orders_count": delivered_orders_count,
        "total_shipments_count": total_shipments_count,
        "delivered_shipments_count": delivered_shipments_count,
        "rto_shipments_count": rto_shipments_count,
        "rto_rate_percent": rto_rate_percent,
    }


def get_order_economics_list(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    order_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """Return detailed per-order financial economics with line item cost attribution."""
    query = select(Order).order_by(Order.placed_at.desc())
    if order_id:
        query = query.where(Order.id == order_id)
    if status:
        query = query.where(Order.order_status == status)
    if search:
        s_pat = f"%{search.strip()}%"
        query = query.where(
            or_(
                Order.order_number.ilike(s_pat),
                Order.customer_name.ilike(s_pat),
                Order.customer_phone.ilike(s_pat),
            )
        )
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=KARACHI_TZ).astimezone(
            timezone.utc
        )
        query = query.where(Order.placed_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=KARACHI_TZ).astimezone(
            timezone.utc
        )
        query = query.where(Order.placed_at < end_dt)

    total_count = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    orders = db.scalars(query.offset(offset).limit(limit)).all()

    result: List[Dict[str, Any]] = []
    for ord_obj in orders:
        # 1. COGS & Lines
        lines_data: List[Dict[str, Any]] = []
        tot_cogs = 0
        for line in ord_obj.lines:
            tot_price = line.unit_price_minor * line.quantity
            tot_cost = line.acquisition_cost_minor if line.acquisition_cost_minor is not None else (line.unit_cost_minor or 0) * line.quantity
            tot_cogs += tot_cost
            line_contrib = tot_price - tot_cost
            var = db.scalar(select(Variant).where(Variant.id == line.variant_id))
            prod_title = line.product_title_snapshot
            sku = line.variant_sku_snapshot
            size = line.variant_size_snapshot
            color = line.variant_color_snapshot

            # Find supplier name if mapped
            sup_name = None
            sup_name = (line.acquisition_snapshot or {}).get('supplier_name')

            lines_data.append(
                {
                    "order_line_id": line.id,
                    "variant_id": line.variant_id,
                    "title": prod_title,
                    "sku": sku,
                    "size": size,
                    "color": color,
                    "quantity": line.quantity,
                    "unit_price_minor": line.unit_price_minor,
                    "unit_cost_minor": line.unit_cost_minor or 0,
                    "total_price_minor": tot_price,
                    "total_cost_minor": tot_cost,
                    "line_contribution_minor": line_contrib,
                    "ownership_source": line.ownership_source or "vendor_consignment",
                    "supplier_name": sup_name,
                }
            )

        # Include every original/replacement parcel rather than only the latest one.
        parcels = list(db.scalars(select(Shipment).where(Shipment.order_id == ord_obj.id)))
        shipment = next((parcel for parcel in parcels if parcel.replacement_return_id is None), None)
        outbound_shipping = sum(parcel.shipping_cost_minor for parcel in parcels)
        rto_cost = sum(parcel.rto_courier_cost_minor for parcel in parcels)
        returns = list(db.scalars(select(OrderReturn).where(OrderReturn.order_id == ord_obj.id)))
        parcel_ids = [parcel.id for parcel in parcels]
        return_ids = [ret.id for ret in returns]
        extra_costs = list(db.scalars(select(BusinessExpense).where(or_(
            BusinessExpense.linked_shipment_id.in_(parcel_ids), BusinessExpense.linked_return_id.in_(return_ids)))))
        extra_freight = sum(exp.amount_minor for exp in extra_costs if exp.category == 'customer_return_transport')
        attributed_overhead = sum(exp.amount_minor for exp in extra_costs
            if exp.category not in {'outbound_delivery', 'rto_transport', 'customer_return_transport'})
        total_logistics = outbound_shipping + rto_cost + extra_freight

        # 3. Supplier Charges & Payments
        charges = db.scalars(
            select(SupplierLedgerEntry).where(
                SupplierLedgerEntry.order_id == ord_obj.id,
                SupplierLedgerEntry.entry_type == "charge",
                SupplierLedgerEntry.status == "posted",
            )
        ).all()
        tot_charges = sum(c.amount_minor for c in charges)
        tot_payments = 0
        for ch in charges:
            alloc_sum = db.scalar(
                select(func.sum(SupplierPaymentAllocation.allocated_amount_minor)).where(
                    SupplierPaymentAllocation.charge_entry_id == ch.id
                )
            )
            tot_payments += int(alloc_sum or 0)
        sup_outstanding = max(0, tot_charges - tot_payments)

        # Completed returns reverse their actual cost and customer sales once.
        from app.services.stock_ownership import returned_cost
        returned_cogs = sum(ret.restocked_cost_minor if ret.restocked_cost_minor is not None
            else returned_cost(db.get(OrderLine, ret.order_line_id), ret.sellable_quantity)
            for ret in returns if ret.status == 'completed')
        refunded_sales = sum(ret.refund_amount_minor for ret in returns
            if ret.status == 'completed' and ret.return_type == 'refund_bank_transfer')
        if ord_obj.order_status == 'delivered':
            delivered_replacement_ids = {parcel.replacement_return_id for parcel in parcels
                if parcel.replacement_return_id and parcel.delivered_at}
            consumed_cost = sum((line.acquisition_cost_minor if line.acquisition_cost_minor is not None
                else (line.unit_cost_minor or 0) * line.quantity) for line in ord_obj.lines
                if line.fulfillment_kind == 'original' or line.replacement_return_id in delivered_replacement_ids)
            replacement_sales = sum(parcel.cod_amount_minor for parcel in parcels
                if parcel.replacement_return_id in delivered_replacement_ids)
            estimated_contrib = ord_obj.total_minor + replacement_sales - refunded_sales - consumed_cost + returned_cogs - total_logistics - attributed_overhead
        elif ord_obj.order_status in {'rto', 'cancelled', 'rto_initiated', 'rto_delivered'}:
            written_off = sum(returned_cost(db.get(OrderLine, allocation.reservation.order_line_id),
                allocation.damaged_quantity, allocation.sellable_quantity)
                for parcel in parcels for allocation in parcel.allocations)
            estimated_contrib = -total_logistics - attributed_overhead - written_off
        else:
            estimated_contrib = ord_obj.total_minor - tot_cogs - total_logistics - attributed_overhead

        result.append(
            {
                "order_id": ord_obj.id,
                "order_number": ord_obj.order_number,
                "placed_at": ord_obj.placed_at,
                "delivered_at": shipment.delivered_at if shipment else None,
                "order_status": ord_obj.order_status,
                "payment_method": ord_obj.payment_method,
                "payment_status": ord_obj.payment_status,
                "customer_total_minor": ord_obj.total_minor,
                "subtotal_minor": ord_obj.subtotal_minor,
                "shipping_fee_minor": ord_obj.shipping_fee_minor,
                "discount_minor": ord_obj.discount_amount_minor,
                "cogs_minor": tot_cogs,
                "outbound_shipping_cost_minor": outbound_shipping,
                "rto_courier_cost_minor": rto_cost,
                "total_logistics_cost_minor": total_logistics,
                "supplier_charges_minor": tot_charges,
                "supplier_payments_minor": tot_payments,
                "supplier_outstanding_minor": sup_outstanding,
                "estimated_contribution_minor": estimated_contrib,
                "lines": lines_data,
            }
        )

    return result, total_count


def export_order_economics_csv(
    db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None,
    status: Optional[str] = None, search: Optional[str] = None, order_id: Optional[str] = None,
) -> str:
    """Export every matching row, with the same filters as the owner table."""
    orders = []
    offset = 0
    while True:
        page, count = get_order_economics_list(db, start_date=start_date, end_date=end_date,
            status=status, search=search, order_id=order_id, limit=500, offset=offset)
        orders.extend(page)
        offset += len(page)
        if not page or offset >= count:
            break
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Order Number",
            "Placed At (UTC)",
            "Delivered At (UTC)",
            "Order Status",
            "Payment Method",
            "Payment Status",
            "Customer Total (PKR)",
            "Subtotal (PKR)",
            "Shipping Fee (PKR)",
            "Discount (PKR)",
            "Wholesale COGS (PKR)",
            "Outbound Courier Cost (PKR)",
            "RTO Courier Cost (PKR)",
            "Total Logistics (PKR)",
            "Supplier Charges (PKR)",
            "Supplier Paid (PKR)",
            "Supplier Outstanding (PKR)",
            "Estimated Contribution (PKR)",
        ]
    )

    for o in orders:
        writer.writerow(
            [
                escape_csv_cell(o["order_number"]),
                escape_csv_cell(o["placed_at"].strftime("%Y-%m-%d %H:%M:%S") if o["placed_at"] else ""),
                escape_csv_cell(o["delivered_at"].strftime("%Y-%m-%d %H:%M:%S") if o["delivered_at"] else ""),
                escape_csv_cell(o["order_status"]),
                escape_csv_cell(o["payment_method"]),
                escape_csv_cell(o["payment_status"]),
                escape_csv_cell(f"{o['customer_total_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['subtotal_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['shipping_fee_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['discount_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['cogs_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['outbound_shipping_cost_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['rto_courier_cost_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['total_logistics_cost_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['supplier_charges_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['supplier_payments_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['supplier_outstanding_minor'] / 100:.2f}"),
                escape_csv_cell(f"{o['estimated_contribution_minor'] / 100:.2f}"),
            ]
        )

    return output.getvalue()


def export_period_pnl_csv(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> str:
    """Generate CSV string of P&L and Cash Reconciliation report."""
    rep = get_period_financial_report(db, start_date=start_date, end_date=end_date)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["AlphaZee Period Financial & P&L Statement"])
    writer.writerow(["Timezone", rep["timezone"]])
    writer.writerow(["Period Start", str(rep["start_date"] or "All Time")])
    writer.writerow(["Period End", str(rep["end_date"] or "All Time")])
    writer.writerow(["Date Basis", rep["date_basis"]])
    writer.writerow([])

    # Revenue
    writer.writerow(["SECTION", "LINE ITEM", "AMOUNT (PKR)", "NOTES"])
    writer.writerow(["Revenue", "Delivered Gross Sales", f"{rep['revenue']['gross_sales_minor']/100:.2f}", "Delivered order value"])
    writer.writerow(["Revenue", "Customer Shipping Fees", f"{rep['revenue']['shipping_revenue_minor']/100:.2f}", "Delivery fees billed"])
    writer.writerow(["Revenue", "Promotional Discounts", f"-{rep['revenue']['discounts_minor']/100:.2f}", "Coupons and promos"])
    writer.writerow(["Revenue", "Sales Reversals (Refunds)", f"-{rep['revenue']['sales_reversals_minor']/100:.2f}", "Completed return refunds"])
    writer.writerow(["Revenue", "NET REVENUE", f"{rep['revenue']['net_revenue_minor']/100:.2f}", "Gross sales less reversals"])
    writer.writerow([])

    # COGS
    writer.writerow(["Cost of Goods", "Gross Wholesale COGS", f"{rep['cogs']['gross_cogs_minor']/100:.2f}", "Supplier acquisition cost"])
    writer.writerow(["Cost of Goods", "Sellable Return Reversal", f"-{rep['cogs']['cogs_reversals_minor']/100:.2f}", "Returned to active stock"])
    writer.writerow(["Cost of Goods", "NET COGS", f"{rep['cogs']['net_cogs_minor']/100:.2f}", "Net product cost"])
    writer.writerow([])

    # Freight
    writer.writerow(["Freight & Transport", "Outbound Courier Shipping", f"{rep['freight']['outbound_freight_minor']/100:.2f}", "Courier delivery cost"])
    writer.writerow(["Freight & Transport", "RTO Courier Transport", f"{rep['freight']['rto_freight_minor']/100:.2f}", "Borne 100% by AlphaZee"])
    writer.writerow(["Freight & Transport", "Customer Return Transport", f"{rep['freight']['customer_return_freight_minor']/100:.2f}", "Borne 100% by AlphaZee"])
    writer.writerow(["Freight & Transport", "TOTAL FREIGHT", f"{rep['freight']['total_freight_minor']/100:.2f}", rep['freight']['policy_note']])
    writer.writerow([])

    # Contribution
    writer.writerow(["Contribution", "Packaging & Materials", f"{rep['overhead']['packaging_minor']/100:.2f}", "Boxes, polybags, tags"])
    writer.writerow(["Contribution", "CONTRIBUTION BEFORE OVERHEAD", f"{rep['operating_result']['contribution_before_overhead_minor']/100:.2f}", f"Margin: {rep['operating_result']['contribution_margin_percent']}%"])
    writer.writerow([])

    # Overhead
    writer.writerow(["Overhead", "Advertising & Marketing", f"{rep['overhead']['advertising_minor']/100:.2f}", "Ad spend"])
    writer.writerow(["Overhead", "Platform & Hosting", f"{rep['overhead']['platform_hosting_minor']/100:.2f}", "Cloud, server, domains"])
    writer.writerow(["Overhead", "Salaries & Wages", f"{rep['overhead']['salaries_minor']/100:.2f}", "Staff compensation"])
    writer.writerow(["Overhead", "Office Supplies", f"{rep['overhead']['office_supplies_minor']/100:.2f}", "Office overhead"])
    writer.writerow(["Overhead", "Other Overhead", f"{rep['overhead']['other_overhead_minor']/100:.2f}", "Miscellaneous expenses"])
    writer.writerow(["Overhead", "TOTAL OVERHEAD", f"{rep['overhead']['total_overhead_minor']/100:.2f}", "All overhead costs"])
    writer.writerow([])

    # Net Operating Result
    writer.writerow(["Operating Result", "NET OPERATING RESULT", f"{rep['operating_result']['net_operating_result_minor']/100:.2f}", rep['operating_result']['disclaimer']])
    writer.writerow([])

    # Cash Reconciliation
    writer.writerow(["Cash Reconciliation", "Bank Customer Prepayments", f"{rep['cash_reconciliation']['bank_customer_receipts_minor']/100:.2f}", "Verified bank receipts"])
    writer.writerow(["Cash Reconciliation", "Courier COD Remitted", f"{rep['cash_reconciliation']['courier_cod_remitted_minor']/100:.2f}", "Cleared in bank"])
    writer.writerow(["Cash Reconciliation", "TOTAL CASH INFLOW", f"{rep['cash_reconciliation']['total_cash_inflow_minor']/100:.2f}", "Total receipts"])
    writer.writerow(["Cash Reconciliation", "Customer Refunds Paid", f"-{rep['cash_reconciliation']['refunds_paid_minor']/100:.2f}", "Disbursed to customers"])
    writer.writerow(["Cash Reconciliation", "Supplier Payments Paid", f"-{rep['cash_reconciliation']['supplier_payments_paid_minor']/100:.2f}", "Disbursed to suppliers"])
    writer.writerow(["Cash Reconciliation", "Expenses Paid (Bank/Cash)", f"-{rep['cash_reconciliation']['business_expenses_paid_cash_or_bank_minor']/100:.2f}", "Operating expenses paid"])
    writer.writerow(["Cash Reconciliation", "TOTAL CASH OUTFLOW", f"-{rep['cash_reconciliation']['total_cash_outflow_minor']/100:.2f}", "Total disbursements"])
    writer.writerow(["Cash Reconciliation", "NET CASH MOVEMENT", f"{rep['cash_reconciliation']['net_cash_movement_minor']/100:.2f}", "Inflows less outflows"])
    writer.writerow(["Cash Reconciliation", "Courier-Held COD (Unremitted)", f"{rep['cash_reconciliation']['courier_held_cod_outstanding_minor']/100:.2f}", "Awaiting remittance"])
    writer.writerow(["Cash Reconciliation", "Supplier Liabilities (Unpaid)", f"{rep['cash_reconciliation']['supplier_liabilities_outstanding_minor']/100:.2f}", "Awaiting payment"])
    writer.writerow(["Cash Reconciliation", "Refund Liabilities (Unpaid)", f"{rep['cash_reconciliation']['refund_liabilities_outstanding_minor']/100:.2f}", "Awaiting execution"])

    return output.getvalue()
