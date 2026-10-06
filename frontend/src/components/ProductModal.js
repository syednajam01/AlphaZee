import { cart } from '../utils/cart.js';
import { storeConfig } from '../data/store-config.js';

export function createProductModal(onAddedToCart) {
  const modalContainer = document.createElement('div');
  modalContainer.className = 'modal-container';
  modalContainer.id = 'product-modal';
  modalContainer.setAttribute('role', 'dialog');
  modalContainer.setAttribute('aria-modal', 'true');

  let currentProduct = null;
  let selectedSize = null;
  let selectedColor = null;

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
    if (!currentProduct) return;
    const body = modalContainer.querySelector('#modal-body-content');

    const sizes = currentProduct.options?.sizes || [];
    const colors = currentProduct.options?.colors || [];

    if (sizes.length > 0 && !selectedSize) selectedSize = sizes[0];
    if (colors.length > 0 && !selectedColor) selectedColor = colors[0];

    body.innerHTML = `
      <div class="modal-img-wrapper">
        <img src="${currentProduct.image}" alt="${currentProduct.title}" class="modal-img" />
      </div>

      <div class="modal-details">
        <span class="badge badge-accent" style="align-self: flex-start; margin-bottom: 8px;">
          ${currentProduct.stockStatus}
        </span>
        <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 4px;">${currentProduct.title}</h2>
        <div style="font-size: 1.35rem; font-weight: 700; color: var(--color-accent); margin-bottom: 12px;">
          ${currentProduct.formattedPrice}
        </div>
        <p style="font-size: 0.875rem; color: var(--color-text-muted); line-height: 1.5; margin-bottom: 16px;">
          ${currentProduct.description}
        </p>

        <!-- Color selector -->
        ${colors.length > 0 ? `
          <div class="option-group">
            <label class="option-label">Color: <strong>${selectedColor}</strong></label>
            <div class="option-pills" id="modal-colors-list">
              ${colors.map(col => `
                <button class="option-pill ${col === selectedColor ? 'is-selected' : ''}" data-color="${col}">
                  ${col}
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Size selector -->
        ${sizes.length > 0 ? `
          <div class="option-group">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <label class="option-label">Size: <strong>${selectedSize}</strong></label>
              <span style="font-size: 0.75rem; color: var(--color-text-muted); text-decoration: underline; cursor: pointer;">Size Guide</span>
            </div>
            <div class="option-pills" id="modal-sizes-list">
              ${sizes.map(sz => `
                <button class="option-pill ${sz === selectedSize ? 'is-selected' : ''}" data-size="${sz}">
                  ${sz}
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--color-border);">
          <button class="btn btn-primary" id="btn-modal-add-to-cart" style="width: 100%; min-height: 48px;">
            Add to Cart • ${currentProduct.formattedPrice}
          </button>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: 0.75rem; color: var(--color-text-muted);">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="3" width="15" height="13"></rect>
              <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
            </svg>
            <span>${storeConfig.shippingInfo.standardTime}</span>
          </div>
        </div>
      </div>
    `;

    // Colors listener
    body.querySelectorAll('#modal-colors-list .option-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedColor = btn.dataset.color;
        render();
      });
    });

    // Sizes listener
    body.querySelectorAll('#modal-sizes-list .option-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedSize = btn.dataset.size;
        render();
      });
    });

    // Add to cart listener
    body.querySelector('#btn-modal-add-to-cart')?.addEventListener('click', () => {
      const options = {};
      if (selectedSize) options.size = selectedSize;
      if (selectedColor) options.color = selectedColor;

      cart.addItem(currentProduct, options, 1);
      close();
      if (onAddedToCart) onAddedToCart();
    });
  }

  function open(product) {
    currentProduct = product;
    selectedSize = product.options?.sizes?.[0] || null;
    selectedColor = product.options?.colors?.[0] || null;
    render();
    modalContainer.classList.add('is-open');
    document.body.style.overflow = 'hidden';
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
