"""Catalog permissions/lifecycle, edit atomicity and snapshot preservation."""
import pytest
from sqlalchemy import select
from app.models.catalog import Product, Variant, Collection, AvailabilityStatus
from app.models.orders import Order, OrderLine
from app.services.orders import place_order, CreateOrderDTO, OrderItemDTO


def create_draft(client, **fields):
    response = client.post('/api/v1/admin/products', json=fields)
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_requires_owner_and_csrf(client, admin_headers):
    assert client.get('/api/v1/admin/products').status_code == 401
    assert client.post('/api/v1/admin/products', json={}).status_code == 401
    headers = {k: v for k, v in admin_headers.items() if k != 'X-CSRF-Token'}
    assert client.post('/api/v1/admin/products', headers=headers, json={}).status_code == 403
    assert client.post('/api/v1/admin/collections', headers=admin_headers | {'Origin': 'https://evil.invalid'}, json={'name': 'SAMPLE', 'slug': 'sample'}).status_code == 403


def test_incomplete_drafts_versions_and_publication_requirements(admin_client):
    public_count = admin_client.get('/api/v1/products').json()['total']
    product = create_draft(admin_client)
    assert product['status'] == 'draft' and product['title'] is None and product['variants'] == []
    assert admin_client.get('/api/v1/products').json()['total'] == public_count
    response = admin_client.post(f"/api/v1/admin/products/{product['id']}/publish", json={'expected_version': 1})
    assert response.status_code == 422
    assert {item['field'] for item in response.json()['detail']['fields']} == {'title', 'slug', 'collection_id', 'description', 'primary_media_id', 'variants'}
    path = f"/api/v1/admin/products/{product['id']}"
    updated = admin_client.post(path, json={'expected_version': 1, 'title': ' SAMPLE Tee ', 'slug': 'SAMPLE-TEE',
        'variants': [{'sku': ' SAMPLE-M ', 'size': ' M ', 'price_minor': 123450, 'is_active': True}]}).json()
    assert updated['edit_version'] == 2 and updated['slug'] == 'sample-tee'
    assert updated['variants'][0]['price_minor'] == 123450
    assert admin_client.post(path, json={'expected_version': 1, 'title': 'Overwritten'}).status_code == 409
    assert admin_client.get(path).json()['title'] == 'SAMPLE Tee'


def test_missing_price_is_null_and_cannot_activate(admin_client):
    p = create_draft(admin_client, variants=[{'sku': 'SAMPLE-NOPRICE'}])
    assert p['variants'][0]['price_minor'] is None and not p['variants'][0]['is_active']
    mapped_variants = admin_client.get('/api/v1/admin/catalog/variants')
    assert mapped_variants.status_code == 200
    assert next(v for v in mapped_variants.json() if v['id'] == p['variants'][0]['id'])['product_title'] == 'Untitled draft'
    path = f"/api/v1/admin/products/{p['id']}"
    result = admin_client.post(path, json={'expected_version': 1, 'variants': [{'id': p['variants'][0]['id'], 'is_active': True}]})
    assert result.status_code == 422
    assert admin_client.get(path).json()['edit_version'] == 1
    for amount in (0.01, True, -1, 2147483648):
        assert admin_client.post(path, json={'expected_version': 1, 'variants': [{'id': p['variants'][0]['id'], 'price_minor': amount}]}).status_code == 422


def test_duplicate_values_rollback_entire_edit_and_omitted_variants_survive(admin_client):
    p = create_draft(admin_client, slug='sample-dup', variants=[{'sku': 'SAMPLE-DUP', 'size': 'M'}, {'sku': 'SAMPLE-DUP-L', 'size': 'L'}])
    assert admin_client.post('/api/v1/admin/products', json={'slug': 'sample-dup'}).status_code == 409
    assert admin_client.post('/api/v1/admin/products', json={'variants': [{'sku': 'SAMPLE-DUP'}]}).status_code == 409
    path = f"/api/v1/admin/products/{p['id']}"
    response = admin_client.post(path, json={'expected_version': 1, 'title': 'MUST ROLLBACK',
        'variants': [{'id': p['variants'][1]['id'], 'size': ' M '}]})
    assert response.status_code == 409
    unchanged = admin_client.get(path).json()
    assert unchanged['title'] is None and unchanged['edit_version'] == 1
    response = admin_client.post(path, json={'expected_version': 1, 'variants': [{'id': p['variants'][0]['id'], 'price_minor': 9900}]}).json()
    assert len(response['variants']) == 2
    assert admin_client.post(path, json={'expected_version': 2, 'variants': [{'id': 999999, 'sku': 'SAMPLE-FOREIGN'}]}).status_code == 422


def test_managed_media_guard_cannot_be_bypassed(admin_client):
    collection = admin_client.post('/api/v1/admin/collections', json={'name': 'SAMPLE', 'slug': 'sample-media'}).json()
    p = create_draft(admin_client, title='SAMPLE Complete', slug='sample-complete', collection_id=collection['id'],
        description='Sample description', variants=[{'sku': 'SAMPLE-COMPLETE', 'price_minor': 10000, 'is_active': True}])
    fields = admin_client.post(f"/api/v1/admin/products/{p['id']}/publish", json={'expected_version': 1}).json()['detail']['fields']
    assert [item['field'] for item in fields] == ['primary_media_id']
    assert admin_client.post(f"/api/v1/admin/products/{p['id']}", json={'expected_version': 1, 'legacy_media': True, 'image_url': '/unsafe.png'}).status_code == 422


def test_collection_validation_reordering_and_activation(admin_client):
    rows = [admin_client.post('/api/v1/admin/collections', json={'name': 'SAMPLE ' + slug, 'slug': slug}).json() for slug in ('sample-one', 'sample-two')]
    assert admin_client.post('/api/v1/admin/collections', json={'name': ' ', 'slug': 'invalid'}).status_code == 422
    assert admin_client.post('/api/v1/admin/collections', json={'name': 'SAMPLE', 'slug': 'sample-one'}).status_code == 409
    existing = admin_client.get('/api/v1/admin/collections').json()['collections']
    owned_ids = {row['id'] for row in rows}
    ordered = rows[::-1] + [row for row in existing if row['id'] not in owned_ids]
    result = admin_client.post('/api/v1/admin/collections/reorder', json={'items': [{'id': row['id'], 'expected_version': row['edit_version']} for row in ordered]})
    assert result.status_code == 200
    assert result.json()['collections'][0]['id'] == rows[1]['id']
    assert admin_client.post('/api/v1/admin/collections/reorder', json={'items': [{'id': row['id'], 'expected_version': 1} for row in rows]}).status_code == 409
    c = rows[0]
    public_count = admin_client.get('/api/v1/collections').json()['total']
    response = admin_client.post(f"/api/v1/admin/collections/{c['id']}", json={'expected_version': 2, 'is_active': False})
    assert response.status_code == 200
    assert admin_client.get('/api/v1/collections').json()['total'] == public_count - 1


def test_published_edit_archive_and_order_snapshots(admin_client, client, db_session):
    col = Collection(id='sample-history-col', name='SAMPLE', slug='sample-history-col')
    db_session.add(col); db_session.flush()
    p = Product(id='sample-history', title='SAMPLE Original', slug='sample-history', collection_id=col.id,
                description='SAMPLE description', image_url='/sample-image.png', is_active=True)
    db_session.add(p); db_session.flush()
    v = Variant(product_id=p.id, sku='SAMPLE-HISTORY', price_minor=12345, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(v); db_session.flush()
    order = Order(order_number='SAMPLE-M2-HISTORY', customer_name='SAMPLE', customer_phone='03001234567',
                  shipping_address_line1='SAMPLE street', shipping_city='Lahore', shipping_province='Punjab',
                  payment_method='cod', payment_status='pending', order_status='placed', subtotal_minor=12345, total_minor=12345)
    db_session.add(order); db_session.flush()
    line = OrderLine(order_id=order.id, variant_id=v.id, quantity=1, product_title_snapshot=p.title,
                     variant_sku_snapshot=v.sku, unit_price_minor=12345, line_total_minor=12345)
    db_session.add(line); db_session.flush()
    path = f'/api/v1/admin/products/{p.id}'
    assert admin_client.post(path, json={'expected_version': 1, 'title': 'SAMPLE Edited', 'variants': [{'id': v.id, 'price_minor': 54321}]}).status_code == 200
    assert admin_client.post(path, json={'expected_version': 2, 'title': None}).status_code == 422
    assert admin_client.post(path + '/archive', json={'expected_version': 2}).status_code == 200
    assert client.get('/api/v1/products/sample-history').status_code == 404
    with pytest.raises(ValueError, match='no longer available'):
        place_order(db_session, CreateOrderDTO(customer_name='SAMPLE', customer_phone='03001234567',
            shipping_address_line1='SAMPLE', shipping_city='Lahore', shipping_province='Punjab',
            payment_method='cod', items=[OrderItemDTO(v.id, 1)]))
    assert admin_client.post(path, json={'expected_version': 3, 'title': 'No'}).status_code == 409
    db_session.refresh(line)
    assert line.product_title_snapshot == 'SAMPLE Original' and line.unit_price_minor == 12345
    assert db_session.get(Variant, v.id) is not None
    assert admin_client.post(path + '/restore', json={'expected_version': 3}).json()['status'] == 'draft'
    assert admin_client.post(path + '/publish', json={'expected_version': 4}).status_code == 200
    assert admin_client.post(path + '/unpublish', json={'expected_version': 5}).status_code == 200
    assert client.get('/api/v1/products/sample-history').status_code == 404
    response = client.post('/api/v1/orders', headers={'Idempotency-Key': 'sample_m2_hidden_order_001'}, json={
        'customer_name': 'SAMPLE', 'customer_phone': '03001234567', 'shipping_address_line1': 'SAMPLE Street',
        'shipping_city': 'Lahore', 'shipping_province': 'Punjab', 'payment_method': 'cod', 'items': [{'variant_id': v.id, 'quantity': 1}]})
    assert response.status_code != 201


def test_owner_search_filters_and_no_private_public_fields(admin_client, client):
    p = create_draft(admin_client, title='SAMPLE Search', variants=[{'sku': 'SAMPLE-SEARCH-ABC'}])
    result = admin_client.get('/api/v1/admin/products', params={'search': 'SEARCH-ABC', 'status': 'draft', 'page_size': 1}).json()
    assert result['total'] == 1 and result['products'][0]['id'] == p['id']
    assert admin_client.get('/api/v1/admin/products', params={'search': '%'}).json()['total'] == 0
    assert p['id'] not in {row['id'] for row in client.get('/api/v1/products', params={'page_size': 100}).json()['products']}


def test_delete_product_draft_and_published_guard(admin_client, db_session):
    # 1. Empty draft can be deleted normally
    empty_draft = create_draft(admin_client)
    res = admin_client.delete(f"/api/v1/admin/products/{empty_draft['id']}")
    assert res.status_code == 200, res.text
    assert res.json() == {'deleted': True, 'id': empty_draft['id']}
    assert admin_client.get(f"/api/v1/admin/products/{empty_draft['id']}").status_code == 404

    # 2. Deleting nonexistent product returns 404
    assert admin_client.delete("/api/v1/admin/products/non-existent-id").status_code == 404

    # 3. Draft with variants (no orders) can be deleted
    draft_with_vars = create_draft(admin_client, title='SAMPLE Draft With Vars', variants=[{'sku': 'SAMPLE-DEL-1', 'size': 'M', 'price_minor': 10000}])
    res = admin_client.delete(f"/api/v1/admin/products/{draft_with_vars['id']}")
    assert res.status_code == 200
    assert admin_client.get(f"/api/v1/admin/products/{draft_with_vars['id']}").status_code == 404

    # 4. Published product cannot be deleted; must be unpublished first
    col = Collection(id='del-test-col', name='Delete Test Col', slug='del-test-col')
    db_session.add(col)
    pub = Product(id='pub-del-test', title='Published Tee', slug='pub-del-test', collection_id=col.id,
                  description='Sample description', image_url='/sample-img.png', status='published', is_active=True, edit_version=1)
    db_session.add(pub)
    db_session.commit()

    # Attempt delete on published product
    fail_del = admin_client.delete(f"/api/v1/admin/products/{pub.id}")
    assert fail_del.status_code == 422
    assert fail_del.json()['detail']['code'] == 'published_cannot_delete'
    assert 'Make it unpublished first then delete' in fail_del.json()['detail']['message']

    # Unpublish it first
    unpub_res = admin_client.post(f"/api/v1/admin/products/{pub.id}/unpublish", json={'expected_version': 1})
    assert unpub_res.status_code == 200
    assert unpub_res.json()['status'] == 'draft'

    # Now deletion succeeds
    succ_del = admin_client.delete(f"/api/v1/admin/products/{pub.id}")
    assert succ_del.status_code == 200
    assert admin_client.get(f"/api/v1/admin/products/{pub.id}").status_code == 404


def test_simultaneous_catalog_edits_allow_one_version(test_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from app.schemas.owner_catalog import ProductUpdate
    from app.services.owner_catalog import edit_product, CatalogError
    import uuid
    identifier = 'sample-race-' + uuid.uuid4().hex
    with Session(test_engine) as db:
        db.add(Product(id=identifier, status='draft', is_active=False, legacy_media=False))
        db.commit()
    barrier = Barrier(2)
    def edit(number):
        with Session(test_engine) as db:
            barrier.wait(timeout=10)
            try:
                product = edit_product(db, identifier, ProductUpdate(expected_version=1, title=f'SAMPLE edit {number}'))
                db.commit()
                return 'saved'
            except CatalogError as error:
                db.rollback()
                assert error.detail['code'] == 'edit_conflict'
                return 'conflict'
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(edit, [1, 2])) == ['conflict', 'saved']
        with Session(test_engine) as db:
            assert db.get(Product, identifier).edit_version == 2
    finally:
        with Session(test_engine) as db:
            db.delete(db.get(Product, identifier)); db.commit()


def test_product_multiple_collections_assignment_and_queries(admin_client):
    col1 = admin_client.post('/api/v1/admin/collections', json={'name': 'Multi Col 1', 'slug': 'multi-col-1'}).json()
    col2 = admin_client.post('/api/v1/admin/collections', json={'name': 'Multi Col 2', 'slug': 'multi-col-2'}).json()

    # Create draft with multiple collection assignments
    prod = create_draft(
        admin_client,
        title='Multi Collection Piece',
        slug='multi-collection-piece',
        collection_ids=[col1['id'], col2['id']],
        variants=[{'sku': 'MULTI-1', 'size': 'M', 'color': 'Black', 'price_minor': 250000, 'is_active': True}]
    )
    assert prod['collection_id'] == col1['id']
    assert set(prod['collection_ids']) == {col1['id'], col2['id']}

    # Both collections list this product in owner query
    list1 = admin_client.get(f"/api/v1/admin/products?collection_id={col1['id']}").json()
    assert any(p['id'] == prod['id'] for p in list1['products'])

    list2 = admin_client.get(f"/api/v1/admin/products?collection_id={col2['id']}").json()
    assert any(p['id'] == prod['id'] for p in list2['products'])

    # Update collection assignments to only col2
    updated = admin_client.post(
        f"/api/v1/admin/products/{prod['id']}",
        json={'expected_version': prod['edit_version'], 'collection_ids': [col2['id']]}
    ).json()
    assert updated['collection_id'] == col2['id']
    assert updated['collection_ids'] == [col2['id']]

    # col1 no longer lists it, col2 still lists it
    list1_after = admin_client.get(f"/api/v1/admin/products?collection_id={col1['id']}").json()
    assert not any(p['id'] == prod['id'] for p in list1_after['products'])
    list2_after = admin_client.get(f"/api/v1/admin/products?collection_id={col2['id']}").json()
    assert any(p['id'] == prod['id'] for p in list2_after['products'])

