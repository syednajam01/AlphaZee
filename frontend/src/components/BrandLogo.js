/**
 * AlphaZee BrandLogo Component
 * 
 * Supports:
 * - Variants: 'combined', 'wordmark', 'symbol', 'responsive-header'
 * - Surfaces: 'light', 'dark', 'auto'
 * - Accessible link with name 'AlphaZee home'
 * - Dimension and aspect ratio preservation
 */

export const LOGO_ASSETS = {
  symbol: '/logo/Modern black AZ monogram-1.png',
  wordmark: '/logo/Bold AlphaZee geometric wordmark-2.png',
  combined: '/logo/AlphaZee monogram and wordmark-3.png',
};

export function createBrandLogo({
  variant = 'combined',
  surface = 'auto',
  width = null,
  asLink = true,
  href = '#',
  className = '',
  ariaLabel = 'AlphaZee home',
} = {}) {
  const container = document.createElement(asLink ? 'a' : 'div');
  container.className = `brand-logo-link ${className}`.trim();
  
  if (asLink) {
    container.href = href;
    container.setAttribute('aria-label', ariaLabel);
  }

  // Surface class
  if (surface === 'light') {
    container.classList.add('logo-surface-light');
  } else if (surface === 'dark') {
    container.classList.add('logo-surface-dark');
  }

  if (variant === 'responsive-header') {
    container.classList.add('storefront-header-logo');

    // Wordmark for mobile (110–135px)
    const imgWordmark = document.createElement('img');
    imgWordmark.src = LOGO_ASSETS.wordmark;
    imgWordmark.alt = '';
    imgWordmark.setAttribute('aria-hidden', 'true');
    imgWordmark.className = 'brand-logo-img logo-variant-wordmark';
    imgWordmark.width = 125;
    imgWordmark.height = 42;

    // Combined for desktop (150–180px)
    const imgCombined = document.createElement('img');
    imgCombined.src = LOGO_ASSETS.combined;
    imgCombined.alt = '';
    imgCombined.setAttribute('aria-hidden', 'true');
    imgCombined.className = 'brand-logo-img logo-variant-combined';
    imgCombined.width = 165;
    imgCombined.height = 55;

    container.appendChild(imgWordmark);
    container.appendChild(imgCombined);
  } else if (variant === 'symbol') {
    const symbolWrapper = document.createElement('div');
    symbolWrapper.className = 'logo-symbol-wrapper';
    
    const targetWidth = typeof width === 'number' ? `${width}px` : (width || '44px');
    symbolWrapper.style.width = targetWidth;

    const img = document.createElement('img');
    img.src = LOGO_ASSETS.symbol;
    img.alt = '';
    img.setAttribute('aria-hidden', 'true');
    img.className = 'brand-logo-img';
    img.style.width = '100%';

    symbolWrapper.appendChild(img);
    container.appendChild(symbolWrapper);
  } else {
    // Single image variant: 'wordmark' or 'combined'
    const img = document.createElement('img');
    const assetSrc = variant === 'wordmark' ? LOGO_ASSETS.wordmark : LOGO_ASSETS.combined;
    img.src = assetSrc;
    img.alt = '';
    img.setAttribute('aria-hidden', 'true');
    img.className = 'brand-logo-img';

    if (width) {
      img.style.width = typeof width === 'number' ? `${width}px` : width;
    } else {
      // Default recommended widths
      img.style.width = variant === 'wordmark' ? '125px' : '175px';
    }

    container.appendChild(img);
  }

  return container;
}
