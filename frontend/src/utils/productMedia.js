import { sanitizeMediaUrl } from './dom.js';

export function mediaForVariant(product, variantId) {
  const media = (product.media || []).filter(m => ['primary','gallery'].includes(m.role)
    && (m.variant_id === null || m.variant_id === undefined || m.variant_id === variantId)
    && sanitizeMediaUrl(m.url, '') && ['image','video'].includes(m.kind));
  return media.length ? media : [{kind:'image', url:product.image_url, alt_text:product.title, role:'primary'}];
}

export function variantImage(product, variantId) {
  const media = mediaForVariant(product, variantId);
  return media.find(m => m.kind === 'image' && m.variant_id === variantId)?.url
    || media.find(m => m.role === 'primary' && m.kind === 'image')?.url || product.image_url;
}
