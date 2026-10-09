/**
 * Safe DOM and URL validation helpers.
 */

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
 * Allows http, https, and root-relative URLs. Rejects javascript: or arbitrary protocols.
 * @param {string|null|undefined} url
 * @returns {boolean}
 */
export function isValidMediaUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
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
 * @param {string} fallback
 * @returns {string}
 */
export function sanitizeMediaUrl(url, fallback = '') {
  return isValidMediaUrl(url) ? url.trim() : fallback;
}
