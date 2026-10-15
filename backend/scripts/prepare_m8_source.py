"""SAMPLE catalog transfer acceptance source, confined to the old isolated media DB."""
import hashlib,io,json,re,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile,Headers
from verify_m3_media_runtime import guard,make_video
from app.database import SessionLocal,engine
from app.services.owners import provision_owner
from app.services import media
from app.services.owner_catalog import create_collection,create_product,transition
from app.services.catalog_transfer import export_bundle
from app.schemas.owner_catalog import CollectionCreate,ProductCreate,VersionCommand
from app.schemas.media import ProductMediaCommand,MediaLink,PosterCommand
from app.models.inventory import SupplierVariant,InventoryBalance
from app.models.suppliers import Supplier

def main():
    guard();token=sys.argv[1]
    if not re.fullmatch('[a-f0-9]{8}',token):raise ValueError('Fresh SAMPLE token required')
    password=sys.stdin.read().strip()
    with SessionLocal() as db:
        owner=provision_owner(db,'sample_m8_'+token,password);db.commit()
        principal=SimpleNamespace(owner=owner)
        stream=io.BytesIO();Image.new('RGB',(80,60),'#123456').save(stream,'PNG');stream.seek(0)
        image=media.ingest(db,UploadFile(stream,filename='SAMPLE-M8.png',headers=Headers({'content-type':'image/png'})),principal)
        with tempfile.TemporaryDirectory() as folder:
            video=make_video(Path(folder)/'sample.mp4','libx264')
            clip=media.ingest(db,UploadFile(io.BytesIO(video),filename='SAMPLE-M8.mp4',headers=Headers({'content-type':'video/mp4'})),principal)
        media.set_poster(db,clip['id'],PosterCommand(expected_version=1,poster_id=image['id']))
        col=create_collection(db,CollectionCreate(name='SAMPLE M8 '+token,slug='sample-m8-'+token,image_media_id=image['id']))
        p=create_product(db,ProductCreate(title='SAMPLE M8 '+token,slug='sample-m8-'+token,description='SAMPLE checkout walkthrough',
            collection_id=col.id,variants=[{'sku':'SAMPLE-M8-'+token+'-'+s,'size':s,'color':'Blue','price_minor':12345,'is_active':True,'availability':'available'} for s in ('M','L')]))
        media.replace_product_media(db,p.id,ProductMediaCommand(expected_version=1,items=[MediaLink(asset_id=image['id'],role='primary'),MediaLink(asset_id=clip['id'],role='gallery',variant_id=p.variants[0].id)]))
        transition(db,p.id,VersionCommand(expected_version=2),'publish')
        supplier=Supplier(name='SAMPLE PRIVATE CONTACT MUST NOT COPY',slug='sample-m8-'+token,status='active',notes='PRIVATE SUPPLIER NOTES')
        db.add(supplier);db.flush()
        for v in p.variants:
            mapping=SupplierVariant(supplier_id=supplier.id,variant_id=v.id,supplier_cost_minor=5000,active=True)
            db.add(mapping);db.flush();db.add(InventoryBalance(supplier_variant_id=mapping.id,on_hand=73,version=1))
        db.commit();product_id=p.id
    def snapshot(connection):
        return {table:connection.scalar(text('SELECT count(*) FROM '+table)) for table in ('products','orders','owner_credentials','supplier_variants','stock_events')}
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            connection.execute(text('SET TRANSACTION READ ONLY'));before=snapshot(connection)
            with Session(bind=connection) as db:bundle=export_bundle(db,[product_id],'/tmp/m8-'+token+'.zip',True)
            assert before==snapshot(connection)
    print(json.dumps({'product_id':product_id,'archive':'/tmp/m8-'+token+'.zip','source_rows_unchanged_by_export':True,
        'assets':[{'id':a.id,'checksum':a.checksum,'kind':'video' if a.content_type.startswith('video/') else 'image'} for a in bundle.assets]}))

if __name__=='__main__':main()
