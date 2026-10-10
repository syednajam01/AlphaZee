/**
 * Safe DOM and URL validation helpers.
 */

/**
 * Neutral SVG placeholder used when product or collection media is not yet available.
 * Avoids third-party model photo fallbacks and provides honest visual indication.
 */
export const PLACEHOLDER_IMAGE_URL =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">' +
    '<rect width="400" height="400" fill="#131B16"/>' +
    '<circle cx="200" cy="180" r="56" fill="#1E2A23" stroke="#2D3F35" stroke-width="2"/>' +
    '<text x="200" y="190" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="28" fill="#52B788" letter-spacing="2">AZ</text>' +
    '<text x="200" y="270" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="600" font-size="12" fill="#88988E" letter-spacing="3">IMAGE COMING SOON</text>' +
    '</svg>'
  );

/**
 * Escape HTML special characters to prevent XSS when rendering dynamic text.
 * @param {string|null|undefined} str
 * @returns {string}
 */
export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Validate that a media URL is safe to use in src attributes.
 * Allows http, https, root-relative URLs, and the internal PLACEHOLDER_IMAGE_URL.
 * Rejects javascript:, quotes, angle brackets, control characters, and whitespace.
 * @param {string|null|undefined} url
 * @returns {boolean}
 */
export function isValidMediaUrl(url) {
  if (!url || typeof url !== 'string') return false;
  if (url === PLACEHOLDER_IMAGE_URL) return true;
  // Reject strings containing characters that allow HTML attribute injection or breakout
  if (/["'`<>\r\n\t\\]/.test(url)) return false;
  const trimmed = url.trim();
  if (!trimmed || /\s/.test(trimmed)) return false;
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) return true;
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Sanitize a media URL, returning a fallback if invalid.
 * @param {string|null|undefined} url
 * @param {string} [fallback=PLACEHOLDER_IMAGE_URL]
 * @returns {string}
 */
export function sanitizeMediaUrl(url, fallback = PLACEHOLDER_IMAGE_URL) {
  return isValidMediaUrl(url) ? url.trim() : fallback;
}

/**
 * Create an HTML <img> element safely by setting src, alt, and attributes via DOM properties.
 * Prevents HTML string concatenation and attribute breakout vulnerabilities.
 * @param {Object} options
 * @param {string|null|undefined} options.src
 * @param {string} [options.alt='']
 * @param {string} [options.className='']
 * @param {number|string} [options.width]
 * @param {number|string} [options.height]
 * @param {string} [options.loading='lazy']
 * @param {string} [options.fallback=PLACEHOLDER_IMAGE_URL]
 * @returns {HTMLImageElement}
 */
export function createSafeImageElement({
  src,
  alt = '',
  className = '',
  width,
  height,
  loading = 'lazy',
  fallback = PLACEHOLDER_IMAGE_URL,
} = {}) {
  const img = document.createElement('img');
  const safeSrc = sanitizeMediaUrl(src, fallback);
  if (safeSrc) {
    img.src = safeSrc;
  }
  img.alt = alt || '';
  if (className) {
    img.className = className;
  }
  if (loading) {
    img.loading = loading;
  }
  if (width !== undefined) {
    img.width = width;
  }
  if (height !== undefined) {
    img.height = height;
  }
  return img;
}
