"""API endpoints for VF4 Financial Reports, Period P&L, Per-Order Economics, and CSV Exports."""

from datetime import date, datetime
from typing import Annotated, Optional, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, require_owner_session
from app.schemas.financial_report import (
    OrderEconomicsListResponse,
    PeriodFinancialReportResponse,
)
from app.services import financial_report as report_service

router = APIRouter(
    prefix="/admin/reports",
    tags=["Financial Reports"],
    dependencies=[Depends(require_owner_session)],
)


@router.get(
    "/period",
    response_model=PeriodFinancialReportResponse,
    summary="Get period financial statement, P&L, operating results, and cash reconciliation",
)
def get_period_report_endpoint(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD) inclusive in Asia/Karachi"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD) inclusive in Asia/Karachi"),
    timezone: Literal["Asia/Karachi"] = Query("Asia/Karachi", description="Reporting timezone for day boundaries"),
    db: Session = Depends(get_db),
) -> PeriodFinancialReportResponse:
    report_dict = report_service.get_period_financial_report(
        db, start_date=start_date, end_date=end_date, timezone_str=timezone
    )
    return PeriodFinancialReportResponse.model_validate(report_dict)


@router.get(
    "/orders",
    response_model=OrderEconomicsListResponse,
    summary="Get detailed per-order economics, line-item cost attribution, and estimated contribution",
)
def get_order_economics_endpoint(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    order_id: Optional[str] = Query(None, description="Filter by exact order ID"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by order number or customer name"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
) -> OrderEconomicsListResponse:
    items, total = report_service.get_order_economics_list(
        db,
        start_date=start_date,
        end_date=end_date,
        order_id=order_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return OrderEconomicsListResponse(
        orders=items,
        total_orders=total,
        page=(offset // limit) + 1,
        limit=limit,
    )


@router.get(
    "/orders/export",
    summary="Export order economics to CSV with formula injection escaping",
)
def export_order_economics_csv_endpoint(
    start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None),
    status_filter: Optional[str] = Query(None, alias='status'), search: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None), db: Session = Depends(get_db),
) -> Response:
    csv_data = report_service.export_order_economics_csv(db, start_date=start_date, end_date=end_date,
        status=status_filter, search=search, order_id=order_id)
    filename = f"alphazee_order_economics_{date.today().isoformat()}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/period/export",
    summary="Export period financial statement and P&L to CSV with formula injection escaping",
)
def export_period_pnl_csv_endpoint(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> Response:
    csv_data = report_service.export_period_pnl_csv(
        db, start_date=start_date, end_date=end_date
    )
    filename = f"alphazee_financial_pnl_{date.today().isoformat()}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
