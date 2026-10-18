import { fetchProductBySlug } from '../utils/api.js';
import { cart } from '../utils/cart.js';
import { extractPriceMinor, formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';
import { mountProductGallery } from './ProductGallery.js';
import { variantImage } from '../utils/productMedia.js';

export function createProductPage({ onAddedToCart, onNavigate }) {
  const container = document.createElement('div');
  container.className = 'product-page-container container';

  let currentProduct = null;
  let selectedSize = null;
  let selectedColor = null;
  let quantity = 1;
  let isLoading = false;
  let errorMessage = null;
  let gallery = null;
  let ctaObserver = null;
  let mobileBar = null;

  function updateMetadata(product) {
    if (typeof document === 'undefined') return;
    if (product) {
      document.title = `${product.title} — AlphaZee`;
      let descMeta = document.querySelector('meta[name="description"]');
      if (descMeta) {
        descMeta.setAttribute('content', product.description?.slice(0, 160) || `${product.title} by AlphaZee`);
      }
      let canonical = document.querySelector('link[rel="canonical"]');
      if (!canonical) {
        canonical = document.createElement('link');
        canonical.setAttribute('rel', 'canonical');
        document.head.appendChild(canonical);
      }
      if (typeof window !== 'undefined') {
        canonical.setAttribute('href', `${window.location.origin}/products/${encodeURIComponent(product.slug)}`);
      }
    } else {
      document.title = 'Piece Unavailable — AlphaZee';
    }
  }

  function getSelectedVariant() {
    if (!currentProduct?.variants || currentProduct.variants.length === 0) return null;
    return currentProduct.variants.find(v => {
      const sizeMatch = !selectedSize || v.size === selectedSize;
      const colorMatch = !selectedColor || v.color === selectedColor;
      return sizeMatch && colorMatch;
    }) || null;
  }

  function render() {
    gallery?.destroy();
    gallery = null;
    if (ctaObserver) {
      ctaObserver.disconnect();
      ctaObserver = null;
    }

    if (isLoading) {
      container.innerHTML = `
        <div class="product-breadcrumb">
          <a href="/" data-nav="/">Home</a>
          <span class="product-breadcrumb-sep">/</span>
          <span>Loading...</span>
        </div>
        <div class="product-page-grid" style="opacity: 0.6;">
          <div class="product-page-gallery">
            <div class="product-gallery-stage catalog-skeleton-card" style="aspect-ratio: 3/4;">
              <div class="catalog-skeleton-img" style="width: 100%; height: 100%;"></div>
            </div>
          </div>
          <div class="product-page-details">
            <div class="catalog-skeleton-text" style="width: 30%; height: 20px; margin-bottom: 12px;"></div>
            <div class="catalog-skeleton-text" style="width: 80%; height: 36px; margin-bottom: 16px;"></div>
            <div class="catalog-skeleton-text" style="width: 40%; height: 24px; margin-bottom: 24px;"></div>
            <div class="catalog-skeleton-text" style="width: 100%; height: 48px;"></div>
          </div>
        </div>
      `;
      return;
    }

    if (errorMessage || !currentProduct) {
      container.innerHTML = `
        <div class="product-breadcrumb">
          <a href="/" data-nav="/">Home</a>
          <span class="product-breadcrumb-sep">/</span>
          <span class="product-breadcrumb-current">Product Unavailable</span>
        </div>
        <div class="product-unavailable-view">
          <svg class="product-unavailable-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <h1 class="product-unavailable-title">Piece Unavailable</h1>
          <p class="product-unavailable-desc">${escapeHtml(errorMessage || 'The piece you requested could not be found or is no longer active in our catalog.')}</p>
          <a href="/" data-nav="/" class="btn btn-primary" style="display: inline-flex;">
            Explore Available Collection
          </a>
        </div>
      `;
      attachNavLinks();
      return;
    }

    const product = currentProduct;
    const variants = product.variants || [];
    const sizes = variants.some(v => v.size) ? [...new Set(variants.map(v => v.size || '').filter(Boolean))] : [];
    const colors = variants.some(v => v.color) ? [...new Set(variants.map(v => v.color || '').filter(Boolean))] : [];
    const activeVariant = getSelectedVariant();

    const priceMinor = extractPriceMinor(activeVariant?.price_minor ?? activeVariant?.price ?? product.min_price ?? product.min_price_minor);
    const displayPrice = formatDisplayPrice(priceMinor);
    const isAvailable = activeVariant ? (activeVariant.availability === 'available') : (product.availability === 'available');

    const safeTitle = escapeHtml(product.title);
    const safeCollection = product.collection_name ? escapeHtml(product.collection_name) : null;

    container.innerHTML = `
      <nav class="product-breadcrumb" aria-label="Breadcrumb">
        <a href="/" data-nav="/">Home</a>
        <span class="product-breadcrumb-sep">/</span>
        ${safeCollection ? `
          <a href="/#featured" data-nav="/#featured">${safeCollection}</a>
          <span class="product-breadcrumb-sep">/</span>
        ` : ''}
        <span class="product-breadcrumb-current" aria-current="page">${safeTitle}</span>
      </nav>

      <div class="product-page-grid">
        <!-- 58% Gallery Stage -->
        <div class="product-page-gallery" id="product-gallery-host">
          <!-- Mount Product Gallery -->
        </div>

        <!-- 42% Purchase Details -->
        <div class="product-page-details is-sticky">
          ${safeCollection ? `<div class="product-collection-eyebrow">${safeCollection}</div>` : ''}
          <h1 class="product-page-title">${safeTitle}</h1>

          <div class="product-price-row">
            <span class="product-page-price price-tabular" id="product-detail-price">${displayPrice}</span>
            <span class="badge ${isAvailable ? 'badge-stock' : 'badge-out-of-stock'}" id="product-detail-stock">
              ${isAvailable ? 'In Stock' : 'Currently Unavailable'}
            </span>
          </div>

          <!-- Options -->
          <div class="product-options-container">
            ${colors.length > 0 ? `
              <div class="option-group" data-option="color">
                <div class="option-group-header">
                  <span class="option-group-title">Color</span>
                  <span class="option-group-value" id="selected-color-name">${escapeHtml(selectedColor || '')}</span>
                </div>
                <div class="option-chips" role="radiogroup" aria-label="Select color">
                  ${colors.map(col => `
                    <button type="button" 
                      class="option-chip ${selectedColor === col ? 'is-selected' : ''}" 
                      data-option-color="${escapeHtml(col)}"
                      role="radio"
                      aria-checked="${selectedColor === col}"
                      aria-label="Color ${escapeHtml(col)}">
                      ${escapeHtml(col)}
                    </button>
                  `).join('')}
                </div>
              </div>
            ` : ''}

            ${sizes.length > 0 ? `
              <div class="option-group" data-option="size">
                <div class="option-group-header">
                  <span class="option-group-title">Size</span>
                  <span class="option-group-value" id="selected-size-name">${escapeHtml(selectedSize || '')}</span>
                </div>
                <div class="option-chips" role="radiogroup" aria-label="Select size">
                  ${sizes.map(sz => {
                    const variantForSize = variants.find(v => v.size === sz && (!selectedColor || v.color === selectedColor));
                    const szAvailable = variantForSize ? variantForSize.availability === 'available' : false;
                    return `
                      <button type="button" 
                        class="option-chip ${selectedSize === sz ? 'is-selected' : ''} ${!szAvailable ? 'is-unavailable' : ''}" 
                        data-option-size="${escapeHtml(sz)}"
                        role="radio"
                        aria-checked="${selectedSize === sz}"
                        aria-label="Size ${escapeHtml(sz)}">
                        ${escapeHtml(sz)}
                      </button>
                    `;
                  }).join('')}
                </div>
              </div>
            ` : ''}
          </div>

          <!-- Quantity Stepper -->
          <div class="product-qty-row">
            <span class="form-label" style="margin: 0;">Quantity</span>
            <div class="qty-stepper">
              <button type="button" class="qty-btn" id="btn-qty-minus" aria-label="Decrease quantity" ${quantity <= 1 ? 'disabled' : ''}>-</button>
              <input type="text" class="qty-value" id="qty-input" value="${quantity}" readonly aria-label="Quantity" />
              <button type="button" class="qty-btn" id="btn-qty-plus" aria-label="Increase quantity" ${quantity >= 99 ? 'disabled' : ''}>+</button>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="product-actions">
            <button 
              type="button" 
              class="btn btn-primary btn-add-to-cart" 
              id="btn-add-to-cart"
              ${!isAvailable || priceMinor === null ? 'disabled' : ''}>
              ${isAvailable ? 'Add to Shopping Bag' : 'Out of Stock'}
            </button>
          </div>

          <!-- Editorial Accordions: Description, Material & Care, Sizing, Delivery -->
          <div class="product-info-sections">
            ${product.description ? `
              <div class="product-info-block">
                <h3 class="product-info-title">Description & Details</h3>
                <div class="product-info-content">${escapeHtml(product.description)}</div>
              </div>
            ` : ''}

            <div class="product-info-block">
              <h3 class="product-info-title">Material & Garment Care</h3>
              <div class="product-info-content">${escapeHtml(product.material || product.material_care || 'Crafted from 100% heavyweight combed cotton (240 GSM). Preshrunk fabric. Machine wash cold with like colors. Line dry inside out to maintain shape and color richness.')}</div>
            </div>

            <div class="product-info-block">
              <h3 class="product-info-title">Sizing Guide</h3>
              <div class="product-info-content">
                ${escapeHtml(product.sizing_guide || 'Designed for a structured, contemporary silhouette with a relaxed shoulder drop. Order your standard size for the intended relaxed drape, or size down for a slimmer tailoring.')}
                <table class="size-guide-table">
                  <thead>
                    <tr><th>Size</th><th>Chest (in)</th><th>Length (in)</th><th>Shoulder (in)</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>S</td><td>38 - 40</td><td>27.5</td><td>18.5</td></tr>
                    <tr><td>M</td><td>40 - 42</td><td>28.5</td><td>19.5</td></tr>
                    <tr><td>L</td><td>42 - 44</td><td>29.5</td><td>20.5</td></tr>
                    <tr><td>XL</td><td>44 - 46</td><td>30.5</td><td>21.5</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="product-info-block">
              <h3 class="product-info-title">Nationwide Delivery & Returns</h3>
              <div class="product-info-content">
                Orders dispatch within 24 to 48 hours from our Karachi fulfillment hub. Standard nationwide transit is 3–5 business days. Cash on delivery (COD) and direct online bank transfer accepted. Every order includes private order tracking and our 7-day inspection and size-exchange policy.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Mobile Sticky Purchase Bar -->
      <div class="mobile-purchase-bar" id="mobile-purchase-bar" aria-hidden="true">
        <div class="mobile-bar-info">
          <span class="mobile-bar-title">${safeTitle} (${escapeHtml(selectedSize || 'Standard')})</span>
          <span class="mobile-bar-price price-tabular">${displayPrice}</span>
        </div>
        <button type="button" class="btn btn-primary mobile-bar-btn" id="btn-mobile-add-to-cart" ${!isAvailable || priceMinor === null ? 'disabled' : ''}>
          ${isAvailable ? 'Add to Bag' : 'Out of Stock'}
        </button>
      </div>
    `;

    // Mount media gallery
    const galleryHost = container.querySelector('#product-gallery-host');
    if (galleryHost) {
      gallery = mountProductGallery(galleryHost, product, activeVariant?.id);
    }

    // Attach option handlers
    attachOptionHandlers();

    // Attach quantity stepper
    attachQuantityHandlers();

    // Attach Add to Cart
    attachAddToCartHandlers();

    // Attach breadcrumb links
    attachNavLinks();

    // Setup Mobile Bar Intersection Observer
    setupMobileBarObserver();
  }

  function attachNavLinks() {
    container.querySelectorAll('a[data-nav]').forEach(link => {
      link.addEventListener('click', (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        const target = link.getAttribute('data-nav') || link.getAttribute('href');
        if (target && onNavigate) {
          e.preventDefault();
          onNavigate(target);
        }
      });
    });
  }

  function attachOptionHandlers() {
    container.querySelectorAll('[data-option-color]').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedColor = btn.dataset.optionColor;
        onVariantOptionsChanged();
      });
    });

    container.querySelectorAll('[data-option-size]').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedSize = btn.dataset.optionSize;
        onVariantOptionsChanged();
      });
    });
  }

  function onVariantOptionsChanged() {
    const active = getSelectedVariant();
    if (active && typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('variant', String(active.id));
      window.history.replaceState(null, '', url.pathname + url.search);
    }
    render();
  }

  function attachQuantityHandlers() {
    const minus = container.querySelector('#btn-qty-minus');
    const plus = container.querySelector('#btn-qty-plus');
    const input = container.querySelector('#qty-input');

    minus?.addEventListener('click', () => {
      if (quantity > 1) {
        quantity--;
        if (input) input.value = quantity;
        minus.disabled = quantity <= 1;
        if (plus) plus.disabled = false;
      }
    });

    plus?.addEventListener('click', () => {
      if (quantity < 99) {
        quantity++;
        if (input) input.value = quantity;
        plus.disabled = quantity >= 99;
        if (minus) minus.disabled = false;
      }
    });
  }

  function handleAddToCart() {
    const active = getSelectedVariant();
    if (!active || active.availability !== 'available') return;
    const priceMinor = extractPriceMinor(active.price_minor ?? active.price);
    if (priceMinor === null) return;

    const img = variantImage(currentProduct, active.id);

    cart.addItem({
      product_id: currentProduct.id,
      variant_id: active.id,
      title: currentProduct.title,
      slug: currentProduct.slug,
      sku: active.sku,
      price_minor: priceMinor,
      size: active.size,
      color: active.color,
      image_url: img ? img.url : (currentProduct.image_url || ''),
    }, {}, quantity);

    if (onAddedToCart) {
      onAddedToCart();
    }
  }

  function attachAddToCartHandlers() {
    container.querySelector('#btn-add-to-cart')?.addEventListener('click', handleAddToCart);
    container.querySelector('#btn-mobile-add-to-cart')?.addEventListener('click', handleAddToCart);
  }

  function setupMobileBarObserver() {
    const mainBtn = container.querySelector('#btn-add-to-cart');
    mobileBar = container.querySelector('#mobile-purchase-bar');
    if (!mainBtn || !mobileBar || typeof IntersectionObserver === 'undefined') return;

    ctaObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting && entry.boundingClientRect.top < 0) {
          mobileBar.classList.add('is-visible');
          mobileBar.setAttribute('aria-hidden', 'false');
        } else {
          mobileBar.classList.remove('is-visible');
          mobileBar.setAttribute('aria-hidden', 'true');
        }
      });
    }, { threshold: 0.1 });

    ctaObserver.observe(mainBtn);
  }

  async function load(slug, variantIdQuery = null) {
    isLoading = true;
    errorMessage = null;
    currentProduct = null;
    quantity = 1;
    render();

    try {
      const prod = await fetchProductBySlug(slug);
      currentProduct = prod;

      // Select initial variant
      const variants = prod.variants || [];
      let initialVariant = null;
      if (variantIdQuery) {
        initialVariant = variants.find(v => String(v.id) === String(variantIdQuery));
      }
      if (!initialVariant) {
        initialVariant = variants.find(v => v.availability === 'available') || variants[0];
      }

      if (initialVariant) {
        selectedSize = initialVariant.size || null;
        selectedColor = initialVariant.color || null;
      } else {
        selectedSize = null;
        selectedColor = null;
      }

      isLoading = false;
      updateMetadata(prod);
      render();
    } catch (err) {
      isLoading = false;
      errorMessage = err.message || 'Unable to load product information.';
      updateMetadata(null);
      render();
    }
  }

  return {
    element: container,
    load,
    destroy() {
      gallery?.destroy();
      if (ctaObserver) ctaObserver.disconnect();
    }
  };
}
