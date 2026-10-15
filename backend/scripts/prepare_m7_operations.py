"""Synthetic owner-operation fixtures, restricted to the existing isolated test DB."""
from datetime import datetime,timedelta,timezone
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.config import settings
from app.database import SessionLocal
from app.models.auth import OwnerCredential
from app.models.catalog import Collection,Product,Variant,AvailabilityStatus
from app.models.inventory import InventoryBalance,SupplierVariant
from app.models.suppliers import Supplier
from app.models.orders import Order
from app.services.orders import (place_order,CreateOrderDTO,OrderItemDTO,confirm_supplier_acceptance,
    record_payment_instructions_sent,upload_payment_receipt)
from app.services.shipments import create_shipment,update_shipment_status
from app.services.returns import create_return_request
from verify_m3_media_runtime import guard


def main():
    guard()
    if not settings.database_url.endswith('/alphazee_m3_media_test') or not settings.bank_transfer_enabled:
        raise RuntimeError('Requires the isolated M7 Compose override and test bank settings')
    if sys.argv[1]=='--proof':
        with SessionLocal() as db:
            bank=db.get(Order,__import__('uuid').UUID(sys.argv[2]))
            if not bank or not bank.customer_name.startswith('SAMPLE M7 '):raise RuntimeError('Only SAMPLE M7 orders accepted')
            receipt=upload_payment_receipt(db,order_id=bank.id,receipt_image_url='/favicon.svg',bank_reference='SAMPLE-M7-PROOF')
            db.commit();print(json.dumps({'receipt_id':str(receipt.id)}));return
    username,token=sys.argv[1:]
    if not re.fullmatch(r'sample_m4_[a-f0-9]{8}',username) or not re.fullmatch(r'[a-f0-9]{8}',token):
        raise RuntimeError('Only fresh SAMPLE browser fixtures are accepted')
    with SessionLocal() as db:
        owner=db.scalar(select(OwnerCredential).where(OwnerCredential.username==username))
        if not owner:raise RuntimeError('Provision the isolated browser owner first')
        col=Collection(id='sample-m7-'+token,slug='sample-m7-'+token,name='SAMPLE M7 '+token)
        db.add(col);db.flush()
        product=Product(id='sample-m7-'+token,slug='sample-m7-'+token,title='SAMPLE M7 '+token,
                        collection_id=col.id,description='SAMPLE operations simulation',status='published',is_active=True)
        supplier=Supplier(name='SAMPLE M7 '+token,slug='sample-m7-'+token,status='active')
        db.add_all([product,supplier]);db.flush()
        variants=[]
        for size in ('M','L'):
            v=Variant(product_id=product.id,sku='SAMPLE-M7-'+token+'-'+size,size=size,color='Blue',
                      price_minor=12345,is_active=True,availability=AvailabilityStatus.AVAILABLE)
            db.add(v);db.flush();link=SupplierVariant(supplier_id=supplier.id,variant_id=v.id,supplier_cost_minor=5000,active=True)
            db.add(link);db.flush();db.add(InventoryBalance(supplier_variant_id=link.id,on_hand=100,version=1));variants.append(v)
        db.flush()
        def make(kind='cod',quantity=1):
            return place_order(db,CreateOrderDTO(customer_name='SAMPLE M7 '+token,customer_phone='03001234567',
                shipping_address_line1='SAMPLE fixture street',shipping_city='Lahore',shipping_province='Punjab',
                payment_method=kind,items=[OrderItemDTO(variants[0].id,quantity)]))
        cod=make(quantity=2);bank=make('bank_transfer');rto=make();cancel=make()
        expired=make('bank_transfer');confirm_supplier_acceptance(db,order_id=expired.id,supplier_notes='SAMPLE accepted')
        record_payment_instructions_sent(db,order_id=expired.id,actor_user_id=owner.user_id,channel='other',reference='SAMPLE simulated handoff')
        expired.payment_deadline_at=datetime.now(timezone.utc)-timedelta(minutes=1)
        delivered=make(quantity=2);confirm_supplier_acceptance(db,order_id=delivered.id,supplier_notes='SAMPLE accepted')
        shipment=create_shipment(db,order_id=delivered.id,courier_code='manual',tracking_number='SAMPLE-M7-DEL-'+token,actor_user_id=owner.user_id)
        update_shipment_status(db,shipment_id=shipment.id,status='delivered',actor_user_id=owner.user_id)
        refund=create_return_request(db,order_id=delivered.id,order_line_id=delivered.lines[0].id,
            return_type='refund_bank_transfer',reason='changed_mind',quantity=1)
        exchange=create_return_request(db,order_id=delivered.id,order_line_id=delivered.lines[0].id,
            return_type='size_exchange',reason='size_too_small',quantity=1,exchange_variant_id=variants[1].id)
        db.commit()
        result={name:{'id':str(row.id),'number':getattr(row,'order_number',None)} for name,row in
                [('cod',cod),('bank',bank),('rto',rto),('cancel',cancel),('expired',expired),('delivered',delivered),('refund',refund),('exchange',exchange)]}
        result.update({'database':'alphazee_m3_media_test','development_modified':False,'token':token})
        print(json.dumps(result))


if __name__=='__main__':main()
