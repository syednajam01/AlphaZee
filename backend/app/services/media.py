"""Media transactions serialize reference edits/deletion; files precede ready rows."""
from datetime import datetime, timezone
import hashlib
import os
import uuid
from sqlalchemy import delete, func, select, text
from app.models.catalog import Collection, Product
from app.models.media import MediaAsset, ProductMedia, HeroSlide
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
    return [{'id': link.id, 'asset': public_asset(link.asset), 'role': link.role, 'variant_id': link.variant_id,
             'display_order': link.display_order, 'alt_text': link.alt_text}
            for link in sorted(product.media_links, key=lambda l: (l.display_order, l.id or 0))]


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
        'hero_slides': list(db.scalars(select(HeroSlide.id).where(
            (HeroSlide.video_asset_id == identifier) | (HeroSlide.poster_asset_id == identifier) | (HeroSlide.image_asset_id == identifier)))),
    }


def sync_product_roles(product):
    roles = {m.role: m.asset for m in product.media_links if m.role != 'gallery'}
    for role, field in (('primary', 'image_url'), ('hover_image', 'hover_image_url'),
                        ('hero_image', 'hero_image_url'), ('hero_video', 'hero_video_url'), ('hero_poster', 'hero_poster_url')):
        if hasattr(product, field):
            setattr(product, field, public_asset(roles[role])['url'] if role in roles else None)


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
            raise CatalogError('duplicate_media_role', 'Each primary/hero/hover role must have one asset; gallery links must be unique')
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
    sync_product_roles(product)
    product.edit_version += 1
    db.flush()
    return product


def attach_product_media(db, identifier, command):
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore to draft before editing', 409)

    kind = 'video' if command.role == 'hero_video' else ('image' if command.role != 'gallery' else None)
    asset = ready(db, command.asset_id, kind)

    if product.status == 'published' and command.role == 'gallery' and asset.kind == 'video' and not asset.poster_id:
        raise CatalogError('poster_required', 'Choose a poster before attaching a gallery video to a published product')

    if command.variant_id is not None:
        variants = {v.id for v in product.variants}
        if command.variant_id not in variants or command.role != 'gallery':
            raise CatalogError('invalid_media_variant', 'Variant gallery media must belong to this product')

    # If attaching a single role (primary, hover_image, etc.), replace any existing link with that role
    if command.role != 'gallery':
        for existing in list(product.media_links):
            if existing.role == command.role:
                db.delete(existing)
        db.flush()
        db.expire(product, ['media_links'])

    order = command.display_order if command.display_order is not None else len(product.media_links)
    link = ProductMedia(
        product_id=product.id,
        asset_id=asset.id,
        asset=asset,
        role=command.role,
        variant_id=command.variant_id,
        display_order=order,
        alt_text=command.alt_text,
    )
    product.media_links.append(link)
    product.legacy_media = False
    sync_product_roles(product)
    product.edit_version += 1
    db.flush()
    return product


def detach_product_media(db, identifier, command):
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore to draft before editing', 409)

    target_link = None
    if command.link_id is not None:
        target_link = next((l for l in product.media_links if l.id == command.link_id), None)
    elif command.asset_id and command.role:
        target_link = next((l for l in product.media_links if l.asset_id == command.asset_id and l.role == command.role), None)
    elif command.asset_id:
        target_link = next((l for l in product.media_links if l.asset_id == command.asset_id), None)

    if not target_link:
        raise CatalogError('link_not_found', 'Media attachment not found', 404)

    if target_link.role == 'primary' and product.status == 'published':
        raise CatalogError('primary_required', 'Choose a replacement primary image or unpublish first', 409)

    db.delete(target_link)
    db.flush()
    db.expire(product, ['media_links'])
    sync_product_roles(product)
    product.edit_version += 1
    db.flush()
    return product


def reorder_product_media(db, identifier, command):
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore to draft before editing', 409)

    links_by_id = {l.id: l for l in product.media_links}
    for order, link_id in enumerate(command.link_ids):
        if link_id in links_by_id:
            links_by_id[link_id].display_order = order

    product.edit_version += 1
    db.flush()
    return product


def set_product_roles(db, identifier, command):
    reference_lock(db)
    product = locked(db, Product, identifier, command.expected_version)
    if product.status == 'archived': raise CatalogError('archived_read_only', 'Restore to draft before editing', 409)

    if 'primary_asset_id' in command.model_fields_set:
        if command.primary_asset_id:
            primary_asset = ready(db, command.primary_asset_id, 'image')
            for l in list(product.media_links):
                if l.role == 'primary': db.delete(l)
            db.flush()
            db.expire(product, ['media_links'])
            product.media_links.append(ProductMedia(
                product_id=product.id, asset_id=primary_asset.id, asset=primary_asset,
                role='primary', display_order=0, alt_text=''
            ))
        elif product.status == 'published':
            raise CatalogError('primary_required', 'Published products require a primary image', 409)

    if 'hover_asset_id' in command.model_fields_set:
        if command.hover_asset_id:
            hover_asset = ready(db, command.hover_asset_id, 'image')
            for l in list(product.media_links):
                if l.role == 'hover_image': db.delete(l)
            db.flush()
            db.expire(product, ['media_links'])
            product.media_links.append(ProductMedia(
                product_id=product.id, asset_id=hover_asset.id, asset=hover_asset,
                role='hover_image', display_order=0, alt_text=''
            ))
        else:
            for l in list(product.media_links):
                if l.role == 'hover_image': db.delete(l)
            db.flush()
            db.expire(product, ['media_links'])

    sync_product_roles(product)
    product.edit_version += 1
    db.flush()
    return product


def hero_slide_response(slide):
    from app.services.owner_catalog import collection_response
    video = public_asset(slide.video) if slide.video else None
    poster = public_asset(slide.poster) if slide.poster else None
    image = public_asset(slide.image) if slide.image else None
    product_dict = None
    if slide.product:
        product_dict = {
            'id': slide.product.id,
            'title': slide.product.title,
            'slug': slide.product.slug,
            'status': slide.product.status,
            'is_active': slide.product.is_active,
        }
    collection_dict = None
    if slide.collection:
        collection_dict = collection_response(slide.collection)
    return {
        'id': slide.id,
        'title': slide.title,
        'benefit': slide.benefit,
        'video_asset_id': slide.video_asset_id,
        'poster_asset_id': slide.poster_asset_id,
        'image_asset_id': slide.image_asset_id,
        'video': video,
        'poster': poster,
        'image': image,
        'video_url': video['url'] if video else None,
        'poster_url': poster['url'] if poster else None,
        'image_url': image['url'] if image else None,
        'display_order': slide.display_order,
        'is_enabled': slide.is_enabled,
        'target_product_id': slide.target_product_id,
        'target_collection_id': slide.target_collection_id,
        'product': product_dict,
        'collection': collection_dict,
        'edit_version': slide.edit_version,
        'created_at': slide.created_at.isoformat() if slide.created_at else None,
        'updated_at': slide.updated_at.isoformat() if slide.updated_at else None,
    }


def list_hero_slides(db, include_disabled=True):
    from sqlalchemy.orm import selectinload
    stmt = select(HeroSlide).options(
        selectinload(HeroSlide.video).selectinload(MediaAsset.poster),
        selectinload(HeroSlide.poster),
        selectinload(HeroSlide.image),
        selectinload(HeroSlide.product),
        selectinload(HeroSlide.collection),
    )
    if not include_disabled:
        stmt = stmt.where(HeroSlide.is_enabled.is_(True))
    slides = list(db.scalars(stmt.order_by(HeroSlide.display_order.asc(), HeroSlide.id.asc())))
    return [hero_slide_response(s) for s in slides]


def create_hero_slide(db, command):
    reference_lock(db)
    video = ready(db, command.video_asset_id, 'video') if command.video_asset_id else None
    poster = ready(db, command.poster_asset_id, 'image') if command.poster_asset_id else None
    image = ready(db, command.image_asset_id, 'image') if command.image_asset_id else None

    if not video and not poster and not image:
        raise CatalogError('media_required', 'Hero slide requires at least a video, poster or image asset')
    if video and not poster and not video.poster_id:
        raise CatalogError('poster_required', 'Featured hero video requires a poster image')

    product = None
    if command.target_product_id:
        product = db.get(Product, command.target_product_id)
        if not product:
            raise CatalogError('product_not_found', 'Target product does not exist')

    collection = None
    if command.target_collection_id:
        collection = db.get(Collection, command.target_collection_id)
        if not collection:
            raise CatalogError('collection_not_found', 'Target collection does not exist')

    current_max = db.scalar(select(func.coalesce(func.max(HeroSlide.display_order), -1)))
    order = command.display_order if command.display_order is not None else current_max + 1

    slide = HeroSlide(
        id=uuid.uuid4().hex,
        title=command.title,
        benefit=command.benefit,
        video_asset_id=video.id if video else None,
        poster_asset_id=poster.id if poster else None,
        image_asset_id=image.id if image else None,
        display_order=order,
        is_enabled=command.is_enabled,
        target_product_id=product.id if product else None,
        target_collection_id=collection.id if collection else None,
        edit_version=1,
    )
    db.add(slide)
    db.flush()
    return slide


def update_hero_slide(db, identifier, command):
    reference_lock(db)
    slide = locked(db, HeroSlide, identifier, command.expected_version)

    if 'video_asset_id' in command.model_fields_set:
        video = ready(db, command.video_asset_id, 'video') if command.video_asset_id else None
        slide.video_asset_id = video.id if video else None
    if 'poster_asset_id' in command.model_fields_set:
        poster = ready(db, command.poster_asset_id, 'image') if command.poster_asset_id else None
        slide.poster_asset_id = poster.id if poster else None
    if 'image_asset_id' in command.model_fields_set:
        image = ready(db, command.image_asset_id, 'image') if command.image_asset_id else None
        slide.image_asset_id = image.id if image else None

    if not slide.video_asset_id and not slide.poster_asset_id and not slide.image_asset_id:
        raise CatalogError('media_required', 'Hero slide requires at least a video, poster or image asset')

    if 'title' in command.model_fields_set: slide.title = command.title
    if 'benefit' in command.model_fields_set: slide.benefit = command.benefit
    if 'display_order' in command.model_fields_set and command.display_order is not None:
        slide.display_order = command.display_order
    if 'is_enabled' in command.model_fields_set and command.is_enabled is not None:
        slide.is_enabled = command.is_enabled
    if 'target_product_id' in command.model_fields_set:
        slide.target_product_id = command.target_product_id
    if 'target_collection_id' in command.model_fields_set:
        slide.target_collection_id = command.target_collection_id

    slide.edit_version += 1
    db.flush()
    return slide


def reorder_hero_slides(db, command):
    reference_lock(db)
    slides = list(db.scalars(select(HeroSlide).where(HeroSlide.id.in_(command.slide_ids)).with_for_update()))
    slides_by_id = {s.id: s for s in slides}
    for index, s_id in enumerate(command.slide_ids):
        if s_id in slides_by_id:
            slides_by_id[s_id].display_order = index
            slides_by_id[s_id].edit_version += 1
    db.flush()
    return list_hero_slides(db)


def delete_hero_slide(db, identifier, command):
    reference_lock(db)
    slide = locked(db, HeroSlide, identifier, command.expected_version)
    db.delete(slide)
    db.flush()
    return {'id': identifier, 'deleted': True}


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
