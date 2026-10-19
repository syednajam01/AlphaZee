import { sanitizeMediaUrl } from './dom.js';

export function mediaForVariant(product, variantId) {
  const seenAssets = new Set();
  const media = (product.media || []).filter(m => {
    if (!['primary', 'gallery', 'hover_image'].includes(m.role)) return false;
    if (m.variant_id !== null && m.variant_id !== undefined && m.variant_id !== variantId) return false;
    if (!sanitizeMediaUrl(m.url, '') || !['image', 'video'].includes(m.kind)) return false;
    const key = m.asset_id || m.id || m.url;
    if (seenAssets.has(key)) return false;
    seenAssets.add(key);
    return true;
  });
  return media.length ? media : [{kind:'image', url:product.image_url, alt_text:product.title, role:'primary'}];
}

export function variantImage(product, variantId) {
  const media = mediaForVariant(product, variantId);
  return media.find(m => m.kind === 'image' && m.variant_id === variantId)?.url
    || media.find(m => m.role === 'primary' && m.kind === 'image')?.url || product.image_url;
}
