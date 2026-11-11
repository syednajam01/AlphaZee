/**
 * SKU Auto-Generation Utility
 *
 * Generates an auto-suggested SKU based on:
 * - First letter of each word in product title (e.g. "syed najam ul huda" -> "snuh")
 * - First letter of color word(s) (e.g. "green" -> "g", "royal blue" -> "rb")
 * - Size token (e.g. "medium" -> "m", "small" -> "s", "large" -> "l", "extra large" -> "xl", "one size" -> "os", "32" -> "32")
 * Output format: lowercased, hyphen-separated string: "snuh-g-m"
 */

export function generateSku(productTitle, color, size) {
  // 1. Product title initials (first alphanumeric character of each word)
  const cleanTitle = String(productTitle || '').toLowerCase().replace(/[^a-z0-9\s\-_]/g, '');
  const titleWords = cleanTitle
    .trim()
    .split(/[\s\-_]+/)
    .filter(Boolean);
  const titleInitials = titleWords.map(w => w[0]).join('') || 'prod';

  // 2. Color initials (first alphanumeric character of each word)
  const cleanColor = String(color || '').toLowerCase().replace(/[^a-z0-9\s\-_]/g, '');
  const colorWords = cleanColor
    .trim()
    .split(/[\s\-_]+/)
    .filter(Boolean);
  const colorCode = colorWords.map(w => w[0]).join('') || 'c';

  // 3. Size code mapping
  const cleanSize = String(size || '').trim().toLowerCase();
  const sizeMap = {
    'extra small': 'xs',
    'extrasmall': 'xs',
    'small': 's',
    'medium': 'm',
    'large': 'l',
    'extra large': 'xl',
    'extralarge': 'xl',
    'one size': 'os',
    'onesize': 'os',
  };

  let sizeCode = sizeMap[cleanSize];
  if (!sizeCode) {
    const stripped = cleanSize.replace(/[^a-z0-9]/g, '');
    if (/^[a-z]+$/.test(stripped) && stripped.length > 2) {
      sizeCode = stripped[0];
    } else {
      sizeCode = stripped || 'sz';
    }
  }

  return `${titleInitials}-${colorCode}-${sizeCode}`;
}
