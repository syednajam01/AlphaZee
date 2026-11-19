"""Allowlisted storefront assets, stable ordering and inactive variant filtering."""
from app.schemas.catalog import PublicMediaSchema


def product_media(product):
    active_ids = {v.id for v in product.variants if v.is_active}
    result = []
    seen = set()
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
        dedup_key = (asset.id, link.role, link.variant_id)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        fx = link.focal_x if getattr(link, 'focal_x', None) is not None else getattr(asset, 'focal_x', 50)
        fy = link.focal_y if getattr(link, 'focal_y', None) is not None else getattr(asset, 'focal_y', 50)
        zm = link.zoom_scale if getattr(link, 'zoom_scale', None) is not None else getattr(asset, 'zoom_scale', 1.0)
        result.append(PublicMediaSchema(id=asset.id, role=link.role, variant_id=link.variant_id,
            display_order=link.display_order, alt_text=link.alt_text or product.title or '', kind=asset.kind,
            content_type=asset.content_type, url=f'/api/v1/media/{asset.id}/content', width=asset.width,
            height=asset.height, duration_ms=asset.duration_ms, poster_url=poster_url,
            focal_x=fx, focal_y=fy, zoom_scale=zm))
    return result


def primary_alt(product):
    return next((m.alt_text for m in product_media(product) if m.role == 'primary'), product.title or '')


def storefront_framing(product):
    links = {m.role: m for m in product_media(product)}
    primary = links.get('primary')
    hover = links.get('hover_image')
    return {
        'focal_x': primary.focal_x if primary else 50,
        'focal_y': primary.focal_y if primary else 50,
        'zoom_scale': primary.zoom_scale if primary else 1.0,
        'hover_focal_x': hover.focal_x if hover else 50,
        'hover_focal_y': hover.focal_y if hover else 50,
        'hover_zoom_scale': hover.zoom_scale if hover else 1.0,
    }


def storefront_urls(product):
    roles = {m.role:m.url for m in product_media(product) if m.role != 'gallery'}
    fields = {'image_url':'primary', 'hover_image_url':'hover_image', 'hero_image_url':'hero_image',
              'hero_poster_url':'hero_poster', 'hero_video_url':'hero_video'}
    return {field:roles.get(role) or (getattr(product, field, None) if getattr(product, 'legacy_media', True) is not False else None)
            for field, role in fields.items()}
