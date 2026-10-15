"""Synthetic reservation proof ONLY in the isolated, checkout-disabled Compose DB."""
import json
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_m3_media_runtime import guard
from app.config import settings
from app.database import SessionLocal
from app.models.catalog import Variant
from app.models.inventory import StockReservation
from app.queries.inventory import get_active_supplier_variant
from app.services.orders import place_order, CreateOrderDTO, OrderItemDTO


def main():
    guard()
    assert settings.database_url.endswith('/alphazee_m3_media_test')
    identifier = int(sys.argv[1])
    with SessionLocal() as db:
        variant = db.get(Variant, identifier)
        assert variant and variant.sku.startswith('SAMPLE-M4-'), 'Only isolated browser SAMPLE variants are permitted'
        supplier_variant = get_active_supplier_variant(db, identifier)
        orders = []
        for quantity in (2, 3):
            order = place_order(db, CreateOrderDTO(customer_name='SAMPLE M5 simulation', customer_phone='03001234567',
                shipping_address_line1='SAMPLE fixture street', shipping_city='Lahore', shipping_province='Punjab',
                payment_method='cod', items=[OrderItemDTO(identifier, quantity)]))
            orders.append({'id': str(order.id), 'number': order.order_number})
        db.add(StockReservation(supplier_variant_id=supplier_variant.id, order_line_id=uuid.uuid4(),
            quantity=1, stage='dispatched', legacy_stock_hold=True))
        db.commit()
    print(json.dumps({'orders':orders, 'simulated_orders':True, 'development_modified':False}))


if __name__ == '__main__': main()
