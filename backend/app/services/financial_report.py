"""Owner financial view, explicitly separating sales, cash and liabilities.

All amounts use PKR minor units. This is an all-time operational snapshot: sales use
current delivered status, cash uses recorded receipts and refund executions, and
expenses use recorded courier costs. It is not a tax or accrual accounting export.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.finance import CourierSettlementEntry, RefundExecution
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment


def _sum(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def get_financial_summary(db: Session) -> dict:
    valid_order = Order.order_status != 'cancelled'
    delivered = Order.order_status == 'delivered'
    order_value = _sum(db, select(func.sum(Order.total_minor)).where(valid_order))
    original_sales = _sum(db, select(func.sum(Order.total_minor)).where(delivered))
    replacement_sales = _sum(db, select(func.sum(Shipment.cod_amount_minor)).where(
        Shipment.replacement_return_id.is_not(None), Shipment.status == 'delivered'))
    delivered_sales = original_sales + replacement_sales
    bank_payments = _sum(db, select(func.sum(Order.total_minor)).where(
        Order.payment_method == 'bank_transfer',
        or_(Order.payment_verified_at.is_not(None), Order.payment_status.in_(['verified', 'refunded']))))
    cod_collected = _sum(db, select(func.sum(Shipment.cod_amount_minor)).where(
        Shipment.cod_amount_minor > 0,
        or_(Shipment.delivered_at.is_not(None), Shipment.status == 'delivered')))
    courier_cash = _sum(db, select(func.sum(CourierSettlementEntry.amount_minor)).where(
        CourierSettlementEntry.entry_type == 'receipt'))
    courier_deductions = _sum(db, select(func.sum(CourierSettlementEntry.amount_minor)).where(
        CourierSettlementEntry.entry_type != 'receipt'))
    other_deductions = _sum(db, select(func.sum(CourierSettlementEntry.amount_minor)).where(
        CourierSettlementEntry.entry_type == 'other_deduction'))
    cod_outstanding = max(0, cod_collected - courier_cash - courier_deductions)

    sales_reversals = _sum(db, select(func.sum(OrderReturn.refund_amount_minor)).where(
        OrderReturn.status == 'completed', OrderReturn.return_type == 'refund_bank_transfer'))
    refund_paid = _sum(db, select(func.sum(RefundExecution.amount_minor)))
    refund_outstanding = max(0, sales_reversals - refund_paid)

    original_cogs = _sum(db, select(func.sum(OrderLine.unit_cost_minor * OrderLine.quantity))
        .join(Order, OrderLine.order_id == Order.id).where(delivered,
            OrderLine.fulfillment_kind == 'original'))
    return_cogs_reversal = _sum(db, select(func.sum(OrderLine.unit_cost_minor * OrderReturn.sellable_quantity))
        .join(OrderReturn, OrderReturn.order_line_id == OrderLine.id).join(
            Order, Order.id == OrderLine.order_id).where(delivered,
            OrderReturn.status == 'completed'))
    replacement_cogs = _sum(db, select(func.sum(OrderLine.unit_cost_minor * OrderLine.quantity))
        .join(Shipment, Shipment.replacement_return_id == OrderLine.replacement_return_id).where(
            OrderLine.fulfillment_kind == 'replacement', Shipment.status == 'delivered'))
    cogs = original_cogs - return_cogs_reversal + replacement_cogs
    outbound_cost = _sum(db, select(func.sum(Shipment.shipping_cost_minor)))
    rto_cost = _sum(db, select(func.sum(Shipment.rto_courier_cost_minor)))
    courier_expenses = outbound_cost + rto_cost
    net_sales = delivered_sales - sales_reversals
    contribution = net_sales - cogs - courier_expenses - other_deductions
    total_shipments = _sum(db, select(func.count(Shipment.id)))
    rto_shipments = _sum(db, select(func.count(Shipment.id)).where(
        Shipment.status.in_(['rto_initiated', 'rto_delivered'])))
    delivered_shipments = _sum(db, select(func.count(Shipment.id)).where(
        Shipment.status == 'delivered'))
    return {
        'order_value_minor': order_value,
        'delivered_sales_minor': delivered_sales,
        'bank_customer_payments_minor': bank_payments,
        'cod_collected_minor': cod_collected,
        'courier_held_cod_minor': cod_outstanding,
        'courier_deductions_minor': courier_deductions,
        'other_deductions_minor': other_deductions,
        'business_cash_received_minor': bank_payments + courier_cash - refund_paid,
        'refund_paid_minor': refund_paid,
        'refund_outstanding_minor': refund_outstanding,
        'sales_reversals_minor': sales_reversals,
        'cogs_reversals_minor': return_cogs_reversal,
        'gross_revenue_minor': delivered_sales,
        'net_revenue_minor': net_sales,
        'refund_total_minor': sales_reversals,
        'subtotal_revenue_minor': _sum(db, select(func.sum(Order.subtotal_minor)).where(delivered)),
        'shipping_revenue_minor': _sum(db, select(func.sum(Order.shipping_fee_minor)).where(delivered)),
        'cogs_minor': cogs,
        'outbound_courier_cost_minor': outbound_cost,
        'rto_courier_cost_minor': rto_cost,
        'total_courier_expenses_minor': courier_expenses,
        'gross_profit_minor': contribution,
        'total_orders_count': _sum(db, select(func.count(Order.id)).where(valid_order)),
        'total_shipments_count': total_shipments,
        'delivered_shipments_count': delivered_shipments,
        'rto_shipments_count': rto_shipments,
        'rto_rate_percent': round(rto_shipments / total_shipments * 100, 2) if total_shipments else 0.0,
        'cod_pending_remittance_minor': cod_outstanding,
        'cod_remitted_minor': courier_cash,
    }
