"""Transactional owner editing without stock writes or historical snapshot edits."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import select
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
    if not product.collection or not product.collection.is_active:
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
    from app.services.media import links_response
    return {field: getattr(product, field) for field in (
        'id', 'title', 'slug', 'collection_id', 'status', 'edit_version', 'archived_at',
        'description', 'short_description', 'material', 'care', 'sizing', 'badge',
        'is_hero', 'hero_order', 'hero_benefit', 'image_url', 'hover_image_url', 'hero_image_url',
        'hero_video_url', 'hero_poster_url', 'stock_management_source', 'vendor_id',
        'created_at', 'updated_at')} | {
        'publication_requirements': publication_requirements(product),
        'media': links_response(product),
        'vendor_name': product.vendor.name if getattr(product, 'vendor', None) else None,
        'variants': [{'id': v.id, 'sku': v.sku, 'size': v.size, 'color': v.color,
                      'price_minor': v.price_minor, 'is_active': v.is_active,
                      'availability': v.availability.value} for v in sorted(product.variants, key=lambda v: v.id)],
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
        if not vendor or vendor.status != 'active':
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
            active_holds = db.scalar(
                select(func.count(StockReservation.id))
                .join(SupplierVariant, SupplierVariant.id == StockReservation.supplier_variant_id)
                .where(SupplierVariant.variant_id.in_(v_ids), holding_predicate())
            )
            if active_holds and active_holds > 0:
                raise CatalogError('reassignment_blocked',
                                   'Cannot reassign product stock responsibility while open holds exist. Fulfill or cancel open reservations first.', 409)

    if 'collection_id' in data and data['collection_id'] is not None:
        collection = db.scalar(select(Collection).where(Collection.id == data['collection_id']).with_for_update(read=True))
        if collection is None: raise CatalogError('invalid_collection', 'Collection does not exist')
        product.collection = collection
    elif 'collection_id' in data:
        product.collection = None
    for key, value in data.items(): setattr(product, key, value)
    seen_ids = set()
    for item in variants or []:
        fields = item.model_dump(exclude_unset=True) if hasattr(item, 'model_dump') else dict(item)
        identifier = fields.pop('id', None)
        if identifier is None:
            if not fields.get('sku'): raise CatalogError('invalid_variant', 'New variants require a SKU')
            variant = Variant(product_id=product.id, is_active=False, availability=AvailabilityStatus.UNKNOWN)
            product.variants.append(variant)
        else:
            if identifier in seen_ids: raise CatalogError('duplicate_variant_id', 'A variant cannot occur twice in one save')
            seen_ids.add(identifier)
            variant = next((v for v in product.variants if v.id == identifier), None)
            if variant is None: raise CatalogError('invalid_variant', 'Variant does not belong to this product')
        for key, value in fields.items():
            setattr(variant, key, AvailabilityStatus(value) if key == 'availability' else value)
        if not variant.sku: raise CatalogError('invalid_variant', 'SKU cannot be cleared')
        if variant.is_active and variant.price_minor is None:
            raise CatalogError('invalid_variant', 'Enter a price before activating the variant', fields=[{'field': 'variants.price_minor', 'code': 'required', 'message': 'An active variant requires a price'}])

    # Auto-synchronize variant supplier mappings to agree with product stock responsibility
    from app.models.inventory import InventoryBalance, SupplierVariant
    from app.models.suppliers import get_or_create_internal_supplier
    target_supplier_id = None
    if product.stock_management_source == 'alphazee_managed':
        internal_sup = get_or_create_internal_supplier(db)
        target_supplier_id = internal_sup.id
    elif product.stock_management_source == 'vendor_managed' and product.vendor_id:
        target_supplier_id = product.vendor_id

    if target_supplier_id:
        db.flush()
        for v in product.variants:
            if not v.id:
                continue
            active_sv = db.scalar(select(SupplierVariant).where(
                SupplierVariant.variant_id == v.id,
                SupplierVariant.active.is_(True)
            ))
            if not active_sv:
                sv = SupplierVariant(
                    supplier_id=target_supplier_id,
                    variant_id=v.id,
                    active=True,
                    supplier_cost_minor=0
                )
                db.add(sv)
                db.flush()
                db.add(InventoryBalance(supplier_variant_id=sv.id, on_hand=0))
            elif is_reassignment and active_sv.supplier_id != target_supplier_id:
                active_sv.active = False
                new_sv = db.scalar(select(SupplierVariant).where(
                    SupplierVariant.variant_id == v.id,
                    SupplierVariant.supplier_id == target_supplier_id
                ))
                if new_sv:
                    new_sv.active = True
                else:
                    new_sv = SupplierVariant(
                        supplier_id=target_supplier_id,
                        variant_id=v.id,
                        active=True,
                        supplier_cost_minor=active_sv.supplier_cost_minor
                    )
                    db.add(new_sv)
                    db.flush()
                    db.add(InventoryBalance(supplier_variant_id=new_sv.id, on_hand=0))

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
