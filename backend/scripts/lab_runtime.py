"""Guarded SAMPLE acceptance setup; real lab owners use provision_owner.py interactively."""
import argparse,json,re,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.engine import make_url
from sqlalchemy import select,text
from app.config import settings
from app.database import SessionLocal
from app.services.owners import provision_owner
from app.models.orders import Order

def guard():
    if not settings.checkout_lab or not settings.checkout_enabled or make_url(settings.database_url).database!='alphazee_checkout_test':
        raise RuntimeError('Only the isolated checkout lab is accepted')

def main():
    guard();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provision');parser.add_argument('--expire');parser.add_argument('--verify',action='store_true');parser.add_argument('--snapshot-token');args=parser.parse_args()
    with SessionLocal() as db:
        if args.provision:
            if not re.fullmatch('sample_m8_[a-f0-9]{8}',args.provision):raise ValueError('Only SAMPLE acceptance owners')
            provision_owner(db,args.provision,sys.stdin.read().strip());db.commit();print('{"provisioned":true}')
        elif args.expire:
            import uuid
            order=db.get(Order,uuid.UUID(args.expire))
            if not order or not order.customer_name.startswith('SAMPLE M8 ') or order.payment_method!='bank_transfer' or not order.payment_instructions_sent_at:
                raise ValueError('Only SAMPLE orders with a simulated instruction handoff')
            order.payment_deadline_at=datetime.now(timezone.utc)-timedelta(minutes=1);db.commit();print('{"sample_expired":true}')
        elif args.verify:
            print(json.dumps({'database':make_url(settings.database_url).database,'checkout_enabled':settings.checkout_enabled,
                'rows':{table:db.scalar(text('SELECT count(*) FROM '+table)) for table in ('products','media_assets','orders','stock_reservations')}}))
        elif args.snapshot_token:
            import hashlib
            from app.models.catalog import Product
            from app.models.media import MediaAsset
            from app.services.media_storage import object_path
            from app.queries.catalog_stock import variant_stock
            token=args.snapshot_token
            if not re.fullmatch('[a-f0-9]{8}',token):raise ValueError('SAMPLE token required')
            product=db.scalar(select(Product).where(Product.slug=='sample-m8-'+token))
            if not product:raise ValueError('SAMPLE product missing')
            assets=set(link.asset_id for link in product.media_links)
            media=[]
            for identifier in sorted(assets):
                asset=db.get(MediaAsset,identifier);digest=hashlib.sha256(object_path(asset.storage_key).read_bytes()).hexdigest()
                if digest!=asset.checksum:raise ValueError('Persisted media checksum differs')
                media.append({'id':asset.id,'checksum':digest,'poster_id':asset.poster_id})
            stocks=[variant_stock(db,v.id)['mapping'] for v in sorted(product.variants,key=lambda v:v.id)]
            orders=list(db.scalars(select(Order).where(Order.customer_name=='SAMPLE M8 '+token).order_by(Order.placed_at)))
            assert len(orders)==4 and [o.order_status for o in orders]==['delivered','confirmed','cancelled','cancelled']
            assert stocks[0]['physical_on_hand']==20 and stocks[0]['held_reservations']==1 and stocks[0]['available_to_sell']==19
            assert stocks[1]['physical_on_hand']==19 and stocks[1]['held_reservations']==0
            print(json.dumps({'product_id':product.id,'status':product.status,'media':media,
                'stock':[{'physical':s['physical_on_hand'],'held':s['held_reservations'],'available':s['available_to_sell']} for s in stocks],
                'order_states':[o.order_status for o in orders],'schema_head':db.scalar(text('SELECT version_num FROM alembic_version'))}))

if __name__=='__main__':main()
