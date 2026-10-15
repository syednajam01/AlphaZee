"""Real image decoding, file compensation, references, ranges and upload limits."""
import io
import os
import time
import uuid
import pytest
from PIL import Image
from sqlalchemy import select, text
from app.config import settings
from app.models.media import MediaAsset
from app.services import media, media_storage


@pytest.fixture(autouse=True)
def isolated_media(monkeypatch, tmp_path):
    root = tmp_path / 'catalog-media-test'
    assert root.resolve() != settings.catalog_media_root.resolve()
    monkeypatch.setattr(settings, 'catalog_media_root', root)
    return root


@pytest.fixture(autouse=True)
def committed_test_owner(db_session, admin_headers):
    # Real provisioning commits first. Keep fixture credentials across deliberately
    # rolled-back invalid uploads, while the outer test transaction still rolls back.
    db_session.commit()


def image_bytes(fmt='PNG'):
    data = io.BytesIO()
    Image.new('RGB', (32, 24), '#123456').save(data, format=fmt)
    return data.getvalue()


def upload(client, fmt='PNG'):
    ext, mime = {'PNG': ('png', 'image/png'), 'JPEG': ('jpg', 'image/jpeg'), 'WEBP': ('webp', 'image/webp')}[fmt]
    response = client.post('/api/v1/admin/media', files={'file': ('SAMPLE.' + ext, image_bytes(fmt), mime)})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize('fmt', ['PNG', 'JPEG', 'WEBP'])
def test_decoded_images_public_ranges_private_metadata(admin_client, client, fmt):
    asset = upload(admin_client, fmt)
    assert asset['width'] == 32 and asset['height'] == 24 and asset['state'] == 'ready'
    response = client.get(asset['url'])
    assert response.status_code == 200 and response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['content-type'] == asset['content_type']
    assert 'immutable' in response.headers['cache-control']
    assert client.head(asset['url']).content == b''
    ranged = client.get(asset['url'], headers={'Range': 'bytes=0-9'})
    assert ranged.status_code == 206 and ranged.content == response.content[:10]
    assert client.get(asset['url'], headers={'Range': 'bytes=999999-'}).status_code == 416
    assert 'creator_id' not in asset and 'storage_key' not in asset
    assert admin_client.get('/api/v1/admin/media').json()['total'] == 1
    assert client.get('/api/v1/admin/media').status_code == 401
    assert client.get('/api/v1/media/' + uuid.uuid4().hex + '/content').status_code == 404


def test_auth_csrf_origin_and_invalid_payloads(client, admin_client, admin_headers, isolated_media):
    file = {'file': ('SAMPLE.png', image_bytes(), 'image/png')}
    assert client.post('/api/v1/admin/media', files=file).status_code == 401
    headers = {k: v for k, v in admin_headers.items() if k != 'X-CSRF-Token'}
    assert client.post('/api/v1/admin/media', files=file, headers=headers).status_code == 403
    assert client.post('/api/v1/admin/media', files=file, headers=admin_headers | {'Origin': 'https://evil.invalid'}).status_code == 403
    cases = [('script.svg', b'<svg/>', 'image/svg+xml'), ('SAMPLE.png', b'<html>script</html>', 'image/png'),
             ('SAMPLE.jpg', image_bytes(), 'image/jpeg'), ('SAMPLE.png', image_bytes(), 'text/html'),
             ('../SAMPLE.png', image_bytes(), 'image/png'), ('SAMPLE.png', b'', 'image/png')]
    for name, data, mime in cases:
        result = admin_client.post('/api/v1/admin/media', files={'file': (name, data, mime)})
        assert result.status_code == 422, result.text
    assert admin_client.post('/api/v1/admin/media', files=[('file', ('1.png', image_bytes(), 'image/png')), ('file', ('2.png', image_bytes(), 'image/png'))]).status_code == 400
    assert not list((isolated_media / 'objects').iterdir())
    assert not list((isolated_media / 'staging').iterdir())


def test_image_limit_pixel_limit_and_normalization(admin_client, monkeypatch):
    assert admin_client.post('/api/v1/admin/media', files={'file': ('SAMPLE.png', b'x' * (media_storage.IMAGE_LIMIT + 1), 'image/png')}).status_code == 413
    monkeypatch.setattr(media_storage, 'PIXEL_LIMIT', 100)
    assert admin_client.post('/api/v1/admin/media', files={'file': ('SAMPLE.png', image_bytes(), 'image/png')}).status_code == 422
    monkeypatch.setattr(media_storage, 'PIXEL_LIMIT', 40_000_000)
    raw = image_bytes() + b'<script>appended data must be stripped</script>'
    response = admin_client.post('/api/v1/admin/media', files={'file': ('SAMPLE.png', raw, 'image/png')})
    assert response.status_code == 201
    assert b'<script>' not in admin_client.get(response.json()['url']).content


def test_staged_file_compensation_on_database_error(admin_client, db_session, monkeypatch, isolated_media):
    original = db_session.flush
    def fail(*args, **kwargs):
        if any(isinstance(x, MediaAsset) for x in db_session.new): raise RuntimeError('SAMPLE database failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(db_session, 'flush', fail)
    with pytest.raises(RuntimeError, match='SAMPLE database failure'): upload(admin_client)
    assert not list((isolated_media / 'objects').iterdir())
    assert not list((isolated_media / 'staging').iterdir())


def test_product_attachment_publication_and_shared_deletion(admin_client):
    asset, replacement = upload(admin_client), upload(admin_client)
    c = admin_client.post('/api/v1/admin/collections', json={'name': 'SAMPLE', 'slug': 'sample-media'}).json()
    p = admin_client.post('/api/v1/admin/products', json={'title': 'SAMPLE', 'slug': 'sample-media', 'collection_id': c['id'],
        'description': 'Sample description', 'variants': [{'sku': 'SAMPLE-MEDIA', 'price_minor': 12345, 'is_active': True}]}).json()
    path = f"/api/v1/admin/media/products/{p['id']}"
    def attach(version, items): return admin_client.post(path, json={'expected_version': version, 'items': items})
    result = attach(1, [{'asset_id': asset['id'], 'role': 'primary', 'alt_text': 'Sample product'}])
    assert result.status_code == 200, result.text
    assert result.json()['image_url'] == asset['url'] and result.json()['publication_requirements'] == []
    assert attach(1, []).status_code == 409
    published = admin_client.post(f"/api/v1/admin/products/{p['id']}/publish", json={'expected_version': 2})
    assert published.status_code == 200, published.text
    assert attach(3, []).status_code == 422
    assert admin_client.post(f"/api/v1/admin/media/{asset['id']}/delete", json={'expected_version': 1}).status_code == 409
    assert admin_client.post(f"/api/v1/admin/media/collections/{c['id']}", json={'expected_version': 1, 'asset_id': asset['id']}).status_code == 200
    assert attach(3, [{'asset_id': replacement['id'], 'role': 'primary'}]).status_code == 200
    assert admin_client.post(f"/api/v1/admin/media/{asset['id']}/delete", json={'expected_version': 1}).status_code == 409
    assert admin_client.post(f"/api/v1/admin/media/collections/{c['id']}", json={'expected_version': 2, 'asset_id': None}).status_code == 200
    assert admin_client.post(f"/api/v1/admin/media/{asset['id']}/delete", json={'expected_version': 1}).status_code == 200
    assert admin_client.get(asset['url']).status_code == 404
    assert attach(4, [{'asset_id': asset['id'], 'role': 'primary'}]).status_code == 422
    assert admin_client.get(replacement['url']).status_code == 200


def test_roles_variant_validation_and_detach_retains_bytes(admin_client):
    asset = upload(admin_client)
    p = admin_client.post('/api/v1/admin/products', json={'variants': [{'sku': 'SAMPLE-GALLERY'}]}).json()
    path = f"/api/v1/admin/media/products/{p['id']}"
    for items in ([{'asset_id': asset['id'], 'role': 'primary', 'variant_id': p['variants'][0]['id']}],
                  [{'asset_id': asset['id'], 'role': 'gallery', 'variant_id': 999999}],
                  [{'asset_id': asset['id'], 'role': 'primary'}] * 2,
                  [{'asset_id': asset['id'], 'role': 'hero_video'}]):
        assert admin_client.post(path, json={'expected_version': 1, 'items': items}).status_code == 422
    items = [{'asset_id': asset['id'], 'variant_id': p['variants'][0]['id'], 'display_order': 2, 'alt_text': 'SAMPLE variant'}]
    assert admin_client.post(path, json={'expected_version': 1, 'items': items}).status_code == 200
    assert admin_client.post(path, json={'expected_version': 2, 'items': []}).status_code == 200
    assert admin_client.get(asset['url']).status_code == 200


def test_atomic_details_media_and_collection_image_saves(admin_client):
    asset = upload(admin_client)
    c = admin_client.post('/api/v1/admin/collections', json={'name': 'SAMPLE atomic', 'slug': 'sample-atomic', 'image_media_id': asset['id']}).json()
    assert c['image_url'] == asset['url']
    p = admin_client.post('/api/v1/admin/products', json={'title': 'SAMPLE before', 'description': 'SAMPLE before'}).json()
    path = '/api/v1/admin/products/' + p['id']
    invalid = admin_client.post(path, json={'expected_version': 1, 'title': 'MUST ROLLBACK', 'description': 'MUST ROLLBACK',
        'variants': [{'sku': 'SAMPLE-ATOMIC', 'price_minor': 12345, 'is_active': True}], 'media': [{'asset_id': 'f'*32, 'role': 'primary'}]})
    assert invalid.status_code == 422
    unchanged = admin_client.get(path).json()
    assert unchanged['title'] == 'SAMPLE before' and unchanged['description'] == 'SAMPLE before' and unchanged['edit_version'] == 1 and unchanged['variants'] == []
    valid = admin_client.post(path, json={'expected_version': 1, 'title': 'SAMPLE after', 'description': 'SAMPLE after',
        'variants': [{'sku': 'SAMPLE-ATOMIC', 'price_minor': 12345, 'is_active': True}], 'media': [{'asset_id': asset['id'], 'role': 'primary'}]})
    assert valid.status_code == 200, valid.text
    saved = valid.json()
    assert saved['description'] == 'SAMPLE after' and saved['edit_version'] == 2 and saved['image_url'] == asset['url']
    invalid = admin_client.post('/api/v1/admin/collections/' + c['id'], json={'expected_version': 1, 'name': 'MUST ROLLBACK', 'image_media_id': 'f'*32})
    assert invalid.status_code == 422
    rows = admin_client.get('/api/v1/admin/collections').json()['collections']
    assert next(row for row in rows if row['id'] == c['id'])['name'] == 'SAMPLE atomic'


def test_cleanup_ignores_ready_unknown_recent_and_active_files(admin_client, db_session, isolated_media):
    asset = upload(admin_client)
    staging, objects = media_storage.paths()
    ready = next(objects.iterdir())
    orphan = objects / (uuid.uuid4().hex + '.png')
    orphan.write_bytes(b'orphan')
    stage = staging / (uuid.uuid4().hex + '.upload'); stage.write_bytes(b'orphan')
    recent = objects / (uuid.uuid4().hex + '.png'); recent.write_bytes(b'recent')
    unknown = objects / 'keep.txt'; unknown.write_text('keep')
    for path in (ready, orphan, stage, unknown): os.utime(path, (time.time()-90000,) * 2)
    result = media.cleanup(db_session)
    assert set(result['files']) == {f'objects/{orphan.name}', f'staging/{stage.name}'} or set(result['files']) == {f'objects\\{orphan.name}', f'staging\\{stage.name}'}
    assert orphan.exists() and stage.exists()
    media.cleanup(db_session, dry_run=False)
    assert ready.exists() and unknown.exists() and recent.exists() and not orphan.exists() and not stage.exists()
    with pytest.raises(ValueError): media.cleanup(db_session, minimum_age_hours=0)


def test_body_limit_includes_chunked_requests(admin_client, monkeypatch):
    monkeypatch.setattr(media_storage, 'BODY_LIMIT', 64)
    assert admin_client.post('/api/v1/admin/media', content=b'x'*65, headers={'Content-Type': 'multipart/form-data; boundary=sample'}).status_code == 413
    boundary = b'--sample\r\nContent-Disposition: form-data; name="file"; filename="SAMPLE.png"\r\nContent-Type: image/png\r\n\r\n'
    chunks = iter([boundary, image_bytes(), b'\r\n--sample--\r\n'])
    assert admin_client.post('/api/v1/admin/media', content=chunks, headers={'Content-Type': 'multipart/form-data; boundary=sample'}).status_code == 413


def test_active_staging_cleanup_lock(admin_client, db_session, test_engine):
    from sqlalchemy.orm import Session
    staging, _ = media_storage.paths()
    identifier = uuid.uuid4().hex
    active = staging / (identifier + '.upload'); active.write_bytes(b'active upload')
    os.utime(active, (time.time()-90000,) * 2)
    with Session(test_engine) as uploading:
        uploading.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': media.staging_lock_key(identifier)})
        assert media.cleanup(db_session, dry_run=False)['files'] == []
        assert active.exists()
        uploading.rollback()
    assert len(media.cleanup(db_session, dry_run=False)['files']) == 1 and not active.exists()


def test_attach_versus_delete_is_serialized(test_engine, sample_password_hash):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import delete
    from sqlalchemy.orm import Session
    from app.models.catalog import Product
    from app.models.media import ProductMedia
    from app.models.suppliers import UserAccount
    from app.schemas.media import ProductMediaCommand, StrictCommand
    from app.services.owner_catalog import CatalogError
    asset_id = uuid.uuid4().hex
    product_id = 'SAMPLE-media-race-' + asset_id
    file = media_storage.object_path(asset_id + '.png'); file.write_bytes(image_bytes())
    with Session(test_engine) as db:
        creator = UserAccount(auth_subject='SAMPLE-media-race-' + asset_id, is_active=True)
        db.add(creator); db.flush(); creator_id = creator.id
        db.add(MediaAsset(id=asset_id, storage_key=file.name, original_name='SAMPLE.png', kind='image', content_type='image/png',
                          byte_size=file.stat().st_size, checksum='a'*64, width=32, height=24, creator_id=creator_id))
        db.add(Product(id=product_id, status='draft', is_active=False, legacy_media=False))
        db.commit()
    barrier = Barrier(2)
    def race(action):
        with Session(test_engine) as db:
            barrier.wait(timeout=10)
            try:
                if action == 'attach':
                    media.replace_product_media(db, product_id, ProductMediaCommand(expected_version=1, items=[{'asset_id': asset_id, 'role': 'primary'}]))
                    db.commit()
                else: media.delete_asset(db, asset_id, StrictCommand(expected_version=1))
                return action + '_saved'
            except CatalogError as error:
                db.rollback()
                assert error.detail['code'] in {'media_not_ready', 'media_in_use'}
                return action + '_rejected'
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            result = list(workers.map(race, ['attach', 'delete']))
        assert result in [['attach_saved', 'delete_rejected'], ['attach_rejected', 'delete_saved']]
        with Session(test_engine) as db:
            asset = db.get(MediaAsset, asset_id)
            attached = db.scalar(select(ProductMedia.id).where(ProductMedia.asset_id == asset_id))
            assert (asset.state == 'ready' and attached and file.exists()) or (asset.state == 'deleted' and not attached and not file.exists())
    finally:
        with Session(test_engine) as db:
            db.execute(delete(ProductMedia).where(ProductMedia.product_id == product_id))
            db.execute(delete(Product).where(Product.id == product_id))
            db.execute(delete(MediaAsset).where(MediaAsset.id == asset_id))
            db.execute(delete(UserAccount).where(UserAccount.id == creator_id))
            db.commit()
        file.unlink(missing_ok=True)


def test_video_process_timeout_and_missing_binary_are_actionable(monkeypatch):
    import subprocess
    from app.services.owner_catalog import CatalogError
    def timeout(*args, **kwargs): raise subprocess.TimeoutExpired('ffprobe', 1)
    monkeypatch.setattr(subprocess, 'run', timeout)
    with pytest.raises(CatalogError) as result: media_storage._probe(['ffprobe'], 1)
    assert result.value.status == 422
    def missing(*args, **kwargs): raise FileNotFoundError()
    monkeypatch.setattr(subprocess, 'run', missing)
    with pytest.raises(CatalogError) as result: media_storage._probe(['ffprobe'], 1)
    assert result.value.status == 503


def test_local_password_override_keeps_default_policy_and_rejects_production(monkeypatch):
    from app.services.passwords import hash_password, verify_password
    with pytest.raises(ValueError): hash_password('sample7')
    hashed = hash_password('sample7', allow_short_local=True)
    assert verify_password('sample7', hashed)
    monkeypatch.setattr(settings, 'app_env', 'production')
    with pytest.raises(ValueError): hash_password('sample7', allow_short_local=True)


def test_production_rejects_local_only_credentials_and_reset_restores_policy(db_session, client, monkeypatch):
    from app.services.owners import provision_owner
    from app.dependencies.auth import cookie_name
    from app.services.session_store import issue_session
    from app.models.suppliers import UserAccount
    owner = provision_owner(db_session, 'sample_local', 'sample7', allow_short_local=True)
    token, _ = issue_session(db_session, owner)
    assert client.post('/api/v1/auth/login', json={'username': 'sample_local', 'password': 'sample7'}, headers={'Origin': 'http://localhost:3000'}).status_code == 200
    monkeypatch.setattr(settings, 'app_env', 'production')
    assert client.get('/api/v1/auth/session', headers={'Cookie': f'{cookie_name()}={token}'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'username': 'sample_local', 'password': 'sample7'}, headers={'Origin': 'http://localhost:3000'}).status_code == 401
    monkeypatch.setattr(settings, 'app_env', 'development')
    provision_owner(db_session, 'sample_local', 'SAMPLE-strong-password', reset_password=True)
    assert db_session.get(UserAccount, owner.user_id).auth_subject == 'local-owner:sample_local'
    assert client.post('/api/v1/auth/login', json={'username': 'sample_local', 'password': 'SAMPLE-strong-password'}, headers={'Origin': 'http://localhost:3000'}).status_code == 200
