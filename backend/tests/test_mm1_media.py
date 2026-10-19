"""MM1 Media Contract, Hover Role, Incremental Attachments, and Hero Slide Playlist Tests."""
import uuid
import pytest
from app.models.catalog import Variant, AvailabilityStatus, Product, Collection
from app.models.media import MediaAsset, ProductMedia, HeroSlide
from tests.test_orders_integration import _setup_store_catalog
from tests.test_media import upload, isolated_media, image_bytes
from app.services import media_storage


def test_hover_image_role_and_public_urls(admin_client, client, db_session, sample_owner, isolated_media):
    v, _, _ = _setup_store_catalog(db_session)
    product = v.product

    front_img = upload(admin_client)
    hover_img = upload(admin_client)
    gallery_img = upload(admin_client)

    # Attach front (primary), hover, and gallery
    res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/attach', json={
        'expected_version': product.edit_version,
        'asset_id': front_img['id'],
        'role': 'primary',
    })
    assert res.status_code == 200, res.text
    product_data = res.json()
    assert product_data['image_url'] == front_img['url']

    # Attach hover image
    res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/attach', json={
        'expected_version': product_data['edit_version'],
        'asset_id': hover_img['id'],
        'role': 'hover_image',
    })
    assert res.status_code == 200, res.text
    product_data = res.json()
    assert product_data['hover_image_url'] == hover_img['url']
    assert any(m['role'] == 'hover_image' and m['asset']['id'] == hover_img['id'] for m in product_data['media'])

    # Public product listing must include hover_image_url
    public_res = client.get('/api/v1/products')
    assert public_res.status_code == 200
    public_items = public_res.json()['products']
    target = next((p for p in public_items if p['id'] == product.id), None)
    assert target is not None
    assert target['image_url'] == front_img['url']
    assert target['hover_image_url'] == hover_img['url']

    # Public product detail must also include hover_image_url
    detail_res = client.get(f'/api/v1/products/{product.slug}')
    assert detail_res.status_code == 200
    assert detail_res.json()['hover_image_url'] == hover_img['url']

    # Replace hover image via set_product_roles
    hover2 = upload(admin_client)
    roles_res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/roles', json={
        'expected_version': product_data['edit_version'],
        'hover_asset_id': hover2['id'],
    })
    assert roles_res.status_code == 200
    updated_p = roles_res.json()
    assert updated_p['hover_image_url'] == hover2['url']

    # Clear hover image
    clear_res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/roles', json={
        'expected_version': updated_p['edit_version'],
        'hover_asset_id': None,
    })
    assert clear_res.status_code == 200
    assert clear_res.json()['hover_image_url'] is None


def test_incremental_media_detach_and_reorder(admin_client, db_session, isolated_media):
    v, _, _ = _setup_store_catalog(db_session)
    product = v.product

    img1 = upload(admin_client)
    img2 = upload(admin_client)
    img3 = upload(admin_client)

    # Initial bulk setup
    res = admin_client.post(f'/api/v1/admin/media/products/{product.id}', json={
        'expected_version': product.edit_version,
        'items': [
            {'asset_id': img1['id'], 'role': 'primary', 'display_order': 0},
            {'asset_id': img2['id'], 'role': 'gallery', 'display_order': 1},
            {'asset_id': img3['id'], 'role': 'gallery', 'display_order': 2},
        ]
    })
    assert res.status_code == 200
    p = res.json()
    assert len(p['media']) == 3
    link2 = next(m for m in p['media'] if m['asset']['id'] == img2['id'])
    link3 = next(m for m in p['media'] if m['asset']['id'] == img3['id'])

    # Detach img2 by link_id
    detach_res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/detach', json={
        'expected_version': p['edit_version'],
        'link_id': link2['id'],
    })
    assert detach_res.status_code == 200
    p2 = detach_res.json()
    assert len(p2['media']) == 2
    assert not any(m['asset']['id'] == img2['id'] for m in p2['media'])

    # Reorder remaining
    reorder_res = admin_client.post(f'/api/v1/admin/media/products/{product.id}/reorder', json={
        'expected_version': p2['edit_version'],
        'link_ids': [link3['id'], p2['media'][0]['id']],
    })
    assert reorder_res.status_code == 200


def test_more_than_100_media_items_supported(admin_client, db_session, isolated_media, sample_owner):
    v, _, _ = _setup_store_catalog(db_session)
    product = v.product

    primary = upload(admin_client)
    _, objects = media_storage.paths()
    img_data = image_bytes('PNG')

    # Create 105 mock ready image assets directly in DB and disk for high-count attachment
    asset_ids = [primary['id']]
    for i in range(104):
        aid = uuid.uuid4().hex
        key = f'{aid}.png'
        (objects / key).write_bytes(img_data)
        asset = MediaAsset(
            id=aid, storage_key=key, original_name=f'test_{i}.png',
            kind='image', content_type='image/png', byte_size=len(img_data), checksum=f'chk{aid}',
            width=32, height=24, state='ready', creator_id=sample_owner.user_id
        )
        db_session.add(asset)
        asset_ids.append(aid)
    db_session.commit()

    items = [{'asset_id': asset_ids[0], 'role': 'primary', 'display_order': 0}]
    for idx, aid in enumerate(asset_ids[1:], start=1):
        items.append({'asset_id': aid, 'role': 'gallery', 'display_order': idx})

    assert len(items) == 105

    res = admin_client.post(f'/api/v1/admin/media/products/{product.id}', json={
        'expected_version': product.edit_version,
        'items': items,
    })
    assert res.status_code == 200, res.text
    assert len(res.json()['media']) == 105


def test_hero_slide_admin_and_public_lifecycle(admin_client, client, db_session, isolated_media, sample_owner):
    v, _, _ = _setup_store_catalog(db_session)
    product = v.product

    poster = upload(admin_client)
    slide_img = upload(admin_client)

    _, objects = media_storage.paths()
    # Create a ready video asset with physical file
    vid_id = uuid.uuid4().hex
    video_key = f'{vid_id}.mp4'
    (objects / video_key).write_bytes(b'video-content')

    video_asset = MediaAsset(
        id=vid_id, storage_key=video_key, original_name='hero_reel.mp4',
        kind='video', content_type='video/mp4', byte_size=2000, checksum=f'chk{vid_id}',
        width=1920, height=1080, duration_ms=12000, state='ready',
        poster_id=poster['id'], creator_id=sample_owner.user_id
    )
    db_session.add(video_asset)
    db_session.commit()

    # 1. Admin creates slide 1 (video slide)
    create_res1 = admin_client.post('/api/v1/admin/media/hero/slides', json={
        'title': 'Signature Collection Reel',
        'benefit': 'Timeless elegance in luxury fabrics',
        'video_asset_id': video_asset.id,
        'poster_asset_id': poster['id'],
        'display_order': 0,
        'is_enabled': True,
        'target_product_id': product.id,
    })
    assert create_res1.status_code == 201, create_res1.text
    slide1 = create_res1.json()
    assert slide1['title'] == 'Signature Collection Reel'
    assert slide1['video_url'] is not None
    assert slide1['poster_url'] == poster['url']

    # 2. Admin creates slide 2 (image slide)
    create_res2 = admin_client.post('/api/v1/admin/media/hero/slides', json={
        'title': 'Seasonal Lookbook',
        'benefit': 'Modern cuts tailored to perfection',
        'image_asset_id': slide_img['id'],
        'display_order': 1,
        'is_enabled': True,
    })
    assert create_res2.status_code == 201, create_res2.text
    slide2 = create_res2.json()

    # 3. Admin lists slides
    list_res = admin_client.get('/api/v1/admin/media/hero/slides')
    assert list_res.status_code == 200
    slides = list_res.json()['slides']
    assert len(slides) >= 2
    assert any(s['id'] == slide1['id'] for s in slides)
    assert any(s['id'] == slide2['id'] for s in slides)

    # 4. Public endpoint GET /api/v1/hero/slides
    pub_slides_res = client.get('/api/v1/hero/slides')
    assert pub_slides_res.status_code == 200
    pub_slides = pub_slides_res.json()
    assert len(pub_slides) >= 2
    assert pub_slides[0]['id'] == slide1['id']
    assert pub_slides[0]['video_url'] is not None

    # 5. Public endpoint GET /api/v1/products/hero reflects slides
    pub_hero_products = client.get('/api/v1/products/hero')
    assert pub_hero_products.status_code == 200
    hero_prods = pub_hero_products.json()
    assert len(hero_prods) >= 1
    assert any(p.get('slide_id') == slide1['id'] for p in hero_prods)

    # 6. Reorder slides
    reorder_res = admin_client.post('/api/v1/admin/media/hero/slides/reorder', json={
        'expected_version': 1,
        'slide_ids': [slide2['id'], slide1['id']],
    })
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()['slides']
    assert reordered[0]['id'] == slide2['id']
    assert reordered[1]['id'] == slide1['id']
    s2_version = reordered[0]['edit_version']
    s1_version = reordered[1]['edit_version']

    # 7. Update slide 2
    update_res = admin_client.post(f'/api/v1/admin/media/hero/slides/{slide2["id"]}', json={
        'expected_version': s2_version,
        'title': 'Updated Lookbook Title',
        'is_enabled': False,
    })
    assert update_res.status_code == 200
    assert update_res.json()['title'] == 'Updated Lookbook Title'
    assert update_res.json()['is_enabled'] is False

    # Disabled slide must not appear in public /hero/slides
    pub_slides_after = client.get('/api/v1/hero/slides').json()
    assert not any(s['id'] == slide2['id'] for s in pub_slides_after)
    assert any(s['id'] == slide1['id'] for s in pub_slides_after)

    # 8. Delete slide
    del_res = admin_client.post(f'/api/v1/admin/media/hero/slides/{slide1["id"]}/delete', json={
        'expected_version': s1_version,
    })
    assert del_res.status_code == 200
    assert del_res.json()['deleted'] is True
