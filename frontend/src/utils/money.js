/**
 * Money formatting utility for AlphaZee.
 *
 * Monetary values are stored as integer minor units (paisas):
 * 1 PKR = 100 paisas.
 * Example: PKR 3,450 is stored as 345000 paisas.
 */

/**
 * Format paisas (integer minor units) into a display string: "PKR 3,450"
 * @param {number|null|undefined} minorUnits - Amount in paisas
 * @returns {string} Formatted price
 */
export function formatPkr(minorUnits) {
  if (minorUnits === null || minorUnits === undefined || isNaN(minorUnits)) {
    return 'PKR 0';
  }
  const hasFractions = minorUnits % 100 !== 0;
  const rupees = minorUnits / 100;
  return `PKR ${rupees.toLocaleString('en-PK', {
    minimumFractionDigits: hasFractions ? 2 : 0,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Convert whole PKR to minor units (paisas).
 * @param {number} rupees 
 * @returns {number}
 */
export function pkrToMinor(rupees) {
  if (typeof rupees !== 'number' || isNaN(rupees)) return 0;
  return Math.round(rupees * 100);
}

/**
 * Safely extract integer minor units from an API price contract, object, or number.
 * Supports:
 * - CurrencyAmount object: { minor, pkr, formatted, currency }
 * - Object with price_minor or min_price_minor
 * - Plain non-negative integer
 * Returns integer minor units if valid, or null if missing or invalid.
 * @param {any} priceData
 * @returns {number|null}
 */
export function extractPriceMinor(priceData) {
  if (priceData === null || priceData === undefined) return null;
  if (typeof priceData === 'number') {
    return Number.isSafeInteger(priceData) && priceData >= 0 ? priceData : null;
  }
  if (typeof priceData === 'object') {
    if (typeof priceData.minor === 'number' && Number.isSafeInteger(priceData.minor) && priceData.minor >= 0) {
      return priceData.minor;
    }
    if (typeof priceData.price_minor === 'number' && Number.isSafeInteger(priceData.price_minor) && priceData.price_minor >= 0) {
      return priceData.price_minor;
    }
    if (typeof priceData.min_price_minor === 'number' && Number.isSafeInteger(priceData.min_price_minor) && priceData.min_price_minor >= 0) {
      return priceData.min_price_minor;
    }
  }
  return null;
}

/**
 * Format a product or variant price for display.
 * Reads the CurrencyAmount object's formatted string if present, or formats minor units.
 * Returns 'Price unavailable' if the price is missing or invalid.
 * @param {any} priceData
 * @param {string} [fallback='Price unavailable']
 * @returns {string}
 */
export function formatDisplayPrice(priceData, fallback = 'Price unavailable') {
  if (priceData && typeof priceData.formatted === 'string' && priceData.formatted.trim()) {
    return priceData.formatted;
  }
  const minor = extractPriceMinor(priceData);
  if (minor === null) return fallback;
  return formatPkr(minor);
}
