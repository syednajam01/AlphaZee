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
  const wholeRupees = Math.floor(minorUnits / 100);
  return `PKR ${wholeRupees.toLocaleString('en-PK')}`;
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
