"""Media transactions serialize reference edits/deletion; files precede ready rows."""
from datetime import datetime, timezone
import hashlib
import os
import uuid
from sqlalchemy import delete, select, text
from app.models.catalog import Collection, Product
from app.models.media import MediaAsset, ProductMedia
from app.services.owner_catalog import CatalogError, locked, publication_requirements
from app.services import media_storage as storage

REFERENCE_LOCK = 7814620193981


def reference_lock(db):
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': REFERENCE_LOCK})


def staging_lock_key(identifier):
    return int.from_bytes(hashlib.sha256(('media-stage:' + identifier).encode()).digest()[:8], 'big', signed=True)


def public_asset(asset):
    return {field: getattr(asset, field) for field in ('id', 'kind', 'content_type', 'byte_size', 'width', 'height', 'duration_ms', 'poster_id')} | {'url': f'/api/v1/media/{asset.id}/content'}


def owner_asset(asset, db=None):
    result = public_asset(asset) | {field: getattr(asset, field) for field in ('original_name', 'checksum', 'state', 'edit_version', 'created_at')}
    if db is not None: result['usage'] = usage(db, asset.id)
    return result


def links_response(product):
    return [{'asset': public_asset(link.asset), 'role': link.role, 'variant_id': link.variant_id,
             'display_order': link.display_order, 'alt_text': link.alt_text}
            for link in product.media_links]


def ready(db, identifier, kind=None):
    asset = db.get(MediaAsset, identifier)
    if asset is None or asset.state != 'ready' or not storage.object_path(asset.storage_key).is_file():
        raise CatalogError('media_not_ready', 'Choose an existing ready media asset')
    if kind and asset.kind != kind:
        raise CatalogError('wrong_media_kind', f'This role requires an {kind}')
    return asset


def ingest(db, upload, owner):
    kind, extension, limit = storage.upload_type(upload.filename, upload.content_type)
    identifier = uuid.uuid4().hex
    staging, _ = storage.paths()
    path = staging / (identifier + '.upload')
    final = None
    commit_started = False
    # Cleanup can recognize an active upload even before its metadata exists.
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': staging_lock_key(identifier)})
    try:
        count = 0
        with path.open('xb') as target:
            while chunk := upload.file.read(1024 * 1024):
                count += len(chunk)
                if count > limit:
                    raise CatalogError('media_too_large', f'{kind.title()} exceeds its byte limit', 413)
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if count == 0: raise CatalogError('empty_media', 'Choose a nonempty media file')
        metadata, extension = storage.validate(path, kind, extension)
        reference_lock(db)
        key = identifier + extension
        final = storage.object_path(key)
        os.replace(path, final)
        with final.open('r+b') as durable:
            durable.flush()
            os.fsync(durable.fileno())
        if os.name != 'nt':
            descriptor = os.open(str(final.parent), os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        # A crash after rename leaves an unreferenced object; age-based cleanup handles it.
        asset = MediaAsset(id=identifier, storage_key=key, original_name=upload.filename,
                           creator_id=owner.owner.user_id, state='ready', **metadata)
        db.add(asset)
        db.flush()
        result = owner_asset(asset)
        commit_started = True
        db.commit()
        return result
    except Exception:
        db.rollback()
        # A lost commit acknowledgment may still mean PostgreSQL committed.
        # Preserve bytes in that case; cleanup removes only confirmed orphans.
        if final is not None and not commit_started: final.unlink(missing_ok=True)
        raise
    finally:
        path.unlink(missing_ok=True)


def usage(db, identifier):
    return {
        'products': [{'product_id': p, 'product_title': title or 'Untitled draft', 'role': r, 'variant_id': v} for p, title, r, v in db.execute(
            select(ProductMedia.product_id, Product.title, ProductMedia.role, ProductMedia.variant_id).join(Product).where(ProductMedia.asset_id == identifier))],
        'collections': list(db.scalars(select(Collection.id).where(Collection.image_media_id == identifier))),
        'posters_for': list(db.scalars(select(MediaAsset.id).where(MediaAsset.poster_id == identifier, MediaAsset.state == 'ready'))),
    }


def replace_product_media(db, identifier, command):
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore to draft before editing', 409)
    variants = {v.id for v in product.variants}
    seen, singles = set(), set()
    rows = []
    for item in command.items:
        key = (item.asset_id, item.role, item.variant_id)
        if key in seen or (item.role != 'gallery' and item.role in singles):
            raise CatalogError('duplicate_media_role', 'Each primary/hero role must have one asset; gallery links must be unique')
        seen.add(key)
        if item.role != 'gallery': singles.add(item.role)
        if item.variant_id is not None and (item.variant_id not in variants or item.role != 'gallery'):
            raise CatalogError('invalid_media_variant', 'Variant gallery media must belong to this product')
        kind = 'video' if item.role == 'hero_video' else ('image' if item.role != 'gallery' else None)
        asset = ready(db, item.asset_id, kind)
        if product.status == 'published' and item.role == 'gallery' and asset.kind == 'video' and not asset.poster_id:
            raise CatalogError('poster_required', 'Choose a poster before attaching a gallery video to a published product')
        rows.append(ProductMedia(product_id=product.id, asset_id=asset.id, asset=asset, **item.model_dump(exclude={'asset_id'})))
    roles = {r.role: r.asset for r in rows if r.role != 'gallery'}
    if 'hero_video' in roles and 'hero_poster' not in roles:
        if not roles['hero_video'].poster_id: raise CatalogError('poster_required', 'Choose a poster before attaching a featured video')
        poster = ready(db, roles['hero_video'].poster_id, 'image')
        roles['hero_poster'] = poster
        rows.append(ProductMedia(product_id=product.id, asset_id=poster.id, asset=poster, role='hero_poster', display_order=0, alt_text=''))
    if product.status == 'published' and 'primary' not in roles:
        raise CatalogError('primary_required', 'Choose a replacement primary image or unpublish first')
    db.execute(delete(ProductMedia).where(ProductMedia.product_id == product.id))
    db.flush()
    # expire avoids stale ORM links from the bulk delete.
    db.expire(product, ['media_links'])
    product.media_links = rows
    product.legacy_media = False
    for role, field in (('primary', 'image_url'), ('hero_image', 'hero_image_url'), ('hero_video', 'hero_video_url'), ('hero_poster', 'hero_poster_url')):
        setattr(product, field, public_asset(roles[role])['url'] if role in roles else None)
    product.edit_version += 1
    db.flush()
    return product


def set_collection_media(db, identifier, command):
    reference_lock(db)
    collection = locked(db, Collection, identifier, command.expected_version)
    asset = ready(db, command.asset_id, 'image') if command.asset_id else None
    collection.image_media_id = asset.id if asset else None
    collection.image_url = public_asset(asset)['url'] if asset else None
    collection.edit_version += 1
    return collection


def set_poster(db, identifier, command):
    reference_lock(db)
    asset = locked(db, MediaAsset, identifier, command.expected_version)
    if asset.state != 'ready' or asset.kind != 'video':
        raise CatalogError('wrong_media_kind', 'Choose a ready video')
    poster = ready(db, command.poster_id, 'image') if command.poster_id else None
    if poster is None and db.scalar(select(ProductMedia.id).join(Product).where(
            ProductMedia.asset_id == asset.id, ProductMedia.role == 'gallery', Product.status == 'published').limit(1)):
        raise CatalogError('poster_required', 'Unpublish or detach gallery videos before clearing their posters', 409)
    asset.poster_id = poster.id if poster else None
    asset.edit_version += 1
    return asset


def delete_asset(db, identifier, command):
    reference_lock(db)
    asset = locked(db, MediaAsset, identifier, command.expected_version)
    references = usage(db, identifier)
    if any(references.values()):
        raise CatalogError('media_in_use', 'Detach this asset from all products, collections and video posters first', 409,
                           fields=[{'field': 'usage', 'message': references}])
    asset.state = 'deleted'
    asset.poster_id = None
    asset.edit_version += 1
    path = storage.object_path(asset.storage_key)
    db.commit()
    # Tombstone first: a failed unlink cannot make deleted bytes publicly accessible.
    try: path.unlink(missing_ok=True)
    except OSError: pass  # scoped cleanup retries the tombstoned object later
    return {'id': identifier, 'state': 'deleted'}


def cleanup(db, minimum_age_hours=24, dry_run=True):
    if minimum_age_hours < 24: raise ValueError('Cleanup requires at least a 24-hour grace period')
    reference_lock(db)
    staging, objects = storage.paths()
    cutoff = datetime.now(timezone.utc).timestamp() - minimum_age_hours * 3600
    candidates = []
    import re
    for directory in (staging, objects):
        for path in directory.iterdir():
            pattern = r'[a-f0-9]{32}\.(upload|clean)' if directory == staging else r'[a-f0-9]{32}\.(jpg|png|webp|mp4|webm)'
            if path.is_symlink() or not path.is_file() or not re.fullmatch(pattern, path.name) or path.stat().st_mtime >= cutoff: continue
            if directory == staging and not db.scalar(text('SELECT pg_try_advisory_xact_lock(:key)'), {'key': staging_lock_key(path.stem)}): continue
            asset = db.scalar(select(MediaAsset).where(MediaAsset.storage_key == path.name)) if directory == objects else None
            if asset is not None and asset.state == 'ready': continue
            candidates.append(str(path.relative_to(directory.parent)))
            if not dry_run: path.unlink()
    db.commit()
    return {'dry_run': dry_run, 'minimum_age_hours': minimum_age_hours, 'files': candidates}
