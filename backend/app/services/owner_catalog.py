"""Transactional owner editing without stock writes or historical snapshot edits."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import Session
from app.models.catalog import Collection, Product, Variant, AvailabilityStatus


class CatalogError(Exception):
    def __init__(self, code, message, status=422, fields=None, current_version=None):
        self.detail = {'code': code, 'message': message, 'fields': fields or []}
        if current_version is not None:
            self.detail['current_version'] = current_version
        self.status = status
        super().__init__(message)


def locked(db, model, identifier, version):
    obj = db.scalar(select(model).where(model.id == identifier).with_for_update().execution_options(populate_existing=True))
    if obj is None:
        raise CatalogError('not_found', 'Catalog record not found', 404)
    if obj.edit_version != version:
        raise CatalogError('edit_conflict', 'This record changed. Reload and review your edits.', 409, current_version=obj.edit_version)
    return obj


def publication_requirements(product):
    fields = []
    def required(field, message, code='required'):
        fields.append({'field': field, 'code': code, 'message': message})
    if not product.title: required('title', 'Enter a product title')
    if not product.slug: required('slug', 'Enter a unique product slug')
    if product.collection and not product.collection.is_active:
        required('collection_id', 'Choose an active collection')
    if not product.description: required('description', 'Enter a customer description')
    primary = next((link.asset for link in product.media_links if link.role == 'primary'), None)
    if primary is not None:
        from app.services.media_storage import object_path
        valid_primary = primary.state == 'ready' and primary.kind == 'image' and object_path(primary.storage_key).is_file()
    else:
        valid_primary = product.legacy_media and bool(product.image_url)
    if not valid_primary:
        required('primary_media_id', 'Upload and choose a ready primary image', 'media_not_ready')
    for link in product.media_links:
        if link.asset.kind == 'video' and not link.asset.poster_id and link.role != 'hero_video':
            required('media.poster_id', 'Choose a poster for each gallery video', 'poster_required')
    active = [variant for variant in product.variants if variant.is_active]
    if not active: required('variants', 'Add at least one complete active variant')
    for variant in active:
        if not variant.sku or variant.price_minor is None:
            required(f'variants.{variant.id}', 'Active variants need SKU and price')
    if product.is_hero and product.hero_video_url and not product.hero_poster_url:
        required('hero_poster_url', 'A featured video needs a poster image')
    return fields


def product_response(product):
    from sqlalchemy.orm import object_session
    from app.services.media import links_response
    sess = object_session(product)
    stock_by_variant = {}
    if sess and product.variants:
        from app.models.inventory import SupplierVariant, InventoryBalance, StockReservation
        from app.queries.stock_rules import holding_predicate
        from sqlalchemy import select, func
        vids = [v.id for v in product.variants if v.id]
        if vids:
            sv_rows = sess.execute(
                select(SupplierVariant.variant_id, SupplierVariant.id, InventoryBalance.on_hand, InventoryBalance.version, SupplierVariant.supplier_cost_minor)
                .outerjoin(InventoryBalance, InventoryBalance.supplier_variant_id == SupplierVariant.id)
                .where(SupplierVariant.variant_id.in_(vids), SupplierVariant.active.is_(True))
            ).all()
            sv_ids = [r[1] for r in sv_rows if r[1]]
            held_by_sv = {}
            if sv_ids:
                held_res = sess.execute(
                    select(StockReservation.supplier_variant_id, func.sum(StockReservation.quantity))
                    .where(StockReservation.supplier_variant_id.in_(sv_ids), holding_predicate())
                    .group_by(StockReservation.supplier_variant_id)
                ).all()
                held_by_sv = {row[0]: (row[1] or 0) for row in held_res}
            for vid, sv_id, on_hand, ver, cost_minor in sv_rows:
                physical = on_hand or 0
                held = held_by_sv.get(sv_id, 0)
                stock_by_variant[vid] = {
                    'stock_on_hand': physical,
                    'held_reservations': held,
                    'available_to_sell': max(0, physical - held),
                    'supplier_variant_id': str(sv_id) if sv_id else None,
                    'inventory_version': ver,
                    'cost_price_minor': cost_minor,
                }

    return {field: getattr(product, field) for field in (
        'id', 'title', 'slug', 'collection_id', 'status', 'edit_version', 'archived_at',
        'description', 'short_description', 'material', 'care', 'sizing', 'badge',
        'is_hero', 'hero_order', 'hero_benefit', 'image_url', 'hover_image_url', 'hero_image_url',
        'hero_video_url', 'hero_poster_url', 'stock_management_source', 'vendor_id',
        'created_at', 'updated_at')} | {
        'collection_ids': product.collection_ids,
        'publication_requirements': publication_requirements(product),
        'media': links_response(product),
        'vendor_name': product.vendor.name if getattr(product, 'vendor', None) else None,
        'variants': [{
            'id': v.id,
            'sku': v.sku,
            'size': v.size,
            'color': v.color,
            'price_minor': v.price_minor,
            'cost_price_minor': stock_by_variant.get(v.id, {}).get('cost_price_minor'),
            'is_active': v.is_active,
            'availability': v.availability.value,
            'stock_on_hand': stock_by_variant.get(v.id, {}).get('stock_on_hand', 0),
            'held_reservations': stock_by_variant.get(v.id, {}).get('held_reservations', 0),
            'available_to_sell': stock_by_variant.get(v.id, {}).get('available_to_sell', 0),
            'supplier_variant_id': stock_by_variant.get(v.id, {}).get('supplier_variant_id'),
            'inventory_version': stock_by_variant.get(v.id, {}).get('inventory_version'),
        } for v in sorted(product.variants, key=lambda v: v.id)],
    }


def collection_response(collection):
    return {field: getattr(collection, field) for field in
            ('id', 'name', 'slug', 'description', 'display_order', 'is_active', 'edit_version', 'image_url', 'image_media_id')}


def apply_product(db: Session, product, data):
    existing_gaps = {item['field'] for item in publication_requirements(product)} if product.status == 'published' else set()
    data = dict(data)
    variants = data.pop('variants', None)
    data.pop('expected_version', None)

    # Stock responsibility & vendor validation
    new_source = data.get('stock_management_source')
    new_vendor_id = data.get('vendor_id')

    if new_source == 'vendor_managed':
        if not new_vendor_id:
            raise CatalogError('vendor_required', 'An active vendor must be selected for vendor-managed stock', 422,
                               fields=[{'field': 'vendor_id', 'code': 'required', 'message': 'Choose an active shop'}])
        from app.models.suppliers import Supplier
        vendor = db.get(Supplier, new_vendor_id)
        if not vendor or vendor.status != 'active' or vendor.supplier_type != 'external_vendor':
            raise CatalogError('invalid_vendor', 'Selected vendor does not exist or is not active', 422,
                               fields=[{'field': 'vendor_id', 'code': 'invalid', 'message': 'Choose an active shop'}])
    elif new_source == 'alphazee_managed':
        data['vendor_id'] = None

    # Reassignment guard: if product already has an id and stock responsibility changes
    current_source = getattr(product, 'stock_management_source', None)
    current_vendor_id = getattr(product, 'vendor_id', None)
    is_reassignment = current_source is not None and (
        (new_source is not None and new_source != current_source) or
        (new_vendor_id is not None and new_vendor_id != current_vendor_id)
    )
    if is_reassignment and product.id:
        from app.models.inventory import StockReservation, SupplierVariant
        from app.queries.stock_rules import holding_predicate
        from sqlalchemy import func
        v_ids = [v.id for v in product.variants if v.id]
        if v_ids:
            from app.models.inventory import InventoryBalance
            from app.models.vendor_portal import VendorStockShortage
            balances = db.scalars(select(InventoryBalance).join(SupplierVariant).where(
                SupplierVariant.variant_id.in_(v_ids)).order_by(InventoryBalance.supplier_variant_id)
                .with_for_update(of=InventoryBalance)).all()
            if any(balance.on_hand for balance in balances) or db.scalar(select(VendorStockShortage.id).where(
                    VendorStockShortage.variant_id.in_(v_ids), VendorStockShortage.status == 'open').limit(1)):
                raise CatalogError('reassignment_blocked',
                    'Resolve shortages and explicitly reconcile all source stock to zero before changing responsibility.', 409)
            active_holds = db.scalar(
                select(func.count(StockReservation.id))
                .join(SupplierVariant, SupplierVariant.id == StockReservation.supplier_variant_id)
                .where(SupplierVariant.variant_id.in_(v_ids), holding_predicate())
            )
            if active_holds and active_holds > 0:
                raise CatalogError('reassignment_blocked',
                                   'Cannot reassign product stock responsibility while open holds exist. Fulfill or cancel open reservations first.', 409)

    if 'collection_ids' in data:
        raw_col_ids = data.pop('collection_ids') or []
        valid_cols = []
        if raw_col_ids:
            valid_cols = db.scalars(select(Collection).where(Collection.id.in_(raw_col_ids))).all()
            if len(valid_cols) != len(set(raw_col_ids)):
                raise CatalogError('invalid_collection', 'One or more selected collections do not exist')

        from app.models.catalog import ProductCollection
        target_ids = set(raw_col_ids)
        product.collection_links = [
            link for link in (product.collection_links or []) if link.collection_id in target_ids
        ]
        existing_cids = {link.collection_id for link in product.collection_links}
        for cid in raw_col_ids:
            if cid not in existing_cids:
                product.collection_links.append(ProductCollection(product_id=product.id, collection_id=cid))

        if raw_col_ids:
            primary_id = product.collection_id if product.collection_id in target_ids else raw_col_ids[0]
            product.collection_id = primary_id
            product.collection = next((c for c in valid_cols if c.id == primary_id), valid_cols[0])
        else:
            product.collection_id = None
            product.collection = None
        data.pop('collection_id', None)
    elif 'collection_id' in data and data['collection_id'] is not None:
        collection = db.scalar(select(Collection).where(Collection.id == data['collection_id']).with_for_update(read=True))
        if collection is None: raise CatalogError('invalid_collection', 'Collection does not exist')
        product.collection = collection
        product.collection_id = collection.id
        from app.models.catalog import ProductCollection
        existing_cids = {link.collection_id for link in (product.collection_links or [])}
        if collection.id not in existing_cids:
            product.collection_links.append(ProductCollection(product_id=product.id, collection_id=collection.id))
    elif 'collection_id' in data:
        product.collection = None
        product.collection_id = None
        product.collection_links = []
    for key, value in data.items(): setattr(product, key, value)
    seen_ids = set()
    initial_stock_by_variant = {}
    cost_price_by_variant = {}
    for item in variants or []:
        fields = item.model_dump(exclude_unset=True) if hasattr(item, 'model_dump') else dict(item)
        identifier = fields.pop('id', None)
        initial_stock = fields.pop('initial_stock', None)
        cost_price_minor = fields.pop('cost_price_minor', None)
        if identifier is None:
            if not fields.get('sku'): raise CatalogError('invalid_variant', 'New variants require a SKU')
            variant = Variant(product_id=product.id, is_active=False, availability=AvailabilityStatus.UNKNOWN)
            product.variants.append(variant)
        else:
            if identifier in seen_ids: raise CatalogError('duplicate_variant_id', 'A variant cannot occur twice in one save')
            seen_ids.add(identifier)
            variant = next((v for v in product.variants if v.id == identifier), None)
            if variant is None: raise CatalogError('invalid_variant', 'Variant does not belong to this product')
        if initial_stock is not None:
            initial_stock_by_variant[variant] = initial_stock
        if cost_price_minor is not None:
            cost_price_by_variant[variant] = cost_price_minor
        for key, value in fields.items():
            setattr(variant, key, AvailabilityStatus(value) if key == 'availability' else value)
        if not variant.sku: raise CatalogError('invalid_variant', 'SKU cannot be cleared')
        if variant.is_active and variant.price_minor is None:
            raise CatalogError('invalid_variant', 'Enter a price before activating the variant', fields=[{'field': 'variants.price_minor', 'code': 'required', 'message': 'An active variant requires a price'}])

    # Auto-synchronize variant supplier mappings to agree with product stock responsibility
    from app.models.inventory import InventoryBalance, SupplierVariant, StockEvent
    from app.models.suppliers import get_or_create_internal_supplier
    from datetime import datetime, timezone
    target_supplier_id = None
    if product.stock_management_source == 'alphazee_managed' or product.stock_management_source is None:
        internal_sup = get_or_create_internal_supplier(db)
        target_supplier_id = internal_sup.id
    elif product.stock_management_source == 'vendor_managed' and product.vendor_id:
        target_supplier_id = product.vendor_id

    if target_supplier_id:
        db.flush()
        default_cost = 0 if product.stock_management_source != 'vendor_managed' else None
        for v in product.variants:
            if not v.id:
                continue
            desired_cost = cost_price_by_variant.get(v)
            active_sv = db.scalar(select(SupplierVariant).where(
                SupplierVariant.variant_id == v.id,
                SupplierVariant.active.is_(True)
            ))
            if not active_sv:
                initial_cost = desired_cost if desired_cost is not None else default_cost
                sv = SupplierVariant(
                    supplier_id=target_supplier_id,
                    variant_id=v.id,
                    active=True,
                    supplier_cost_minor=initial_cost
                )
                db.add(sv)
                db.flush()
                balance = InventoryBalance(supplier_variant_id=sv.id, on_hand=0)
                db.add(balance)
                db.flush()
                active_sv = sv
            elif is_reassignment and active_sv.supplier_id != target_supplier_id:
                active_sv.active = False
                db.flush()
                new_sv = db.scalar(select(SupplierVariant).where(
                    SupplierVariant.variant_id == v.id,
                    SupplierVariant.supplier_id == target_supplier_id
                ))
                initial_cost = desired_cost if desired_cost is not None else default_cost
                if new_sv:
                    new_sv.active = True
                    if desired_cost is not None:
                        new_sv.supplier_cost_minor = desired_cost
                    active_sv = new_sv
                else:
                    new_sv = SupplierVariant(
                        supplier_id=target_supplier_id,
                        variant_id=v.id,
                        active=True,
                        supplier_cost_minor=initial_cost
                    )
                    db.add(new_sv)
                    db.flush()
                    balance = InventoryBalance(supplier_variant_id=new_sv.id, on_hand=0)
                    db.add(balance)
                    db.flush()
                    active_sv = new_sv
            else:
                if desired_cost is not None and active_sv.supplier_cost_minor != desired_cost:
                    active_sv.supplier_cost_minor = desired_cost
                    db.flush()

            # If an explicit initial / updated stock count was provided
            desired_stock = initial_stock_by_variant.get(v)
            if desired_stock is not None and active_sv:
                balance = db.scalar(select(InventoryBalance).where(InventoryBalance.supplier_variant_id == active_sv.id).with_for_update())
                if balance is None:
                    balance = InventoryBalance(supplier_variant_id=active_sv.id, on_hand=0)
                    db.add(balance)
                    db.flush()
                if balance.on_hand != desired_stock:
                    old_on_hand = balance.on_hand
                    balance.on_hand = desired_stock
                    balance.version = (balance.version or 0) + 1
                    balance.last_counted_at = datetime.now(timezone.utc)
                    db.add(StockEvent(
                        supplier_variant_id=active_sv.id,
                        actor_user_id=None,
                        previous_on_hand=old_on_hand,
                        new_on_hand=desired_stock,
                        delta=desired_stock - old_on_hand,
                        reason='manual_count',
                        notes='Product catalog stock update',
                    ))
                if desired_stock > 0 and v.availability == AvailabilityStatus.UNKNOWN and v.price_minor is not None:
                    v.availability = AvailabilityStatus.AVAILABLE
    else:
        for v in product.variants:
            if not v.id:
                continue
            desired_cost = cost_price_by_variant.get(v)
            if desired_cost is not None:
                active_sv = db.scalar(select(SupplierVariant).where(
                    SupplierVariant.variant_id == v.id,
                    SupplierVariant.active.is_(True)
                ))
                if active_sv and active_sv.supplier_cost_minor != desired_cost:
                    active_sv.supplier_cost_minor = desired_cost
                    db.flush()

    gaps = publication_requirements(product) if product.status == 'published' else []
    new_gaps = [item for item in gaps if item['field'] not in existing_gaps]
    if new_gaps:
        raise CatalogError('publication_invalid', 'Unpublish before clearing required product fields', fields=new_gaps)
    db.flush()


def create_product(db, command):
    product = Product(id='prod-' + uuid.uuid4().hex, status='draft', is_active=False,
                      legacy_media=False, edit_version=1)
    db.add(product)
    with db.no_autoflush:
        apply_product(db, product, command.model_dump(exclude_unset=True, exclude={'variants'}) |
                      ({'variants': command.variants} if command.variants is not None else {}))
    return product


def edit_product(db, identifier, command):
    from app.services.media import reference_lock
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore this product to draft before editing', 409)
    with db.no_autoflush:
        apply_product(db, product, command.model_dump(exclude_unset=True, exclude={'variants', 'media'}) |
                      ({'variants': command.variants} if command.variants is not None else {}))
    if command.media is not None:
        from app.services.media import replace_product_media
        from app.schemas.media import ProductMediaCommand
        product = replace_product_media(db, identifier, ProductMediaCommand(expected_version=command.expected_version, items=command.media))
    else:
        product.edit_version += 1
    return product


def transition(db, identifier, command, action):
    from app.services.media import reference_lock
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if action == 'restore' and product.status != 'archived':
        raise CatalogError('invalid_transition', 'Only an archived product can be restored', 409)
    if action in {'publish', 'unpublish'} and product.status == 'archived':
        raise CatalogError('archived_read_only', 'Restore to draft first', 409)
    if action == 'publish':
        requirements = publication_requirements(product)
        if requirements: raise CatalogError('publication_invalid', 'Complete these requirements before publishing', fields=requirements)
    product.status = {'publish': 'published', 'unpublish': 'draft', 'archive': 'archived', 'restore': 'draft'}[action]
    product.is_active = product.status == 'published'
    product.archived_at = datetime.now(timezone.utc) if product.status == 'archived' else None
    product.edit_version += 1
    return product


def delete_product(db, identifier):
    from app.services.media import reference_lock
    reference_lock(db)
    product = db.get(Product, identifier)
    if product is None:
        raise CatalogError('not_found', 'Product not found', 404)
    if product.status == 'published':
        raise CatalogError('published_cannot_delete', 'Make it unpublished first then delete', 422)

    variant_ids = [v.id for v in product.variants]
    if variant_ids:
        from app.models.orders import OrderLine
        from app.models.inventory import SupplierVariant, InventoryBalance, StockEvent, StockReservation
        from app.models.owned_stock import OwnedStockLot

        has_orders = db.scalar(select(func.count()).select_from(OrderLine).where(OrderLine.variant_id.in_(variant_ids)))
        if has_orders:
            raise CatalogError('cannot_delete_has_orders', 'Cannot delete a product with existing customer orders. Archive it instead.', 409)

        supplier_variant_ids = db.scalars(select(SupplierVariant.id).where(SupplierVariant.variant_id.in_(variant_ids))).all()
        if supplier_variant_ids:
            has_res = db.scalar(select(func.count()).select_from(StockReservation).where(StockReservation.supplier_variant_id.in_(supplier_variant_ids)))
            if has_res:
                raise CatalogError('cannot_delete_has_reservations', 'Cannot delete a product with active stock reservations. Archive it instead.', 409)

            has_events = db.scalar(select(func.count()).select_from(StockEvent).where(StockEvent.supplier_variant_id.in_(supplier_variant_ids)))
            if has_events:
                raise CatalogError('cannot_delete_has_inventory_history', 'Cannot delete a product with stock movement history. Archive it instead.', 409)

            has_owned = db.scalar(select(func.count()).select_from(OwnedStockLot).where(OwnedStockLot.supplier_variant_id.in_(supplier_variant_ids)))
            if has_owned:
                raise CatalogError('cannot_delete_has_owned_stock', 'Cannot delete a product with owned stock units. Archive it instead.', 409)

            db.execute(delete(InventoryBalance).where(InventoryBalance.supplier_variant_id.in_(supplier_variant_ids)))
            db.execute(delete(SupplierVariant).where(SupplierVariant.id.in_(supplier_variant_ids)))

        db.execute(delete(Variant).where(Variant.product_id == identifier))

    from app.models.media import ProductMedia
    db.execute(delete(ProductMedia).where(ProductMedia.product_id == identifier))

    db.delete(product)
    db.flush()
    return product


def create_collection(db, command):
    from app.services.media import ready, reference_lock, public_asset
    reference_lock(db)
    data = command.model_dump()
    identifier = data.pop('image_media_id', None)
    asset = ready(db, identifier, 'image') if identifier else None
    collection = Collection(id='col-' + uuid.uuid4().hex, **data,
                            image_media_id=asset.id if asset else None,
                            image_url=public_asset(asset)['url'] if asset else None)
    db.add(collection); db.flush()
    return collection


def edit_collection(db, identifier, command):
    from app.services.media import ready, reference_lock, public_asset
    reference_lock(db)
    collection = locked(db, Collection, identifier, command.expected_version)
    if 'image_media_id' in command.model_fields_set:
        asset = ready(db, command.image_media_id, 'image') if command.image_media_id else None
        collection.image_media_id = asset.id if asset else None
        collection.image_url = public_asset(asset)['url'] if asset else None
    for key, value in command.model_dump(exclude_unset=True, exclude={'expected_version', 'image_media_id'}).items():
        setattr(collection, key, value)
    collection.edit_version += 1
    return collection


def reorder_collections(db, command):
    ids = [item.id for item in command.items]
    if len(ids) != len(set(ids)): raise CatalogError('duplicate_collection_id', 'Each collection may occur once')
    # A full list is required so a concurrent create cannot silently disappear.
    collections = list(db.scalars(select(Collection).order_by(Collection.id).with_for_update().execution_options(populate_existing=True)))
    if set(ids) != {c.id for c in collections}:
        raise CatalogError('collection_list_changed', 'Reload the complete collection list before reordering', 409)
    versions = {item.id: item.expected_version for item in command.items}
    for collection in collections:
        if versions[collection.id] != collection.edit_version:
            raise CatalogError('edit_conflict', 'A collection changed; reload before reordering', 409)
    for collection in collections:
        collection.display_order = ids.index(collection.id)
        collection.edit_version += 1
    return collections


def delete_collection(db, identifier):
    from app.services.media import reference_lock
    reference_lock(db)
    collection = db.scalar(select(Collection).where(Collection.id == identifier).with_for_update())
    if collection is None:
        raise CatalogError('not_found', 'Collection does not exist', 404)

    # 1. Clear any HeroSlide referencing this collection
    from app.models.media import HeroSlide
    slides = db.scalars(select(HeroSlide).where(HeroSlide.target_collection_id == identifier).with_for_update()).all()
    for slide in slides:
        slide.target_collection_id = None
        slide.edit_version += 1

    # 2. Find all products that had any link to this collection
    from app.models.catalog import ProductCollection
    linked_product_ids = set(db.scalars(select(ProductCollection.product_id).where(ProductCollection.collection_id == identifier)).all())
    linked_product_ids.update(db.scalars(select(Product.id).where(Product.collection_id == identifier)).all())

    # 3. Delete the ProductCollection entries for this collection
    db.execute(delete(ProductCollection).where(ProductCollection.collection_id == identifier))

    # 4. Reassign or clear collection for affected products
    if linked_product_ids:
        affected_products = db.scalars(select(Product).where(Product.id.in_(linked_product_ids)).with_for_update()).all()
        for p in affected_products:
            p.collection_links = [link for link in (p.collection_links or []) if link.collection_id != identifier]
            if p.collection_id == identifier:
                if p.collection_links:
                    p.collection_id = p.collection_links[0].collection_id
                    p.collection = db.get(Collection, p.collection_id)
                else:
                    p.collection_id = None
                    p.collection = None
            p.edit_version += 1

    db.delete(collection)
    db.flush()
    return collection

