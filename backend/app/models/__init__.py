"""
SQLAlchemy ORM models for AlphaZee.

Models are defined in submodules and imported here so that:
  - Alembic's env.py can import Base.metadata via `from app.models import Base`
  - All model classes are registered with Base before any migration runs.
"""

from app.database import Base  # re-export so Alembic can find it
from app.models.media import MediaAsset, ProductMedia  # noqa: F401
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant  # noqa: F401
from app.models.suppliers import Supplier, SupplierMembership, UserAccount  # noqa: F401
from app.models.inventory import (  # noqa: F401
    InventoryBalance,
    StockEvent,
    StockReservation,
    SupplierVariant,
)
from app.models.orders import Order, OrderLine, PaymentReceipt  # noqa: F401
from app.models.owned_stock import OwnedStockLot, OwnedStockAllocation  # noqa: F401
from app.models.shipments import Shipment, ShipmentAllocation  # noqa: F401
from app.models.promotions import Coupon  # noqa: F401
from app.models.returns import OrderReturn  # noqa: F401
from app.models.auth import OwnerCredential, OwnerSession, OwnerLoginBucket  # noqa: F401
from app.models.order_access import OrderAccessGrant, OrderAccessSession, OrderAccessAttempt  # noqa: F401
from app.models.finance import CourierSettlementEntry, RefundExecution  # noqa: F401
from app.models.supplier_finance import SupplierAgreement, SupplierLedgerEntry, SupplierPaymentAllocation  # noqa: F401
from app.models.business_expenses import BusinessExpense  # noqa: F401
from app.models.vendor_portal import (  # noqa: F401
    VendorUser,
    VendorSession,
    VendorLoginBucket,
    VendorStockShortage,
)
from app.models.store_settings import (  # noqa: F401
    StoreSettings,
    StoreSettingsAuditLog,
    OwnerPreference,
)

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
    "ShipmentAllocation",
    "Coupon",
    "OrderReturn",
    "OrderAccessGrant",
    "OrderAccessSession",
    "OrderAccessAttempt",
    "CourierSettlementEntry",
    "RefundExecution",
    "SupplierAgreement",
    "SupplierLedgerEntry",
    "SupplierPaymentAllocation",
    "BusinessExpense",
    "VendorUser",
    "VendorSession",
    "VendorLoginBucket",
    "VendorStockShortage",
    "StoreSettings",
    "StoreSettingsAuditLog",
    "OwnerPreference",
]



