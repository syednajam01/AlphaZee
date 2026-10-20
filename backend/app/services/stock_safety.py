"""Shared shortage gate for storefront reads, reservations and owner resolution."""
from sqlalchemy import select, exists
from app.models.vendor_portal import VendorStockShortage
from app.models.inventory import SupplierVariant


def shortage_predicate(mapping_id):
    return exists(select(VendorStockShortage.id).where(
        VendorStockShortage.variant_id == SupplierVariant.variant_id,
        VendorStockShortage.vendor_id == SupplierVariant.supplier_id,
        SupplierVariant.id == mapping_id, VendorStockShortage.status == 'open'))


def has_open_shortage(db, mapping_id):
    return bool(db.scalar(select(shortage_predicate(mapping_id))))
