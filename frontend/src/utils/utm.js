/**
 * utm.js — Utility to extract, cache, and provide marketing attribution parameters (UTM).
 */

const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'];
const STORAGE_KEY = 'alphazee_utm_params';

/**
 * Capture UTM parameters from the current URL and store in sessionStorage.
 */
export function captureLandingUtmParams() {
  if (typeof window === 'undefined') return;

  try {
    const params = new URLSearchParams(window.location.search);
    const captured = {};
    let hasUtm = false;

    for (const key of UTM_KEYS) {
      const val = params.get(key);
      if (val) {
        captured[key] = val.trim();
        hasUtm = true;
      }
    }

    if (hasUtm) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(captured));
    }
  } catch (err) {
    console.warn('Unable to capture or store UTM parameters:', err);
  }
}

/**
 * Retrieve cached UTM parameters for order payload.
 * @returns {{ utm_source: string|null, utm_medium: string|null, utm_campaign: string|null }}
 */
export function getStoredUtmParams() {
  if (typeof window === 'undefined') {
    return { utm_source: null, utm_medium: null, utm_campaign: null };
  }

  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { utm_source: null, utm_medium: null, utm_campaign: null };
    }
    const parsed = JSON.parse(raw);
    return {
      utm_source: parsed.utm_source || null,
      utm_medium: parsed.utm_medium || null,
      utm_campaign: parsed.utm_campaign || null,
    };
  } catch {
    return { utm_source: null, utm_medium: null, utm_campaign: null };
  }
}
