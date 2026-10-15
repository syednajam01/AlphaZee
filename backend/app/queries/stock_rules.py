"""The physical hold predicate shared by inventory, checkout and owner displays."""
from sqlalchemy import or_
from app.models.inventory import StockReservation, OPEN_RESERVATION_STAGES


def holding_predicate():
    return or_(StockReservation.stage.in_(OPEN_RESERVATION_STAGES), StockReservation.legacy_stock_hold.is_(True))
