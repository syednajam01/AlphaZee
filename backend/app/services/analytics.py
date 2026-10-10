"""
analytics.py — Financial profit & loss calculation, COGS aggregation, and unit economics reporting.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.orders import Order, OrderLine
from app.models.shipments import Shipment


def get_profit_loss_summary(db: Session) -> dict:
    """
    Compute real-time financial economics:
    - Gross revenue from valid orders (placed/confirmed/dispatched/delivered, excluding cancelled)
    - Wholesale Cost of Goods Sold (COGS) from purchase-time snapshots
    - Customer shipping fees collected
    - Outbound and RTO courier costs incurred
    - Net Gross Profit (in integer paisas)
    - Return-to-Origin (RTO) rate percentage
    - COD Cash Remittance progress
    """
    # 1. Orders financial totals
    order_stmt = select(
        func.coalesce(func.sum(Order.total_minor), 0).label("gross_revenue"),
        func.coalesce(func.sum(Order.subtotal_minor), 0).label("subtotal_revenue"),
        func.coalesce(func.sum(Order.discount_amount_minor), 0).label("discount_total"),
        func.coalesce(func.sum(Order.shipping_fee_minor), 0).label("shipping_revenue"),
        func.count(Order.id).label("total_orders"),
    ).where(Order.order_status.in_(["placed", "confirmed", "dispatched", "delivered"]))

    res_orders = db.execute(order_stmt).one()
    gross_revenue_minor = int(res_orders.gross_revenue)
    subtotal_revenue_minor = int(res_orders.subtotal_revenue)
    discount_total_minor = int(res_orders.discount_total)
    shipping_revenue_minor = int(res_orders.shipping_revenue)
    total_orders_count = int(res_orders.total_orders)

    # 2. COGS (Cost of Goods Sold) from line item snapshots
    cogs_stmt = (
        select(func.coalesce(func.sum(OrderLine.unit_cost_minor * OrderLine.quantity), 0))
        .join(Order, OrderLine.order_id == Order.id)
        .where(Order.order_status.in_(["placed", "confirmed", "dispatched", "delivered"]))
    )
    cogs_minor = int(db.scalar(cogs_stmt) or 0)

    # 3. Courier expenses and RTO metrics from shipments
    ship_stmt = select(
        func.coalesce(func.sum(Shipment.shipping_cost_minor), 0).label("outbound_cost"),
        func.coalesce(func.sum(Shipment.rto_courier_cost_minor), 0).label("rto_cost"),
        func.count(Shipment.id).label("total_shipments"),
        func.coalesce(
            func.sum(
                case(
                    (Shipment.status.in_(["rto_initiated", "rto_delivered"]), 1),
                    else_=0,
                )
            ),
            0,
        ).label("rto_shipments"),
        func.coalesce(
            func.sum(
                case(
                    (Shipment.status == "delivered", 1),
                    else_=0,
                )
            ),
            0,
        ).label("delivered_shipments"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (Shipment.cod_remittance_status == "pending_remittance")
                        & (Shipment.status == "delivered"),
                        Shipment.cod_amount_minor,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("cod_pending_minor"),
        func.coalesce(
            func.sum(
                case(
                    (Shipment.cod_remittance_status == "remitted", Shipment.cod_remitted_amount_minor),
                    else_=0,
                )
            ),
            0,
        ).label("cod_remitted_minor"),
    )

    res_ship = db.execute(ship_stmt).one()
    outbound_courier_cost_minor = int(res_ship.outbound_cost)
    rto_courier_cost_minor = int(res_ship.rto_cost)
    total_courier_expenses_minor = outbound_courier_cost_minor + rto_courier_cost_minor
    total_shipments_count = int(res_ship.total_shipments)
    rto_shipments_count = int(res_ship.rto_shipments)
    delivered_shipments_count = int(res_ship.delivered_shipments)
    cod_pending_remittance_minor = int(res_ship.cod_pending_minor)
    cod_remitted_minor = int(res_ship.cod_remitted_minor)

    # Calculate Net Gross Profit
    gross_profit_minor = gross_revenue_minor - cogs_minor - total_courier_expenses_minor

    # RTO Rate
    if total_shipments_count > 0:
        rto_rate_percent = round((rto_shipments_count / total_shipments_count) * 100.0, 2)
    else:
        rto_rate_percent = 0.0

    return {
        "gross_revenue_minor": gross_revenue_minor,
        "subtotal_revenue_minor": subtotal_revenue_minor,
        "discount_total_minor": discount_total_minor,
        "shipping_revenue_minor": shipping_revenue_minor,
        "cogs_minor": cogs_minor,
        "outbound_courier_cost_minor": outbound_courier_cost_minor,
        "rto_courier_cost_minor": rto_courier_cost_minor,
        "total_courier_expenses_minor": total_courier_expenses_minor,
        "gross_profit_minor": gross_profit_minor,
        "total_orders_count": total_orders_count,
        "total_shipments_count": total_shipments_count,
        "delivered_shipments_count": delivered_shipments_count,
        "rto_shipments_count": rto_shipments_count,
        "rto_rate_percent": rto_rate_percent,
        "cod_pending_remittance_minor": cod_pending_remittance_minor,
        "cod_remitted_minor": cod_remitted_minor,
    }


def get_marketing_attribution_summary(db: Session) -> list[dict]:
    """
    Aggregate orders, revenue, discounts, and performance by marketing UTM campaign/source.
    """
    stmt = (
        select(
            func.coalesce(Order.utm_source, "direct").label("source"),
            func.coalesce(Order.utm_medium, "none").label("medium"),
            func.coalesce(Order.utm_campaign, "none").label("campaign"),
            func.count(Order.id).label("orders_count"),
            func.coalesce(func.sum(Order.total_minor), 0).label("revenue_minor"),
            func.coalesce(func.sum(Order.discount_amount_minor), 0).label("discount_minor"),
        )
        .where(Order.order_status.in_(["placed", "confirmed", "dispatched", "delivered"]))
        .group_by(Order.utm_source, Order.utm_medium, Order.utm_campaign)
        .order_by(func.sum(Order.total_minor).desc())
    )

    rows = db.execute(stmt).all()
    results = []
    for r in rows:
        results.append(
            {
                "utm_source": r.source,
                "utm_medium": r.medium,
                "utm_campaign": r.campaign,
                "orders_count": int(r.orders_count),
                "revenue_minor": int(r.revenue_minor),
                "discount_minor": int(r.discount_minor),
            }
        )
    return results
