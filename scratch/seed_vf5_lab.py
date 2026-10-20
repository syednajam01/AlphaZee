"""Seed lab database with a clean vendor-managed product and variants for VF5 browser verification."""
import subprocess
import sys

LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']

PY_SCRIPT = """
import uuid
import secrets
from app.database import SessionLocal
from app.models.suppliers import Supplier
from app.models.catalog import Product, Variant, Collection, AvailabilityStatus
from app.models.inventory import SupplierVariant, InventoryBalance, StockReservation
from app.models.orders import Order, OrderLine

db = SessionLocal()
try:
    # 1. Supplier
    sup = db.query(Supplier).filter(Supplier.slug == 'vendor-denim-vf5').first()
    if not sup:
        sup = Supplier(
            id=uuid.uuid4(),
            name='Vendor Denim Craft (VF5)',
            slug='vendor-denim-vf5',
            status='active',
            supplier_type='external_vendor',
            notes='Primary denim partner for VF5 stock portal acceptance',
        )
        db.add(sup)
        db.flush()

    # 2. Collection
    col = db.get(Collection, 'essentials')
    if not col:
        col = Collection(
            id='essentials',
            slug='essentials',
            name='Essentials',
            is_active=True,
            display_order=1,
        )
        db.add(col)
        db.flush()

    # 3. Product
    prod_id = 'prod-vf5-denim'
    prod = db.get(Product, prod_id)
    if not prod:
        prod = Product(
            id=prod_id,
            title='VF5 Raw Indigo Denim',
            slug='vf5-raw-indigo-denim',
            collection_id=col.id,
            status='published',
            stock_management_source='vendor_managed',
            vendor_id=sup.id,
        )
        db.add(prod)
        db.flush()

    # 4. Variant 1 (Size 32, on_hand=3, holds=1)
    sku1 = 'VF5-DNM-32'
    var1 = db.query(Variant).filter(Variant.sku == sku1).first()
    if not var1:
        var1 = Variant(
            product_id=prod.id,
            sku=sku1,
            size='32',
            color='Indigo',
            price_minor=450000,
            availability=AvailabilityStatus.AVAILABLE,
            is_active=True,
        )
        db.add(var1)
        db.flush()

    sv1 = db.query(SupplierVariant).filter(SupplierVariant.variant_id == var1.id, SupplierVariant.supplier_id == sup.id).first()
    if not sv1:
        sv1 = SupplierVariant(
            supplier_id=sup.id,
            variant_id=var1.id,
            active=True,
            supplier_cost_minor=280000,
        )
        db.add(sv1)
        db.flush()

    bal1 = db.get(InventoryBalance, sv1.id)
    if not bal1:
        bal1 = InventoryBalance(supplier_variant_id=sv1.id, on_hand=3, version=0)
        db.add(bal1)
        db.flush()
    else:
        bal1.on_hand = 3
        bal1.version = 0

    # Create 1 customer hold on var1
    order_num = f'AZ-VF5-HOLD-{secrets.token_hex(3)}'
    order = Order(
        order_number=order_num,
        order_status='confirmed',
        customer_name='Ayesha Khan',
        customer_phone='03009876543',
        shipping_address_line1='42 Gulberg III',
        shipping_city='Lahore',
        shipping_province='Punjab',
        total_minor=450000,
        subtotal_minor=450000,
        payment_method='cod',
        payment_status='pending',
    )
    db.add(order)
    db.flush()

    line = OrderLine(
        order_id=order.id,
        variant_id=var1.id,
        product_title_snapshot=prod.title,
        variant_sku_snapshot=var1.sku,
        quantity=1,
        unit_price_minor=450000,
        line_total_minor=450000,
    )
    db.add(line)
    db.flush()

    hold = StockReservation(
        order_line_id=line.id,
        supplier_variant_id=sv1.id,
        quantity=1,
        stage='held',
        legacy_stock_hold=False,
    )
    db.add(hold)

    # 5. Variant 2 (Size 34, on_hand=5, holds=0)
    sku2 = 'VF5-DNM-34'
    var2 = db.query(Variant).filter(Variant.sku == sku2).first()
    if not var2:
        var2 = Variant(
            product_id=prod.id,
            sku=sku2,
            size='34',
            color='Indigo',
            price_minor=450000,
            availability=AvailabilityStatus.AVAILABLE,
            is_active=True,
        )
        db.add(var2)
        db.flush()

    sv2 = db.query(SupplierVariant).filter(SupplierVariant.variant_id == var2.id, SupplierVariant.supplier_id == sup.id).first()
    if not sv2:
        sv2 = SupplierVariant(
            supplier_id=sup.id,
            variant_id=var2.id,
            active=True,
            supplier_cost_minor=280000,
        )
        db.add(sv2)
        db.flush()

    bal2 = db.get(InventoryBalance, sv2.id)
    if not bal2:
        bal2 = InventoryBalance(supplier_variant_id=sv2.id, on_hand=5, version=0)
        db.add(bal2)
    else:
        bal2.on_hand = 5

    db.commit()
    print(f"SUCCESS: Supplier '{sup.name}' id={sup.id} seeded with 2 variants.")
except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    db.close()
"""

cmd = LAB_COMPOSE + ['exec', '-T', 'api', 'python', '-c', PY_SCRIPT]
res = subprocess.run(cmd, capture_output=True, text=True, check=True)
print(res.stdout)
