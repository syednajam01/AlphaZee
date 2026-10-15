"""Customer media contract, stable identity and catalog lifecycle visibility."""
import uuid
from app.models.catalog import Variant, AvailabilityStatus
from app.models.media import MediaAsset, ProductMedia
from tests.test_orders_integration import _setup_store_catalog
from tests.test_media import upload, isolated_media


def test_gallery_is_ordered_public_only_and_inactive_variant_media_is_hidden(admin_client, db_session, sample_owner, isolated_media):
    v, sv, balance = _setup_store_catalog(db_session)
    other = Variant(product_id=v.product_id, sku='SAMPLE-M6-INACTIVE', size='S', color='Blue',
        price_minor=500, is_active=False, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(other); db_session.flush()
    image, poster, alternate = upload(admin_client), upload(admin_client), upload(admin_client)
    video = MediaAsset(id=uuid.uuid4().hex, storage_key=uuid.uuid4().hex+'.mp4', original_name='PRIVATE-filename.mp4',
        kind='video', content_type='video/mp4', byte_size=100, checksum='PRIVATE-checksum', width=80, height=60,
        duration_ms=1000, state='ready', poster_id=poster['id'], creator_id=sample_owner.user_id)
    db_session.add(video); db_session.flush()
    for asset, role, order, variant in [(image['id'],'primary',0,None),(video.id,'gallery',2,None),
                                      (alternate['id'],'gallery',1,v.id),(poster['id'],'gallery',3,other.id)]:
        db_session.add(ProductMedia(product_id=v.product_id, asset_id=asset, role=role, display_order=order,
            variant_id=variant, alt_text='SAMPLE customer alt'))
    db_session.flush()
    response = admin_client.get(f'/api/v1/catalog/products/{v.product_id}')
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert [m['id'] for m in data['media']] == [image['id'],alternate['id'],video.id]
    assert data['media'][-1]['poster_url'] == poster['url']
    assert data['media'][1]['variant_id'] == v.id
    assert [row['id'] for row in data['variants']] == [v.id]
    for private in ('PRIVATE-', 'storage_key', 'original_name', 'creator_id', 'checksum', 'supplier_cost_minor', 'held_reservations'):
        assert private not in response.text
    db_session.get(MediaAsset, alternate['id']).state = 'deleted'; db_session.flush()
    assert [m['id'] for m in admin_client.get(f'/api/v1/products/{v.product.slug}').json()['media']] == [image['id'],video.id]


def test_stable_identity_survives_slug_edit_and_obeys_publication_and_collection(admin_client, db_session):
    v, sv, balance = _setup_store_catalog(db_session)
    product = v.product
    second = Variant(product_id=product.id, sku='SAMPLE-M6-SECOND', size='L', color='Green',
        price_minor=15025, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(second); db_session.flush()
    product.variants.sort(key=lambda row:row.id, reverse=True)
    old_slug = product.slug
    path = f'/api/v1/catalog/products/{product.id}'
    product.slug = 'sample-m6-renamed'; product.description = 'SAMPLE updated description'
    product.material = 'SAMPLE cotton'; product.care = 'SAMPLE cold wash'; product.sizing = 'SAMPLE relaxed'
    db_session.flush()
    assert admin_client.get(f'/api/v1/products/{old_slug}').status_code == 404
    data = admin_client.get(path).json()
    assert [row['id'] for row in data['variants']] == [v.id, second.id]
    assert data['slug'] == 'sample-m6-renamed' and data['material'] == 'SAMPLE cotton'
    assert data['description'] == 'SAMPLE updated description'
    listing_path = f'/api/v1/products?collection_id={product.collection_id}'
    assert admin_client.get(listing_path).json()['products'][0]['availability'] == 'available'
    balance.on_hand = 0; db_session.flush()
    listing = admin_client.get(listing_path).json()
    assert listing['total'] == 1 and listing['products'][0]['availability'] == 'unavailable'
    for state in ('draft', 'archived'):
        product.status = state; db_session.flush()
        assert admin_client.get(path).status_code == 404
        assert admin_client.get(listing_path).json()['total'] == 0
    product.status = 'published'; product.collection.is_active = False; db_session.flush()
    assert admin_client.get(path).status_code == 404
    assert admin_client.get(listing_path).json()['total'] == 0


def test_public_media_omits_video_without_ready_poster(admin_client, db_session, sample_owner):
    v, _, _ = _setup_store_catalog(db_session)
    video = MediaAsset(id=uuid.uuid4().hex, storage_key=uuid.uuid4().hex+'.webm', original_name='SAMPLE.webm',
        kind='video', content_type='video/webm', byte_size=100, checksum='sample', width=80, height=60,
        duration_ms=1000, state='ready', creator_id=sample_owner.user_id)
    db_session.add(video); db_session.flush()
    db_session.add(ProductMedia(product_id=v.product_id, asset_id=video.id, role='gallery', display_order=0))
    db_session.flush()
    assert admin_client.get(f'/api/v1/catalog/products/{v.product_id}').json()['media'] == []
