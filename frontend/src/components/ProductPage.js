import { fetchProductBySlug, fetchProducts } from '../utils/api.js';
import { cart } from '../utils/cart.js';
import { extractPriceMinor, formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';
import { mountProductGallery } from './ProductGallery.js';
import { variantImage } from '../utils/productMedia.js';
import { storeConfig } from '../data/store-config.js';

export function createProductPage({ onAddedToCart, onNavigate }) {
  const container = document.createElement('div');
  container.className = 'product-page-container container';

  let currentProduct = null;
  let relatedProducts = [];
  let selectedSize = null;
  let selectedColor = null;
  let quantity = 1;
  let isLoading = false;
  let errorMessage = null;
  let gallery = null;
  let ctaObserver = null;
  let mobileBar = null;
  let loadGeneration = 0;

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
      document.querySelector('meta[name="description"]')?.setAttribute('content', 'This product is currently unavailable. Browse the AlphaZee catalog.');
      document.querySelector('link[rel="canonical"]')?.remove();
    }
  }

  function getSelectedVariant() {
    if (!currentProduct?.variants || currentProduct.variants.length === 0) return null;
    if (currentProduct.variants.some(v => v.size) && !selectedSize) return null;
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

    const candidates = variants.filter(v => !selectedColor || v.color === selectedColor);
    const availableCandidates = candidates.filter(v => v.availability === 'available');
    const candidatePrices = availableCandidates.map(v => extractPriceMinor(v.price_minor ?? v.price)).filter(p => p !== null);
    const needsSize = sizes.length > 0 && !selectedSize;
    const priceMinor = activeVariant
      ? extractPriceMinor(activeVariant.price_minor ?? activeVariant.price)
      : needsSize && candidatePrices.length ? Math.min(...candidatePrices) : null;
    const displayPrice = formatDisplayPrice(priceMinor);
    const isAvailable = activeVariant ? activeVariant.availability === 'available' : needsSize && availableCandidates.length > 0;

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
                  <span class="option-group-value" id="selected-size-name">${escapeHtml(selectedSize || (sizes.length > 1 ? 'Select a size' : (sizes[0] || '')))}</span>
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
                <div id="size-selection-prompt" class="form-error" role="alert" hidden style="margin-top: 8px; font-size: 0.8125rem;">
                  Please select a size before adding to bag.
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
              <div class="product-info-content">
                <p style="margin: 0 0 6px 0;">
                  <strong>Material:</strong> ${product.material ? escapeHtml(product.material) : '<span style="color: var(--color-text-muted);">Material composition not verified yet.</span>'}
                </p>
                <p style="margin: 0;">
                  <strong>Care:</strong> ${product.care ? escapeHtml(product.care) : '<span style="color: var(--color-text-muted);">Care instructions not verified yet.</span>'}
                </p>
              </div>
            </div>

            <div class="product-info-block">
              <h3 class="product-info-title">Sizing & Fit</h3>
              <div class="product-info-content">
                <p style="margin: 0 0 8px 0;">
                  ${product.sizing ? escapeHtml(product.sizing) : '<span style="color: var(--color-text-muted);">Garment measurements not verified yet. Product-specific sizing table will be published once verified.</span>'}
                </p>
                ${Array.isArray(product.measurements) && product.measurements.length > 0 ? `
                  <table class="size-guide-table">
                    <thead>
                      <tr><th>Size</th><th>Chest (in)</th><th>Length (in)</th><th>Shoulder (in)</th></tr>
                    </thead>
                    <tbody>
                      ${product.measurements.map(m => `
                        <tr>
                          <td>${escapeHtml(m.size || '')}</td>
                          <td>${escapeHtml(m.chest || '—')}</td>
                          <td>${escapeHtml(m.length || '—')}</td>
                          <td>${escapeHtml(m.shoulder || '—')}</td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                ` : ''}
              </div>
            </div>

            <div class="product-info-block">
              <h3 class="product-info-title">Delivery & Returns</h3>
              <div class="product-info-content">
                <p style="margin: 0 0 6px 0;">
                  <strong>Dispatch:</strong> ${escapeHtml(storeConfig.shippingInfo.dispatchTime)}.
                </p>
                <p style="margin: 0 0 6px 0;">
                  <strong>Transit:</strong> ${escapeHtml(storeConfig.shippingInfo.standardTime)} (${escapeHtml(storeConfig.shippingInfo.standardRate)}).
                </p>
                <p style="margin: 0;">
                  <strong>Policy:</strong> ${escapeHtml(storeConfig.shippingInfo.returnPolicy)}.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Related Pieces Section -->
      ${relatedProducts && relatedProducts.length > 0 ? `
        <section class="product-related-section">
          <div class="product-related-header">
            <div class="product-related-eyebrow">Curated Pieces</div>
            <h2 class="product-related-title">Complete the Silhouette</h2>
          </div>
          <div class="product-related-grid">
            ${relatedProducts.map(p => {
              const pPrice = extractPriceMinor(p.min_price_minor ?? p.min_price);
              const pDisplayPrice = formatDisplayPrice(pPrice);
              const pImg = sanitizeMediaUrl(p.image_url, '');
              const pHoverImg = sanitizeMediaUrl(p.hover_image_url || p.secondary_image_url, '');
              return `
                <a href="/products/${encodeURIComponent(p.slug)}" data-nav="/products/${encodeURIComponent(p.slug)}" class="product-related-card">
                  <div class="product-related-media ${pHoverImg ? 'has-hover' : ''}">
                    ${pImg ? `<img src="${pImg}" alt="${escapeHtml(p.title)}" class="product-related-img product-related-img-primary ${pHoverImg ? 'has-hover' : ''}" loading="lazy" />` : '<div class="product-gallery-neutral-fallback"><span>AZ</span></div>'}
                    ${pHoverImg ? `<img src="${pHoverImg}" alt="${escapeHtml(p.title)} alternate view" class="product-related-img product-related-img-hover" loading="lazy" />` : ''}
                  </div>
                  <div class="product-related-meta">
                    <h3 class="product-related-card-title">${escapeHtml(p.title)}</h3>
                    <span class="product-related-price price-tabular">${pDisplayPrice}</span>
                  </div>
                </a>
              `;
            }).join('')}
          </div>
        </section>
      ` : ''}

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

    // Attach breadcrumb and related links
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
        const prompt = container.querySelector('#size-selection-prompt');
        if (prompt) {
          prompt.hidden = true;
          if (prompt.style && typeof prompt.style === 'object') prompt.style.display = 'none';
        }
        onVariantOptionsChanged();
      });
    });
  }

  function onVariantOptionsChanged() {
    const active = getSelectedVariant();
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (active) url.searchParams.set('variant', String(active.id));
      else url.searchParams.delete('variant');
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
    const product = currentProduct;
    if (!product) return;
    const variants = product.variants || [];
    const sizes = variants.some(v => v.size) ? [...new Set(variants.map(v => v.size || '').filter(Boolean))] : [];

    if (sizes.length > 1 && !selectedSize) {
      const prompt = container.querySelector('#size-selection-prompt');
      if (prompt) {
        prompt.hidden = false;
        if (prompt.style && typeof prompt.style === 'object') prompt.style.display = 'block';
      }
      const sizeGroup = container.querySelector('[data-option="size"]');
      sizeGroup?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' });
      return;
    }

    const active = getSelectedVariant();
    if (!active || active.availability !== 'available') return;
    const priceMinor = extractPriceMinor(active.price_minor ?? active.price);
    if (priceMinor === null) return;

    const img = variantImage(currentProduct, active.id);
    const resolvedImageUrl = typeof img === 'string' ? img : (img?.url || currentProduct.image_url || '');

    cart.addItem({
      product_id: currentProduct.id,
      variant_id: active.id,
      title: currentProduct.title,
      slug: currentProduct.slug,
      sku: active.sku,
      price_minor: priceMinor,
      size: active.size,
      color: active.color,
      image_url: resolvedImageUrl,
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

  // Bind once: rendering options must not accumulate container listeners.
  container.addEventListener('focusin', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target?.tagName)) mobileBar?.classList.add('is-suppressed');
  });
  container.addEventListener('focusout', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target?.tagName)) mobileBar?.classList.remove('is-suppressed');
  });

  async function load(slug, variantIdQuery = null) {
    const currentGen = ++loadGeneration;
    isLoading = true;
    errorMessage = null;
    currentProduct = null;
    relatedProducts = [];
    quantity = 1;
    render();

    try {
      const prod = await fetchProductBySlug(slug);
      if (currentGen !== loadGeneration) return;
      currentProduct = prod;

      // Select initial variant
      const variants = prod.variants || [];
      const sizes = variants.some(v => v.size) ? [...new Set(variants.map(v => v.size || '').filter(Boolean))] : [];
      const colors = variants.some(v => v.color) ? [...new Set(variants.map(v => v.color || '').filter(Boolean))] : [];

      let initialVariant = null;
      if (variantIdQuery) {
        initialVariant = variants.find(v => String(v.id) === String(variantIdQuery));
      }

      if (initialVariant) {
        selectedSize = initialVariant.size || null;
        selectedColor = initialVariant.color || null;
      } else {
        selectedColor = colors[0] || null;
        // Require deliberate size choice if multiple sizes exist
        selectedSize = sizes.length === 1 ? sizes[0] : null;
      }

      // Fetch related products in background
      fetchProducts({ collectionId: prod.collection_id || null, pageSize: 5 })
        .then(res => {
          if (currentGen !== loadGeneration) return;
          const raw = res?.products || [];
          relatedProducts = raw.filter(p => p.id !== prod.id && p.slug !== prod.slug).slice(0, 4);
          render();
        })
        .catch(() => {
          // Non-blocking: related products failure does not block primary product view
        });

      isLoading = false;
      updateMetadata(prod);
      render();
    } catch (err) {
      if (currentGen !== loadGeneration) return;
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
      loadGeneration++;
      gallery?.destroy();
      gallery = null;
      if (ctaObserver) {
        ctaObserver.disconnect();
        ctaObserver = null;
      }
      container.innerHTML = '';
      currentProduct = null;
      mobileBar = null;
    }
  };
}
