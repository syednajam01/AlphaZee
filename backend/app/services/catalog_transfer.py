"""Explicit catalog-only bundles. Source transactions are read-only; import is lab-only."""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import zipfile

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from app.config import settings
from app.models.auth import OwnerCredential
from app.models.catalog import Collection, Product, Variant
from app.models.media import MediaAsset, ProductMedia
from app.models.inventory import SupplierVariant, InventoryBalance
from app.models.suppliers import Supplier
from app.schemas.owner_catalog import Command, ProductCreate, CollectionCreate, VariantEdit
from app.schemas.media import MediaLink, ProductMediaCommand
from app.services import media_storage as storage
from app.services.owner_catalog import apply_product, create_collection
from app.services.media import replace_product_media, reference_lock
from app.queries.inventory import adjust_inventory

LIMIT = 512 * 1024 * 1024


def database_identity(url):
    target = make_url(url)
    host = 'loopback' if target.host in {'localhost', '127.0.0.1', '::1'} else target.host
    return hashlib.sha256(json.dumps([host, target.port or 5432, target.database]).encode()).hexdigest()


class Asset(Command):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    filename: str = Field(max_length=200)
    content_type: str
    checksum: str = Field(pattern=r'^[a-f0-9]{64}$')
    byte_size: int = Field(gt=0, le=storage.VIDEO_LIMIT)
    poster_id: str | None = None


class VariantCopy(Command):
    source_id: int = Field(gt=0)
    fields: VariantEdit
    cost_minor: int | None = Field(default=None, strict=True, ge=0, le=2147483647)


class ProductCopy(Command):
    source_id: str = Field(min_length=1, max_length=100)
    fields: ProductCreate
    variants: list[VariantCopy] = Field(max_length=200)
    media: list[MediaLink] = Field(max_length=100)


class CollectionCopy(Command):
    source_id: str
    fields: CollectionCreate


class Bundle(Command):
    version: int = Field(default=1, ge=1, le=1)
    source_identity: str = Field(pattern=r'^[a-f0-9]{64}$')
    products: list[ProductCopy] = Field(min_length=1, max_length=100)
    collections: list[CollectionCopy] = Field(max_length=100)
    assets: list[Asset] = Field(max_length=1000)


def canonical(bundle):
    return json.dumps(bundle.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode()


def export_bundle(db, product_ids, output, include_costs=False):
    """Caller must start a REPEATABLE READ, READ ONLY transaction before queries."""
    if db.scalar(text('SHOW transaction_read_only')) != 'on':
        raise ValueError('Catalog export requires a read-only transaction')
    reference_lock(db)
    requested = sorted(set(product_ids))
    if not requested or len(requested) > 100:
        raise ValueError('Select 1–100 product IDs explicitly')
    products = [db.get(Product, identifier) for identifier in requested]
    if any(p is None for p in products):
        raise ValueError('A selected product does not exist')
    collections = {}; assets = {}; rows = []
    def add_asset(identifier):
        if not identifier or identifier in assets: return
        asset = db.get(MediaAsset, identifier)
        if not asset or asset.state != 'ready': raise ValueError('Selected media is not ready')
        path = storage.object_path(asset.storage_key)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset.checksum:
            raise ValueError('Source media checksum mismatch')
        assets[identifier] = (asset, path)
        add_asset(asset.poster_id)
    fields = set(ProductCreate.model_fields) - {'variants'}
    for p in products:
        if p.collection_id:
            col = p.collection
            collections[col.id] = CollectionCopy(source_id=col.id, fields=CollectionCreate(
                **{key: getattr(col, key) for key in CollectionCreate.model_fields}))
            add_asset(col.image_media_id)
        variants = []
        for v in sorted(p.variants, key=lambda item:item.id):
            cost = db.scalar(select(SupplierVariant.supplier_cost_minor).where(SupplierVariant.variant_id == v.id, SupplierVariant.active.is_(True))) if include_costs else None
            variants.append(VariantCopy(source_id=v.id, fields={
                'sku':v.sku, 'size':v.size, 'color':v.color, 'price_minor':v.price_minor,
                'is_active':v.is_active, 'availability':v.availability.value}, cost_minor=cost))
        links = []
        for link in p.media_links:
            add_asset(link.asset_id)
            links.append(MediaLink(asset_id=link.asset_id, role=link.role, variant_id=link.variant_id,
                                   display_order=link.display_order, alt_text=link.alt_text))
        rows.append(ProductCopy(source_id=p.id, fields=ProductCreate(**{key:getattr(p,key) for key in fields}), variants=variants, media=links))
    bundle = Bundle(source_identity=database_identity(settings.database_url), products=rows,
                    collections=[collections[k] for k in sorted(collections)], assets=[Asset(
                        id=a.id, filename=a.original_name, content_type=a.content_type, checksum=a.checksum,
                        byte_size=a.byte_size, poster_id=a.poster_id) for a,_ in (assets[k] for k in sorted(assets))])
    if sum(a.byte_size for a in bundle.assets) > LIMIT: raise ValueError('Bundle exceeds 512 MiB')
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation never overwrites a prior export.
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('manifest.json', canonical(bundle))
        for key, (_, path) in assets.items(): archive.write(path, 'assets/'+key)
    return bundle


def read_bundle(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [i.filename for i in entries]
        if len(names) != len(set(names)) or sum(i.file_size for i in entries)>LIMIT+2*1024*1024:
            raise ValueError('Duplicate entries or oversized bundle')
        if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size>2*1024*1024:
            raise ValueError('Missing or oversized manifest')
        bundle = Bundle.model_validate_json(archive.read('manifest.json'))
        if len({p.source_id for p in bundle.products}) != len(bundle.products) or len({a.id for a in bundle.assets}) != len(bundle.assets):
            raise ValueError('Duplicate product/media identities')
        allowed = {'manifest.json'} | {'assets/'+a.id for a in bundle.assets}
        if set(names) != allowed: raise ValueError('Unexpected bundle paths or missing media')
        collections={c.source_id for c in bundle.collections}
        assets={a.id:a for a in bundle.assets}
        if len(collections)!=len(bundle.collections): raise ValueError('Duplicate collection identities')
        skus=set();variant_ids=set();slugs=set()
        for product in bundle.products:
            if product.fields.variants is not None: raise ValueError('Variants must use the explicit variant mapping')
            if product.fields.collection_id and product.fields.collection_id not in collections: raise ValueError('Missing collection reference')
            if product.fields.slug:
                if product.fields.slug in slugs: raise ValueError('Duplicate product slug')
                slugs.add(product.fields.slug)
            local=set()
            for v in product.variants:
                if v.source_id in variant_ids or v.fields.id is not None or not v.fields.sku or v.fields.sku in skus:
                    raise ValueError('Duplicate or invalid variant identity/SKU')
                variant_ids.add(v.source_id);local.add(v.source_id);skus.add(v.fields.sku)
            for link in product.media:
                if link.asset_id not in assets or link.variant_id is not None and link.variant_id not in local:
                    raise ValueError('Invalid media/variant reference')
        for col in bundle.collections:
            if col.fields.image_media_id and col.fields.image_media_id not in assets: raise ValueError('Missing collection image')
        for asset in bundle.assets:
            if asset.poster_id and (asset.poster_id not in assets or not assets[asset.poster_id].content_type.startswith('image/')):
                raise ValueError('Missing or invalid poster')
        data = {}
        for asset in bundle.assets:
            content = archive.read('assets/'+asset.id)
            if len(content)!=asset.byte_size or hashlib.sha256(content).hexdigest()!=asset.checksum:
                raise ValueError('Bundle media checksum mismatch')
            storage.upload_type(asset.filename, asset.content_type)
            data[asset.id] = content
        return bundle, data


def import_bundle(db, path, username, stock=0, apply=False):
    if not settings.checkout_lab or not settings.checkout_enabled or make_url(settings.database_url).database != 'alphazee_checkout_test':
        raise ValueError('Import requires the isolated alphazee_checkout_test lab')
    if type(stock) is not int or not 0<=stock<=2147483647: raise ValueError('Choose an explicit nonnegative starting quantity')
    bundle, contents = read_bundle(path)
    if bundle.source_identity == database_identity(settings.database_url): raise ValueError('Source and destination must differ')
    owner = db.scalar(select(OwnerCredential).where(OwnerCredential.username==username, OwnerCredential.enabled.is_(True)))
    if owner is None: raise ValueError('Provision a separate lab owner first')
    digest = hashlib.sha256(canonical(bundle)).hexdigest()
    def identifier(kind, old): return hashlib.sha256((digest+kind+str(old)).encode()).hexdigest()[:32]
    report = {'bundle':digest, 'dry_run':not apply, 'products':[], 'starting_quantity':stock,
              'copies_customers_orders_sessions':False, 'source_modified':False}
    staged=[]; created=[]; commit_started=False
    try:
        # Serialize imports with catalog attachment/deletion; retries never overwrite edits.
        reference_lock(db)
        skipped=[]
        for row in bundle.products:
            product_id='lab-'+identifier('product', row.source_id)
            exists=db.get(Product,product_id)
            report['products'].append({'source_id':row.source_id, 'id':product_id, 'action':'skip_existing' if exists else 'create_draft'})
            skipped.append(bool(exists))
            if not exists and row.fields.slug and db.scalar(select(Product.id).where(Product.slug==row.fields.slug)):
                raise ValueError('Product slug collision; review destination or export a distinct slug')
        if any(skipped) and not all(skipped): raise ValueError('Partial prior import detected; review before retry')
        if not all(skipped):
            skus=[v.fields.sku for p in bundle.products for v in p.variants]
            if db.scalar(select(Variant.id).where(Variant.sku.in_(skus)).limit(1)): raise ValueError('Variant SKU collision')
            slugs=[c.fields.slug for c in bundle.collections]
            if db.scalar(select(Collection.id).where(Collection.slug.in_(slugs)).limit(1)): raise ValueError('Collection slug collision')
        # Validate bytes again, including decoding and media limits, even for dry runs.
        metadata={}
        staging,_=storage.paths()
        for asset in bundle.assets:
            kind, extension, limit=storage.upload_type(asset.filename,asset.content_type)
            if asset.byte_size>limit: raise ValueError('Media exceeds its format limit')
            stage=staging/(uuid.uuid4().hex+'.upload'); staged.append(stage)
            stage.write_bytes(contents[asset.id])
            meta,extension=storage.validate(stage,kind,extension)
            metadata[asset.id]=(meta,extension,stage)
        if not apply or all(skipped): return report
        media_map={a.id:identifier('asset',a.id) for a in bundle.assets}
        for asset in bundle.assets:
            meta,extension,stage=metadata[asset.id]; key=media_map[asset.id]+extension
            final=storage.object_path(key)
            if final.exists() or db.get(MediaAsset,media_map[asset.id]): raise ValueError('Media identity collision')
            with final.open('xb') as target:
                created.append(final); target.write(stage.read_bytes()); target.flush(); os.fsync(target.fileno())
            db.add(MediaAsset(id=media_map[asset.id],storage_key=key,original_name=asset.filename,
                              creator_id=owner.user_id,state='ready',**meta))
        db.flush()
        for asset in bundle.assets:
            if asset.poster_id:
                if asset.poster_id not in media_map: raise ValueError('Missing video poster')
                poster=db.get(MediaAsset,media_map[asset.poster_id])
                if poster.kind!='image': raise ValueError('Poster must be an image')
                db.get(MediaAsset,media_map[asset.id]).poster_id=poster.id
        collection_map={}
        for row in bundle.collections:
            col_id='lab-'+identifier('collection',row.source_id);collection_map[row.source_id]=col_id
            values=row.fields.model_dump()
            values['image_media_id']=media_map.get(values['image_media_id']) if values['image_media_id'] else None
            if db.scalar(select(Collection.id).where(Collection.slug==values['slug'])): raise ValueError('Collection slug collision')
            col=create_collection(db,CollectionCreate(**values)); col.id=col_id;db.flush()
        supplier=Supplier(name='SAMPLE imported catalog '+digest[:8],slug='lab-'+digest[:24],status='active')
        db.add(supplier);db.flush()
        for row in bundle.products:
            values=row.fields.model_dump(exclude={'variants'})
            values['collection_id']=collection_map.get(values['collection_id'])
            values['stock_management_source'] = 'vendor_managed'
            values['vendor_id'] = supplier.id
            # Validate variant commands through the existing authoring schema.
            values['variants']=[v.fields.model_dump(exclude={'id'}) for v in row.variants]
            command=ProductCreate(**values)
            product=Product(id='lab-'+identifier('product',row.source_id),status='draft',is_active=False,legacy_media=False,edit_version=1)
            db.add(product)
            apply_product(db,product,command.model_dump(exclude={'variants'})|{'variants':command.variants})
            variant_map={v.source_id:new.id for v,new in zip(row.variants,product.variants)}
            for v,new in zip(row.variants,product.variants):
                if v.cost_minor is None: continue
                # Authoring already created the source mapping and empty balance.
                link=db.scalar(select(SupplierVariant).where(SupplierVariant.variant_id==new.id,
                    SupplierVariant.supplier_id==supplier.id, SupplierVariant.active.is_(True)))
                link.supplier_cost_minor=v.cost_minor
                db.flush()
                balance=db.get(InventoryBalance,link.id)
                if stock: adjust_inventory(db,supplier_variant_id=link.id,actor_user_id=owner.user_id,
                    new_on_hand=stock,expected_version=balance.version,reason='supplier_receipt',notes='SAMPLE lab import '+digest)
            links=[]
            for link in row.media:
                if link.asset_id not in media_map or link.variant_id is not None and link.variant_id not in variant_map:
                    raise ValueError('Invalid media/variant reference')
                links.append(MediaLink(**(link.model_dump()|{'asset_id':media_map[link.asset_id],
                    'variant_id':variant_map.get(link.variant_id) if link.variant_id is not None else None})))
            replace_product_media(db,product.id,ProductMediaCommand(expected_version=product.edit_version,items=links))
        db.flush();commit_started=True;db.commit()
        return report
    except Exception:
        db.rollback()
        if not commit_started:
            for path in created: path.unlink(missing_ok=True)
        raise
    finally:
        for path in staged: path.unlink(missing_ok=True)
