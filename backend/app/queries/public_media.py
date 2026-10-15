"""Allowlisted storefront assets, stable ordering and inactive variant filtering."""
from app.schemas.catalog import PublicMediaSchema


def product_media(product):
    active_ids = {v.id for v in product.variants if v.is_active}
    result = []
    for link in sorted(getattr(product, 'media_links', []), key=lambda row: (row.display_order, row.id)):
        asset = link.asset
        if asset.state != 'ready' or (link.variant_id is not None and link.variant_id not in active_ids):
            continue
        if asset.kind == 'image' and asset.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            continue
        if asset.kind == 'video' and asset.content_type not in {'video/mp4', 'video/webm'}:
            continue
        poster = asset.poster
        poster_url = f'/api/v1/media/{poster.id}/content' if poster and poster.state == 'ready' and poster.kind == 'image' else None
        if asset.kind == 'video' and not poster_url:
            continue
        result.append(PublicMediaSchema(id=asset.id, role=link.role, variant_id=link.variant_id,
            display_order=link.display_order, alt_text=link.alt_text or product.title or '', kind=asset.kind,
            content_type=asset.content_type, url=f'/api/v1/media/{asset.id}/content', width=asset.width,
            height=asset.height, duration_ms=asset.duration_ms, poster_url=poster_url))
    return result


def primary_alt(product):
    return next((m.alt_text for m in product_media(product) if m.role == 'primary'), product.title or '')


def storefront_urls(product):
    roles = {m.role:m.url for m in product_media(product) if m.role != 'gallery'}
    fields = {'image_url':'primary', 'hero_image_url':'hero_image',
              'hero_poster_url':'hero_poster', 'hero_video_url':'hero_video'}
    return {field:roles.get(role) or (getattr(product, field, None) if getattr(product, 'legacy_media', True) is not False else None)
            for field, role in fields.items()}
