"""
SQLAlchemy ORM models for AlphaZee.

Models are defined in submodules and imported here so that:
  - Alembic's env.py can import Base.metadata via `from app.models import Base`
  - All model classes are registered with Base before any migration runs.
"""

from app.database import Base  # re-export so Alembic can find it
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant  # noqa: F401
from app.models.suppliers import Supplier, SupplierMembership, UserAccount  # noqa: F401
from app.models.inventory import (  # noqa: F401
    InventoryBalance,
    StockEvent,
    StockReservation,
    SupplierVariant,
)
from app.models.orders import Order, OrderLine, PaymentReceipt  # noqa: F401
from app.models.shipments import Shipment  # noqa: F401
from app.models.promotions import Coupon  # noqa: F401
from app.models.returns import OrderReturn  # noqa: F401

__all__ = [
    "Base",
    "Collection",
    "Product",
    "Variant",
    "AvailabilityStatus",
    "UserAccount",
    "Supplier",
    "SupplierMembership",
    "SupplierVariant",
    "InventoryBalance",
    "StockEvent",
    "StockReservation",
    "Order",
    "OrderLine",
    "PaymentReceipt",
    "Shipment",
    "Coupon",
    "OrderReturn",
]



