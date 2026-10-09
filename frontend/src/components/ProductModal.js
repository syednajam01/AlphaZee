import { cart } from '../utils/cart.js';
import { fetchProductBySlug } from '../utils/api.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

export function createProductModal(onAddedToCart) {
  const modalContainer = document.createElement('div');
  modalContainer.className = 'modal-container';
  modalContainer.id = 'product-modal';
  modalContainer.setAttribute('role', 'dialog');
  modalContainer.setAttribute('aria-modal', 'true');

  let currentProduct = null;
  let selectedSize = null;
  let selectedColor = null;
  let isLoading = false;
  let errorMessage = null;

  modalContainer.innerHTML = `
    <div class="drawer-backdrop is-open" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2;">
      <button class="modal-close-btn" id="modal-close-btn" aria-label="Close product details">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>

      <div class="product-modal-grid" id="modal-body-content">
        <!-- Rendered dynamically -->
      </div>
    </div>
  `;

  function render() {
    const body = modalContainer.querySelector('#modal-body-content');

    if (isLoading) {
      body.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 48px; text-align: center;">
          <p style="color: var(--color-text-muted); font-size: 1rem;">Loading piece details...</p>
        </div>
      `;
      return;
    }

    if (errorMessage) {
      body.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 32px; text-align: center;">
          <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 8px;">Product Unavailable</h3>
          <p style="color: var(--color-text-muted); font-size: 0.875rem; margin-bottom: 16px;">${escapeHtml(errorMessage)}</p>
          <button class="btn btn-secondary" id="btn-modal-err-close">Close</button>
        </div>
      `;
      body.querySelector('#btn-modal-err-close')?.addEventListener('click', close);
      return;
    }

    if (!currentProduct) return;

    const variants = currentProduct.variants || [];
    const sizes = [...new Set(variants.map(v => v.size).filter(Boolean))];
    const colors = [...new Set(variants.map(v => v.color).filter(Boolean))];

    if (sizes.length > 0 && !selectedSize) selectedSize = sizes[0];
    if (colors.length > 0 && !selectedColor) selectedColor = colors[0];

    // Find the active variant matching selectedSize and selectedColor
    const activeVariant = variants.find(v => {
      const sizeMatch = sizes.length === 0 ? true : v.size === selectedSize;
      const colorMatch = colors.length === 0 ? true : v.color === selectedColor;
      return sizeMatch && colorMatch;
    }) || variants[0];

    const isAvailable = activeVariant?.availability === 'available';
    const priceText = activeVariant ? formatPkr(activeVariant.price_minor) : 'Price unavailable';
    const statusText = isAvailable ? 'Available — Ready to ship' : 'Currently Unavailable';
    const safeTitle = escapeHtml(currentProduct.title);
    const safeDesc = escapeHtml(currentProduct.description || 'Architectural fit crafted with premium combed cotton.');
    const safeImage = sanitizeMediaUrl(currentProduct.image_url, 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80');

    body.innerHTML = `
      <div class="modal-img-wrapper">
        <img src="${safeImage}" alt="${safeTitle}" class="modal-img" />
      </div>

      <div class="modal-details">
        <span class="badge ${isAvailable ? 'badge-accent' : 'badge-neutral'}" style="align-self: flex-start; margin-bottom: 8px;">
          ${statusText}
        </span>
        <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 4px;">${safeTitle}</h2>
        <div style="font-size: 1.35rem; font-weight: 700; color: var(--color-accent); margin-bottom: 12px;">
          ${priceText}
        </div>
        <p style="font-size: 0.875rem; color: var(--color-text-muted); line-height: 1.5; margin-bottom: 16px;">
          ${safeDesc}
        </p>

        <!-- Color selector -->
        ${colors.length > 0 ? `
          <div class="option-group">
            <label class="option-label">Color: <strong>${escapeHtml(selectedColor)}</strong></label>
            <div class="option-pills" id="modal-colors-list">
              ${colors.map(col => `
                <button class="option-pill ${col === selectedColor ? 'is-selected' : ''}" data-color="${escapeHtml(col)}">
                  ${escapeHtml(col)}
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Size selector -->
        ${sizes.length > 0 ? `
          <div class="option-group">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <label class="option-label">Size: <strong>${escapeHtml(selectedSize)}</strong></label>
            </div>
            <div class="option-pills" id="modal-sizes-list">
              ${sizes.map(sz => `
                <button class="option-pill ${sz === selectedSize ? 'is-selected' : ''}" data-size="${escapeHtml(sz)}">
                  ${escapeHtml(sz)}
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--color-border);">
          <button 
            class="btn ${isAvailable ? 'btn-primary' : 'btn-secondary'}" 
            id="btn-modal-add-to-cart" 
            style="width: 100%; min-height: 48px;"
            ${!isAvailable ? 'disabled' : ''}>
            ${isAvailable ? `Add to Cart • ${priceText}` : 'Out of Stock'}
          </button>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: 0.75rem; color: var(--color-text-muted);">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="3" width="15" height="13"></rect>
              <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
            </svg>
            <span>Delivery: 2–4 business days across Pakistan (COD & Bank Transfer)</span>
          </div>
        </div>
      </div>
    `;

    // Colors click handling
    body.querySelectorAll('#modal-colors-list .option-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedColor = btn.dataset.color;
        render();
      });
    });

    // Sizes click handling
    body.querySelectorAll('#modal-sizes-list .option-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedSize = btn.dataset.size;
        render();
      });
    });

    // Add to cart click handling
    body.querySelector('#btn-modal-add-to-cart')?.addEventListener('click', () => {
      if (!activeVariant || !isAvailable) return;

      cart.addItem(
        {
          product_id: currentProduct.id,
          slug: currentProduct.slug,
          title: currentProduct.title,
          image_url: safeImage,
          price_minor: activeVariant.price_minor,
          variant_id: activeVariant.id,
          sku: activeVariant.sku,
          size: selectedSize,
          color: selectedColor,
        },
        {},
        1
      );

      close();
      if (onAddedToCart) onAddedToCart();
    });
  }

  async function open(productOrSlug) {
    selectedSize = null;
    selectedColor = null;
    errorMessage = null;

    modalContainer.classList.add('is-open');
    document.body.style.overflow = 'hidden';

    // If it's a slug or product object missing variants, fetch from API
    const slug = typeof productOrSlug === 'string' ? productOrSlug : productOrSlug?.slug;

    if (slug) {
      isLoading = true;
      render();

      try {
        currentProduct = await fetchProductBySlug(slug);
        isLoading = false;
        render();
      } catch (err) {
        isLoading = false;
        errorMessage = err.message || 'Unable to retrieve piece details.';
        render();
      }
    } else if (typeof productOrSlug === 'object') {
      currentProduct = productOrSlug;
      isLoading = false;
      render();
    }
  }

  function close() {
    modalContainer.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  modalContainer.querySelector('.drawer-backdrop').addEventListener('click', close);
  modalContainer.querySelector('#modal-close-btn').addEventListener('click', close);

  return {
    element: modalContainer,
    open,
    close
  };
}
