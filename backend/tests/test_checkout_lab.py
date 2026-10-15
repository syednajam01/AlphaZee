"""Lab guard, cookie separation and transactional catalog-only transfer regressions."""
import hashlib
import io
import json
import zipfile
import pytest
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import select,func
from app.config import Settings,settings
from app.models.catalog import Product
from app.models.inventory import StockEvent,StockReservation,InventoryBalance
from app.models.media import MediaAsset
from app.services.catalog_transfer import Bundle,canonical,import_bundle,read_bundle,database_identity


def lab(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'app_env','test')
    monkeypatch.setattr(settings,'database_url','postgresql://lab:unused@127.0.0.1:5432/alphazee_checkout_test')
    monkeypatch.setattr(settings,'test_checkout_enabled',True)
    monkeypatch.setattr(settings,'checkout_lab',True)
    monkeypatch.setattr(settings,'catalog_media_root',tmp_path/'media')


def bundle_file(tmp_path, corrupt=False, extra=None):
    data=io.BytesIO();Image.new('RGB',(20,20),'blue').save(data,format='PNG');content=data.getvalue()
    manifest=Bundle.model_validate({'source_identity':'a'*64,'collections':[{'source_id':'col-source','fields':{'name':'SAMPLE','slug':'sample-source'}}],
        'products':[{'source_id':'source','fields':{'title':'SAMPLE test','slug':'sample-product','description':'SAMPLE only','collection_id':'col-source'},
                     'variants':[{'source_id':15,'fields':{'sku':'SAMPLE-transfer','size':'M','price_minor':12345,'is_active':True,'availability':'available'},'cost_minor':5000}],
                     'media':[{'asset_id':'b'*32,'role':'primary'}]}],
        'assets':[{'id':'b'*32,'filename':'SAMPLE.png','content_type':'image/png','checksum':hashlib.sha256(content).hexdigest(),'byte_size':len(content)}]})
    path=tmp_path/'catalog.zip'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('manifest.json',canonical(manifest));archive.writestr('assets/'+'b'*32,b'bad' if corrupt else content)
        if extra: archive.writestr(extra,b'bad')
    return path


def test_lab_requires_existing_gate_and_only_lab_allows_simulated_bank():
    with pytest.raises(ValidationError): Settings(_env_file=None,checkout_lab=True,test_checkout_enabled=False)
    config=Settings(_env_file=None,app_env='test',test_checkout_enabled=True,checkout_lab=True,
        database_url='postgresql://u:p@127.0.0.1:5432/lab_test',bank_account_number='NO-REAL-ACCOUNT',bank_iban='NO-REAL-IBAN')
    assert config.bank_transfer_enabled and config.checkout_enabled
    assert not Settings(_env_file=None,bank_account_number='NO-REAL-ACCOUNT',bank_iban='NO-REAL-IBAN').bank_transfer_enabled


def test_lab_cookie_names_separate_all_three_sessions(monkeypatch):
    from app.dependencies.auth import cookie_name as owner
    from app.services.order_access import cookie_name as order
    from app.services.checkout_attempts import checkout_cookie_name as checkout
    monkeypatch.setattr(settings,'checkout_lab',False)
    normal={owner(),order(),checkout()}
    monkeypatch.setattr(settings,'checkout_lab',True)
    isolated={owner(),order(),checkout()}
    assert len(isolated)==3 and not normal.intersection(isolated)
    assert database_identity('postgresql://u:p@localhost/db')==database_identity('postgresql://x:y@127.0.0.1:5432/db')


@pytest.mark.parametrize('extra', ['../escape','assets/unlisted','customers.json'])
def test_bundle_rejects_unlisted_paths(tmp_path,extra):
    with pytest.raises(ValueError,match='Unexpected bundle paths'): read_bundle(bundle_file(tmp_path,extra=extra))


def test_bundle_rejects_tampered_bytes(tmp_path):
    with pytest.raises(ValueError,match='checksum'): read_bundle(bundle_file(tmp_path,corrupt=True))


def test_transfer_dry_run_apply_rerun_preserves_draft_and_stock(db_session,sample_owner,monkeypatch,tmp_path):
    lab(monkeypatch,tmp_path);path=bundle_file(tmp_path)
    before=db_session.scalar(select(func.count(Product.id)))
    report=import_bundle(db_session,path,sample_owner.username,7,False)
    assert report['dry_run'] and db_session.scalar(select(func.count(Product.id)))==before
    assert not list((tmp_path/'media'/'objects').iterdir())
    report=import_bundle(db_session,path,sample_owner.username,7,True)
    product=db_session.get(Product,report['products'][0]['id'])
    assert product.status=='draft' and not product.is_active and product.variants[0].id!=15
    assert product.variants[0].price_minor==12345
    assert db_session.scalar(select(InventoryBalance.on_hand))==7
    events=db_session.scalar(select(func.count(StockEvent.id)))
    assert events==1 and db_session.scalar(select(func.count(StockReservation.id)))==0
    assert len(list((tmp_path/'media'/'objects').iterdir()))==1
    again=import_bundle(db_session,path,sample_owner.username,99,True)
    assert again['products'][0]['action']=='skip_existing'
    assert db_session.scalar(select(InventoryBalance.on_hand))==7
    assert db_session.scalar(select(func.count(StockEvent.id)))==events


def test_transfer_failure_rolls_back_records_and_own_files(db_session,sample_owner,monkeypatch,tmp_path):
    from app.services import catalog_transfer
    lab(monkeypatch,tmp_path);path=bundle_file(tmp_path)
    db_session.commit()
    def fail(*args,**kwargs):raise ValueError('SAMPLE failure')
    monkeypatch.setattr(catalog_transfer,'replace_product_media',fail)
    with pytest.raises(ValueError,match='SAMPLE failure'):import_bundle(db_session,path,sample_owner.username,5,True)
    assert db_session.scalar(select(func.count(Product.id)))==0
    assert db_session.scalar(select(func.count(MediaAsset.id)))==0
    assert not list((tmp_path/'media'/'objects').iterdir())


def test_transfer_rejects_normal_environment_before_reading_bundle(db_session,monkeypatch):
    monkeypatch.setattr(settings,'checkout_lab',False)
    with pytest.raises(ValueError,match='isolated'):import_bundle(db_session,'missing.zip','unknown',0,True)
