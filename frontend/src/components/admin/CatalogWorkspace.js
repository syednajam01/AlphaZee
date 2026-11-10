import * as api from '../../utils/api.js';
import { escapeHtml as esc, sanitizeMediaUrl } from '../../utils/dom.js';
import { parseCatalogPkr } from '../../utils/money.js';
import { mountVariantStock } from './VariantStock.js';

const button = (label, id = '', extra = '') => `<button type="button" class="btn btn-secondary" ${id ? `id="${id}"` : ''} ${extra}>${esc(label)}</button>`;
const options = (items, selected) => items.map(([value, label]) => `<option value="${esc(value)}" ${String(selected ?? '') === String(value) ? 'selected' : ''}>${esc(label)}</option>`).join('');
const field = (name, label, value, { textarea = false, type = 'text', max = 5000 } = {}) => `<label>${esc(label)}${textarea
  ? `<textarea name="${name}" maxlength="${max}" rows="3">${esc(value)}</textarea>`
  : `<input name="${name}" type="${type}" maxlength="${max}" value="${esc(value)}" ${type === 'number' ? 'min="0" step="1"' : ''}>`}</label>`;
const preview = asset => asset.kind === 'video'
  ? `<video controls preload="metadata" src="${esc(sanitizeMediaUrl(asset.url, ''))}" ${asset.poster_id ? `poster="/api/v1/media/${esc(asset.poster_id)}/content"` : ''} aria-label="Video preview"></video>`
  : `<img loading="lazy" src="${esc(sanitizeMediaUrl(asset.url))}" alt="${esc(asset.original_name || 'Catalog image')}">`;

export function catalogError(error) {
  const detail = error.data?.detail;
  const fields = Array.isArray(detail) ? detail.map(x => `${x.loc?.slice(1).join('.')}: ${x.msg}`)
    : (detail?.fields || []).map(x => `${x.field}: ${typeof x.message === 'string' ? x.message : 'This asset is still in use.'}`);
  const customMsg = detail?.code === 'reassignment_blocked' ? detail.message : null;
  return [customMsg || error.message || 'Unable to save', ...fields,
    error.status === 409 && detail?.code === 'edit_conflict' ? 'Your input is preserved. Reload the saved record to review the conflict.' : ''].filter(Boolean).join('\n');
}


export function collectVariant(row) {
  const value = name => row.querySelector(`[name="${name}"]`).value.trim();
  const price = value('price');
  const price_minor = price === '' ? null : parseCatalogPkr(price);
  if (price !== '' && price_minor === null) throw new Error('Variant price must be a nonnegative PKR amount with at most two decimal places.');
  const costInput = row.querySelector('[name="cost_price"]');
  const costPrice = (costInput && costInput.value !== undefined) ? String(costInput.value).trim() : '';
  const cost_price_minor = costPrice === '' ? null : parseCatalogPkr(costPrice);
  if (costPrice !== '' && cost_price_minor === null) throw new Error('Wholesale cost price must be a nonnegative PKR amount with at most two decimal places.');
  const sku = value('sku');
  if (!sku) throw new Error('Every saved variant needs a unique SKU. Remove an unfinished new row to save a draft without it.');
  const color = value('color');
  if (!color) throw new Error('Color is required for each variant. Please enter a color name.');
  const is_active = row.querySelector('[name="variant_active"]').checked;
  if (is_active && price_minor === null) throw new Error('Enter a price before activating this variant.');
  const stockInput = row.querySelector('[name="initial_stock"]');
  const rawStock = (stockInput && stockInput.value !== undefined) ? String(stockInput.value).trim() : '';
  let initial_stock = undefined;
  if (rawStock !== '') {
    const parsed = Number(rawStock);
    if (!Number.isSafeInteger(parsed) || parsed < 0) throw new Error('Variant stock must be a non-negative whole integer.');
    initial_stock = parsed;
  }
  return { ...(row.dataset.variantId ? { id: Number(row.dataset.variantId) } : {}), sku,
    size: value('size') || null, color: color || null, price_minor,
    ...(costInput ? { cost_price_minor } : {}),
    is_active, availability: value('availability'),
    ...(initial_stock !== undefined ? { initial_stock } : {}) };
}

export function mountCatalogSection(section, container, context) {
  const parentContext = context;
  let catalogDirty = false;
  const dirtyStock = new Set();
  context = { ...parentContext, setDirty(value) { catalogDirty = value; parentContext.setDirty(catalogDirty || dirtyStock.size > 0); } };
  let stockViews = [];
  let alive = true, busy = false, currentProduct = null, currentCollection = null;
  let mediaPage = 1, assets = [], assetTotal = 0, collections = [], links = [];
  const knownAssets = new Map();
  const posterDrafts = new Map();
  let productsPage = 1, productFilter = { search: '', status: '', collection_id: '' };
  const controllers = new Set(), objectUrls = new Set();
  const queue = [];
  let uploading = false;
  const current = () => alive && context.isCurrent();
  const query = selector => container.querySelector(selector);
  const value = (form, name) => form.querySelector(`[name="${name}"]`).value;
  const status = (message, error = false) => {
    if (!current()) return;
    const node = query('#catalog-status');
    if (node) { node.textContent = message; node.setAttribute('role', error ? 'alert' : 'status'); node.classList.toggle('catalog-error', error); }
  };
  const shell = html => {
    if (!current()) return;
    container.innerHTML = `<div class="catalog-workspace"><p id="catalog-status" role="status" aria-live="polite"></p>${html}</div>`;
  };
  const markDirty = () => { context.setDirty(true); status('Unsaved changes.'); };
  function fieldErrors(error) {
    container.querySelectorAll('[data-catalog-field-error]').forEach(node => node.remove());
    container.querySelectorAll('[aria-invalid]').forEach(node => node.removeAttribute('aria-invalid'));
    const detail = error.data?.detail;
    const items = Array.isArray(detail) ? detail.map(x => ({ field: x.loc?.at(-1), message: x.msg })) : detail?.fields || [];
    for (const item of items) {
      const name = String(item.field || '').split('.').at(-1);
      const mapped = name === 'price_minor' ? 'price' : name;
      const input = [...container.querySelectorAll('input, select, textarea')].find(node => node.name === mapped);
      if (!input || typeof item.message !== 'string') continue;
      input.setAttribute('aria-invalid', 'true');
      const label = input.closest('label');
      if (label) { const message = document.createElement('span'); message.setAttribute('data-catalog-field-error', ''); message.className = 'catalog-field-error'; message.textContent = item.message; label.appendChild(message); }
    }
  }
  function wireDirty(form) {
    form?.addEventListener('input', markDirty); form?.addEventListener('change', markDirty);
  }
  async function action(operation, success) {
    if (busy || !current()) return;
    busy = true;
    status('Working…');
    container.setAttribute('aria-busy', 'true');
    const controls = [...container.querySelectorAll('button, input, select, textarea')].map(node => [node, node.disabled]);
    controls.forEach(([node]) => { node.disabled = true; });
    try {
      const result = await operation();
      if (current()) await success?.(result);
      return result;
    } catch (error) { status(catalogError(error), true); if (current()) fieldErrors(error); }
    finally { busy = false; controls.forEach(([node, disabled]) => { node.disabled = disabled; }); if (current()) container.setAttribute('aria-busy', 'false'); }
  }
  function bind(id, fn) { query(id)?.addEventListener('click', fn); }
  async function loadAssets() {
    const data = await api.fetchOwnerMedia({ page: mediaPage, page_size: 100 });
    if (!current()) return;
    assets = data.assets || []; assetTotal = data.total || 0;
    assets.forEach(asset => knownAssets.set(asset.id, asset));
  }
  function imageChoices() {
    return [['', 'No image'], ...[...knownAssets.values()].filter(a => a.kind === 'image').map(a => [a.id, a.original_name])];
  }

  async function products() {
    const pageSize = 10;
    const [data, categories] = await Promise.all([
      api.fetchOwnerProducts({ ...productFilter, page: productsPage, page_size: pageSize }),
      api.fetchOwnerCollections()
    ]);
    if (!current()) return;
    currentProduct = null;
    collections = categories.collections || [];
    context.setDirty(false);

    const total = data.total || 0;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (productsPage > totalPages) productsPage = totalPages;

    shell(`
      <div class="catalog-header-bar">
        <div class="catalog-title-group">
          <button type="button" class="btn btn-primary btn-icon-only btn-new-draft" id="catalog-new-product" aria-label="New draft" title="New draft">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
          <span class="catalog-total-pill" title="Total products">${total} products</span>
        </div>
        <form id="catalog-search" class="catalog-search-form">
          <div class="search-field-wrap">
            <svg class="search-field-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input name="search" class="catalog-search-input" placeholder="Search title, slug, SKU…" value="${esc(productFilter.search || '')}" maxlength="200" aria-label="Search title, slug or SKU">
            ${productFilter.search ? '<button type="button" class="btn-clear-search" id="catalog-clear-search" title="Clear search">×</button>' : ''}
          </div>
          <div class="filter-select-wrap">
            <select name="status" class="catalog-filter-select" aria-label="Filter by status">
              ${options([['', 'All statuses'], ['draft', 'Draft'], ['published', 'Published'], ['archived', 'Archived']], productFilter.status)}
            </select>
          </div>
          <div class="filter-select-wrap">
            <select name="collection_id" class="catalog-filter-select" aria-label="Filter by collection">
              ${options([['', 'All collections'], ...collections.map(c => [c.id, c.name])], productFilter.collection_id)}
            </select>
          </div>
        </form>
      </div>

      ${(data.products || []).length ? `<div class="catalog-grid">${data.products.map(p => {
        const thumbUrl = p.image_url || p.media?.find(m => m.role === 'primary')?.asset?.url || p.media?.[0]?.asset?.url || '';
        const statusClass = p.status === 'published' ? 'status-published' : (p.status === 'draft' ? 'status-draft' : 'status-archived');
        const statusLabel = p.status === 'published' ? 'Published' : (p.status === 'draft' ? 'Draft' : 'Archived');
        const displayTitle = p.title || 'Untitled draft';
        const displaySlug = p.slug || 'no-slug';
        return `
          <article class="catalog-card catalog-product-card">
            <div class="catalog-card-body">
              <div class="catalog-card-media-wrapper">
                ${thumbUrl
                  ? `<img src="${esc(thumbUrl)}" alt="${esc(displayTitle)}" class="catalog-card-thumb" loading="lazy" decoding="async">`
                  : `<div class="catalog-card-thumb catalog-card-thumb-empty" title="No image uploaded">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                      </svg>
                    </div>`
                }
              </div>
              <div class="catalog-card-info">
                <div class="catalog-card-top-row">
                  <span class="catalog-status-badge ${statusClass}">${statusLabel}</span>
                  <span class="catalog-variants-count">${p.variants?.length || 0} variant${(p.variants?.length || 0) === 1 ? '' : 's'}</span>
                </div>
                <h3 class="catalog-card-title" title="${esc(displayTitle)}">${esc(displayTitle)}</h3>
                <p class="catalog-card-slug" title="/${esc(displaySlug)}">/${esc(displaySlug)}</p>
              </div>
            </div>
            <div class="catalog-card-actions">
              <button type="button" class="btn-card-action btn-card-edit" data-edit-product="${esc(p.id)}" title="Edit product" aria-label="Edit product">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
              <button type="button" class="btn-card-action btn-card-delete" data-delete-product="${esc(p.id)}" data-status="${esc(p.status)}" title="Delete product" aria-label="Delete product">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </article>
        `;
      }).join('')}</div>`
        : '<p>No products match. Create your first draft to begin.</p>'}

      <div class="catalog-pagination">
        <button type="button" class="btn-pagination" id="catalog-products-prev" ${productsPage <= 1 ? 'disabled' : ''} aria-label="Previous page" title="Previous page">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <span class="catalog-page-indicator"><span>Page </span><strong>${productsPage}</strong><span> of </span><strong>${totalPages}</strong></span>
        <button type="button" class="btn-pagination" id="catalog-products-next" ${productsPage >= totalPages ? 'disabled' : ''} aria-label="Next page" title="Next page">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    `);

    bind('#catalog-new-product', () => action(() => api.createOwnerProduct(), product => editProduct(product)));
    bind('#catalog-clear-search', () => {
      productFilter.search = '';
      productsPage = 1;
      action(products);
    });
    container.querySelectorAll('[data-edit-product]').forEach(node => node.addEventListener('click', () => action(() => api.fetchOwnerProduct(node.dataset.editProduct), p => editProduct(p))));
    container.querySelectorAll('[data-delete-product]').forEach(node => node.addEventListener('click', () => {
      const id = node.dataset.deleteProduct;
      const prodStatus = node.dataset.status;
      if (prodStatus === 'published') {
        status('Make it unpublished first then delete', true);
        if (typeof window !== 'undefined' && typeof window.alert === 'function') {
          window.alert('Make it unpublished first then delete');
        }
        return;
      }
      if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
        if (!window.confirm('Delete this product permanently? This action cannot be undone.')) return;
      }
      action(() => api.deleteOwnerProduct(id), async () => {
        await products();
        status('Product deleted.');
      });
    }));

    const searchForm = query('#catalog-search');
    const triggerSearch = () => {
      productFilter = {
        search: (searchForm.querySelector('[name="search"]')?.value || '').trim(),
        status: searchForm.querySelector('[name="status"]')?.value || '',
        collection_id: searchForm.querySelector('[name="collection_id"]')?.value || '',
      };
      productsPage = 1;
      action(products);
    };

    searchForm.addEventListener('submit', event => {
      event.preventDefault();
      triggerSearch();
    });
    searchForm.querySelector('[name="status"]')?.addEventListener('change', triggerSearch);
    searchForm.querySelector('[name="collection_id"]')?.addEventListener('change', triggerSearch);

    bind('#catalog-products-prev', () => {
      if (productsPage > 1) {
        productsPage--;
        action(products);
      }
    });
    bind('#catalog-products-next', () => {
      if (productsPage < totalPages) {
        productsPage++;
        action(products);
      }
    });
  }

  const STANDARD_SIZES = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', 'One Size'];

  function generateSkuSuggestion(colorName, size) {
    const slugInput = query('#catalog-product-form [name="slug"]')?.value?.trim();
    const titleInput = query('#catalog-product-form [name="title"]')?.value?.trim();
    const rawBase = slugInput || titleInput || currentProduct?.slug || currentProduct?.title || 'PROD';
    const basePart = String(rawBase)
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 14) || 'PROD';
    const colPart = String(colorName || 'COL')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 8) || 'COL';
    const sizePart = String(size || 'SZ')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 8) || 'SZ';
    return `${basePart}-${colPart}-${sizePart}`;
  }

  function variantRowMarkup(v, colorName) {
    const price = v.price_minor === null || v.price_minor === undefined ? '' : `${Math.floor(v.price_minor / 100)}.${String(v.price_minor % 100).padStart(2, '0')}`;
    const costPrice = v.cost_price_minor === null || v.cost_price_minor === undefined ? '' : `${Math.floor(v.cost_price_minor / 100)}.${String(v.cost_price_minor % 100).padStart(2, '0')}`;
    const size = v.size || '';
    const stock = v.stock_on_hand !== undefined ? v.stock_on_hand : '';
    const held = v.held_reservations || 0;
    const avail = v.available_to_sell !== undefined ? v.available_to_sell : stock;
    return `<fieldset class="catalog-variant variant-size-card" ${v.id ? `data-variant-id="${v.id}"` : ''} data-size="${esc(size)}">
      <legend class="variant-size-legend">
        Size: <strong>${esc(size || 'Standard')}</strong>${v.id ? ` · Variant #${v.id}` : ' · new'}
        ${v.id ? `<span class="variant-stock-summary-tag" style="margin-left: 10px; font-size: 0.75rem; color: rgba(255, 255, 255, 0.6); font-weight: normal;">(Stock: <strong style="color: #FFFFFF;">${stock || 0}</strong> | Held: ${held} | Avail: <strong style="color: ${avail > 0 ? '#4ADE80' : '#F87171'};">${avail || 0}</strong>)</span>` : ''}
      </legend>
      <input type="hidden" name="color" value="${esc(colorName || v.color || '')}">
      <input type="hidden" name="size" value="${esc(size)}">
      <div class="catalog-fields variant-fields-row">
        ${field('sku', 'SKU (required)', v.sku || '', { max: 100 })}
        ${field('price', 'Retail price PKR', price, { max: 20 })}
        ${field('cost_price', 'Wholesale cost PKR', costPrice, { max: 20 })}
        <label>Stock (units)
          <input type="number" name="initial_stock" min="0" step="1" placeholder="e.g. 10" value="${esc(String(stock !== '' ? stock : ''))}">
        </label>
        <label>Availability
          <select name="availability">${options([['available', 'Available'], ['unavailable', 'Unavailable'], ['unknown', 'Unknown']], v.availability || 'available')}</select>
        </label>
        <label class="variant-active-label">
          <input name="variant_active" type="checkbox" ${v.is_active ? 'checked' : ''}>
          <span>Active variant</span>
        </label>
        <div class="variant-action-wrap">
          ${v.id
            ? '<span class="variant-db-note" title="Saved in database">Saved in DB</span>'
            : '<button type="button" class="btn-card-action btn-remove-size" data-remove-variant title="Remove size" aria-label="Remove size" style="color: #f87171;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>'}
        </div>
      </div>
      ${v.id ? `<div data-variant-stock="${v.id}"></div>` : ''}
    </fieldset>`;
  }

  function colorCardMarkup(colorName, variants, index) {
    const activeSizes = new Set(variants.map(v => v.size || '').filter(Boolean));
    const allPillSizes = [...new Set([...STANDARD_SIZES, ...activeSizes])];
    return `<div class="color-group-card" data-color-index="${index}">
      <div class="color-group-header">
        <div class="color-group-title-wrap">
          <label class="color-name-label">
            <span class="color-label-text">Color Name <strong style="color: #f87171;">*</strong></span>
            <input type="text" class="color-group-name" value="${esc(colorName)}" placeholder="e.g. Jet Black, Chalk White, Forest Green" maxlength="100" required>
          </label>
        </div>
        <div class="color-group-batch-wrap">
          <div class="batch-price-box">
            <input type="text" class="color-batch-price" placeholder="Batch price (PKR)" maxlength="20" title="Retail selling price for all sizes">
            <button type="button" class="btn-card-action btn-apply-batch-price" title="Apply retail price to all sizes of this color" aria-label="Apply retail price to all sizes">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            </button>
          </div>
          <div class="batch-cost-box">
            <input type="text" class="color-batch-cost" placeholder="Batch cost (PKR)" maxlength="20" title="Wholesale cost for all sizes">
            <button type="button" class="btn-card-action btn-apply-batch-cost" title="Apply wholesale cost to all sizes of this color" aria-label="Apply wholesale cost to all sizes">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            </button>
          </div>
          <div class="batch-stock-box">
            <input type="number" min="0" step="1" class="color-batch-stock" placeholder="Batch stock" title="Stock units for all sizes">
            <button type="button" class="btn-card-action btn-apply-batch-stock" title="Apply stock to all sizes of this color" aria-label="Apply stock to all sizes">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            </button>
          </div>
          <button type="button" class="btn-card-action btn-remove-color-group" title="Remove this color group" aria-label="Remove this color group" style="color: #f87171;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </div>
      <div class="color-sizes-selector-section">
        <div class="color-sizes-label">Available Sizes for this Color (click to enable/disable):</div>
        <div class="color-sizes-pills-bar">
          ${allPillSizes.map(sz => {
            const isActive = activeSizes.has(sz);
            return `<button type="button" class="size-pill ${isActive ? 'is-active' : 'is-inactive'}" data-size="${esc(sz)}">${isActive ? '✓' : '+'} ${esc(sz)}</button>`;
          }).join('')}
          <div class="custom-size-adder">
            <input type="text" class="custom-size-input" placeholder="Custom size" maxlength="50">
            <button type="button" class="btn btn-secondary btn-add-custom-size" style="font-size: 0.75rem; padding: 4px 8px;">+ Add Size</button>
          </div>
        </div>
      </div>
      <div class="color-variants-list">
        ${variants.map(v => variantRowMarkup(v, colorName)).join('')}
      </div>
    </div>`;
  }

  function variantMarkup(v, index) {
    return variantRowMarkup(v, v.color || '');
  }

  function wireColorGroup(card) {
    const nameInput = card.querySelector('.color-group-name');
    nameInput?.addEventListener('input', () => {
      const newColor = nameInput.value.trim();
      card.querySelectorAll('.catalog-variant input[name="color"]').forEach(inp => {
        inp.value = newColor;
      });
      markDirty();
    });

    const pillsBar = card.querySelector('.color-sizes-pills-bar');
    const variantsList = card.querySelector('.color-variants-list');

    function wirePill(pill) {
      pill.addEventListener('click', () => {
        const sz = pill.dataset.size;
        const isCurrentlyActive = pill.classList.contains('is-active');
        if (isCurrentlyActive) {
          const row = [...variantsList.querySelectorAll('.catalog-variant')].find(r => r.dataset.size === sz);
          if (row) {
            if (row.dataset.variantId) {
              if (!window.confirm(`Variant #${row.dataset.variantId} (Size ${sz}) is saved in catalog. Remove this variant?`)) return;
            }
            row.remove();
            pill.classList.remove('is-active');
            pill.classList.add('is-inactive');
            pill.textContent = `+ ${sz}`;
            markDirty();
          }
        } else {
          const cName = nameInput ? nameInput.value.trim() : '';
          const batchPrice = card.querySelector('.color-batch-price')?.value?.trim();
          const pMinor = batchPrice ? parseCatalogPkr(batchPrice) : null;
          const batchCost = card.querySelector('.color-batch-cost')?.value?.trim();
          const cMinor = batchCost ? parseCatalogPkr(batchCost) : null;
          const batchStock = card.querySelector('.color-batch-stock')?.value?.trim();
          const sUnits = batchStock && !isNaN(Number(batchStock)) && Number(batchStock) >= 0 ? parseInt(batchStock, 10) : undefined;
          const suggestedSku = generateSkuSuggestion(cName, sz);
          const wrapper = document.createElement('div');
          wrapper.innerHTML = variantRowMarkup({
            sku: suggestedSku,
            size: sz,
            color: cName,
            price_minor: pMinor,
            cost_price_minor: cMinor,
            stock_on_hand: sUnits,
            is_active: false,
            availability: 'available',
          }, cName);
          const newRow = wrapper.firstElementChild || wrapper;
          variantsList.appendChild(newRow);
          wireRemoveVariants();
          pill.classList.remove('is-inactive');
          pill.classList.add('is-active');
          pill.textContent = `✓ ${sz}`;
          markDirty();
        }
      });
    }

    card.querySelectorAll('.size-pill').forEach(wirePill);

    const customInput = card.querySelector('.custom-size-input');
    const addCustomBtn = card.querySelector('.btn-add-custom-size');
    const handleAddCustom = () => {
      const rawSz = customInput.value.trim();
      if (!rawSz) { customInput.focus(); return; }
      let pill = [...card.querySelectorAll('.size-pill')].find(p => p.dataset.size?.toUpperCase() === rawSz.toUpperCase());
      if (!pill) {
        pill = document.createElement('button');
        pill.type = 'button';
        pill.className = 'size-pill is-inactive';
        pill.setAttribute('data-size', rawSz);
        pill.textContent = `+ ${rawSz}`;
        const adder = card.querySelector('.custom-size-adder');
        if (adder) {
          pillsBar.insertBefore(pill, adder);
        } else {
          pillsBar.appendChild(pill);
        }
        wirePill(pill);
      }
      if (pill.classList.contains('is-inactive')) {
        pill.click();
      }
      customInput.value = '';
    };
    addCustomBtn?.addEventListener('click', handleAddCustom);
    customInput?.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleAddCustom();
      }
    });

    const batchPriceBtn = card.querySelector('.btn-apply-batch-price');
    batchPriceBtn?.addEventListener('click', () => {
      const batchInput = card.querySelector('.color-batch-price');
      const batchVal = batchInput.value.trim();
      if (!batchVal) {
        status('Enter a price amount in PKR first.', true);
        return;
      }
      const pMinor = parseCatalogPkr(batchVal);
      if (pMinor === null) {
        status('Variant price must be a nonnegative PKR amount with at most two decimal places.', true);
        return;
      }
      const formatted = `${Math.floor(pMinor / 100)}.${String(pMinor % 100).padStart(2, '0')}`;
      variantsList.querySelectorAll('.catalog-variant input[name="price"]').forEach(inp => {
        inp.value = formatted;
      });
      markDirty();
      status(`Applied PKR ${formatted} to sizes in this color.`);
    });

    const batchCostBtn = card.querySelector('.btn-apply-batch-cost');
    batchCostBtn?.addEventListener('click', () => {
      const batchInput = card.querySelector('.color-batch-cost');
      const batchVal = batchInput.value.trim();
      if (!batchVal) {
        status('Enter a wholesale cost amount in PKR first.', true);
        return;
      }
      const cMinor = parseCatalogPkr(batchVal);
      if (cMinor === null) {
        status('Wholesale cost must be a nonnegative PKR amount with at most two decimal places.', true);
        return;
      }
      const formatted = `${Math.floor(cMinor / 100)}.${String(cMinor % 100).padStart(2, '0')}`;
      variantsList.querySelectorAll('.catalog-variant input[name="cost_price"]').forEach(inp => {
        inp.value = formatted;
      });
      markDirty();
      status(`Applied wholesale cost PKR ${formatted} to sizes in this color.`);
    });

    const batchStockBtn = card.querySelector('.btn-apply-batch-stock');
    batchStockBtn?.addEventListener('click', () => {
      const stockInput = card.querySelector('.color-batch-stock');
      const stockVal = stockInput.value.trim();
      if (!stockVal || isNaN(Number(stockVal)) || Number(stockVal) < 0) {
        status('Enter a non-negative whole unit stock number first.', true);
        return;
      }
      const val = parseInt(stockVal, 10);
      variantsList.querySelectorAll('.catalog-variant input[name="initial_stock"]').forEach(inp => {
        inp.value = val;
      });
      markDirty();
      status(`Applied stock (${val} units) to all sizes in this color.`);
    });

    const removeColorBtn = card.querySelector('.btn-remove-color-group');
    removeColorBtn?.addEventListener('click', () => {
      const savedVariants = card.querySelectorAll('.catalog-variant[data-variant-id]');
      if (savedVariants.length > 0) {
        if (!window.confirm('This color has variants already saved in the catalog. Removing it will delete these variants when saved. Continue?')) return;
      }
      card.remove();
      markDirty();
    });
  }

  function renderStockMatrix(variants) {
    if (!variants || variants.length === 0) return '';
    const colors = [...new Set(variants.map(v => v.color || 'Standard'))];
    const sizes = [...new Set(variants.map(v => v.size || 'Standard'))];
    let grandStock = 0, grandAvail = 0;

    const rows = colors.map(col => {
      let colStock = 0;
      let colAvail = 0;
      const cells = sizes.map(sz => {
        const match = variants.find(v => (v.color || 'Standard') === col && (v.size || 'Standard') === sz);
        if (!match) return '<td style="padding: 6px 10px; text-align: center; color: rgba(255,255,255,0.25);">—</td>';
        const st = match.stock_on_hand || 0;
        const av = match.available_to_sell !== undefined ? match.available_to_sell : st;
        colStock += st;
        colAvail += av;
        grandStock += st;
        grandAvail += av;
        return `<td style="padding: 6px 10px; text-align: center;"><span style="color: #FFFFFF; font-weight: 600;">${st}</span> <span style="color: ${av > 0 ? '#4ADE80' : '#F87171'}; font-size: 0.75rem;">(${av} av)</span></td>`;
      }).join('');
      return `<tr style="border-bottom: 1px solid rgba(255,255,255,0.06);"><td style="padding: 6px 10px; font-weight: 600; color: #FFFFFF;">${esc(col)}</td>${cells}<td style="padding: 6px 10px; text-align: right; font-weight: 700; color: #60A5FA;">${colStock} <span style="font-size: 0.75rem; color: #94A3B8;">(${colAvail} av)</span></td></tr>`;
    }).join('');

    return `
      <details class="catalog-stock-matrix-accordion" style="margin: 14px 0 20px 0; background: #161A18; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 12px;" open>
        <summary style="font-weight: 700; cursor: pointer; color: #FFFFFF; font-size: 0.875rem; user-select: none;">
          Color × Size Stock Breakdown & Reorder Matrix (Total: ${grandStock} on hand · ${grandAvail} available to sell)
        </summary>
        <div style="overflow-x: auto; margin-top: 12px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.8125rem;">
            <thead>
              <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); color: rgba(255,255,255,0.6);">
                <th style="padding: 6px 10px; text-align: left;">Color</th>
                ${sizes.map(sz => `<th style="padding: 6px 10px; text-align: center;">Size ${esc(sz)}</th>`).join('')}
                <th style="padding: 6px 10px; text-align: right;">Total Units</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </details>
    `;
  }

  async function editProduct(product) {
    stockViews.forEach(v => v.destroy()); stockViews = [];
    const [supData] = await Promise.all([
      api.fetchAdminSuppliers().catch(() => ({ suppliers: [] })),
      loadAssets(),
    ]);
    if (!current()) return;
    const activeVendors = (supData?.suppliers || []).filter(s => s.status === 'active' && s.supplier_type !== 'alphazee_internal');
    const vendorOptions = activeVendors.map(v => `<option value="${esc(v.id)}" ${String(product.vendor_id || '') === String(v.id) ? 'selected' : ''}>${esc(v.name)} (${esc(v.slug)})</option>`).join('');

    currentProduct = product; links = (product.media || []).map(link => ({ ...link, asset_id: link.asset.id }));
    context.setDirty(false);
    const archived = product.status === 'archived';

    const colorMap = new Map();
    for (const v of product.variants || []) {
      const col = v.color ? v.color.trim() : '';
      if (!colorMap.has(col)) colorMap.set(col, []);
      colorMap.get(col).push(v);
    }
    let initialColorGroupsHtml = '';
    if (colorMap.size === 0) {
      initialColorGroupsHtml = colorCardMarkup('', [], 0);
    } else {
      let idx = 0;
      for (const [cName, vars] of colorMap.entries()) {
        initialColorGroupsHtml += colorCardMarkup(cName, vars, idx++);
      }
    }

    const activeColIds = new Set(product.collection_ids || (product.collection_id ? [product.collection_id] : []));

    const statusClass = product.status === 'published' ? 'status-published' : (product.status === 'draft' ? 'status-draft' : 'status-archived');
    const statusLabel = product.status === 'published' ? 'Published' : (product.status === 'draft' ? 'Draft' : 'Archived');
    const displayTitle = product.title || 'Untitled draft';

    shell(`
      <div class="draft-header-bar">
        <div class="draft-header-left">
          <button type="button" class="btn-action-icon" id="catalog-back-products" title="Back to products" aria-label="Back to products">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
          </button>
          <div class="draft-title-block">
            <h2 class="draft-page-title" title="${esc(displayTitle)}">${esc(displayTitle)}</h2>
            <div class="draft-meta-tags">
              <span class="catalog-status-badge ${statusClass}">${statusLabel}</span>
              <span id="catalog-product-state" class="catalog-version-pill" title="Version ${product.edit_version}">v${product.edit_version}</span>
            </div>
          </div>
        </div>

        <div class="draft-header-actions">
          <button type="button" class="btn-action-icon" id="catalog-reload-product" title="Reload saved product" aria-label="Reload saved product">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
          </button>

          ${!archived ? `
            <button type="button" class="btn-action-icon ${product.status === 'published' ? 'btn-action-unpublish' : 'btn-action-publish'}" id="catalog-publish" title="${product.status === 'published' ? 'Unpublish product (make private)' : 'Publish product (make live)'}" aria-label="${product.status === 'published' ? 'Unpublish product' : 'Publish product'}">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                ${product.status === 'published'
                  ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`
                  : `<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>`
                }
              </svg>
            </button>
            <button type="button" class="btn-action-icon btn-action-archive" id="catalog-archive" title="Archive product" aria-label="Archive product">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="21 8 21 21 3 21 3 8"></polyline>
                <rect x="1" y="3" width="22" height="5"></rect>
                <line x1="10" y1="12" x2="14" y2="12"></line>
              </svg>
            </button>
          ` : `
            <button type="button" class="btn-action-icon btn-action-restore" id="catalog-restore" title="Restore to draft" aria-label="Restore to draft">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="1 4 1 10 7 10"></polyline>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
              </svg>
            </button>
          `}

          <button type="button" class="btn-action-icon btn-action-delete" id="catalog-delete-product" title="Delete product" aria-label="Delete product">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>

          <button type="submit" form="catalog-product-form" class="btn-action-icon btn-action-save" id="catalog-save-product" title="Save product and media" aria-label="Save product and media">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17 21 17 13 7 13 7 21"></polyline>
              <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
          </button>
        </div>
      </div>

      <form id="catalog-product-form" class="catalog-edit-form">
        <fieldset ${archived ? 'disabled' : ''} class="catalog-edit-fieldset">

          <!-- Card 1: Basic Information (Row by row) -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Basic Information</h3>
              <p class="catalog-form-card-desc">Product title, URL slug, and customer descriptions.</p>
            </div>
            <div class="form-rows-stack">
              <div class="form-row-2col">
                ${field('title', 'Product Title', product.title, { max: 300 })}
                ${field('slug', 'URL Slug (unique)', product.slug, { max: 100 })}
              </div>
              <div class="form-row">
                ${field('badge', 'Card Badge (e.g. New Season, Limited Edition)', product.badge, { max: 100 })}
              </div>
              <div class="form-row">
                ${field('short_description', 'Short Summary (appears in previews and lists)', product.short_description, { textarea: true, max: 2000 })}
              </div>
              <div class="form-row">
                ${field('description', 'Customer Detailed Description', product.description, { textarea: true, max: 20000 })}
              </div>
            </div>
          </div>

          <!-- Card 2: Organization & Inventory Responsibility -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Organization & Stock Responsibility</h3>
              <p class="catalog-form-card-desc">Categorization and vendor stock assignment.</p>
            </div>
            <div class="form-rows-stack">
              <div class="form-row">
                <label class="section-sublabel">Collections (multi-select)</label>
                <div class="collections-chips-grid" id="product-collections-checkboxes">
                  ${collections.map(c => `
                    <label class="collection-chip ${activeColIds.has(c.id) ? 'is-selected' : ''}">
                      <input type="checkbox" name="collection_ids" value="${esc(c.id)}" ${activeColIds.has(c.id) ? 'checked' : ''} class="col-checkbox">
                      <span>${esc(c.name)}${c.is_active ? '' : ' <em class="chip-inactive">(inactive)</em>'}</span>
                    </label>
                  `).join('') || '<p class="field-empty-note">No collections created yet.</p>'}
                </div>
                <select name="collection_id" style="display: none;">
                  ${options([['', 'Choose later'], ...collections.map(c => [c.id, c.name])], product.collection_id)}
                </select>
                <p class="field-help-text">Check all collections where this product should appear.</p>
              </div>

              <div class="form-row">
                <label class="section-sublabel">Who manages this product's inventory?</label>
                <div class="stock-source-options">
                  <label class="stock-source-card ${(product.stock_management_source || 'alphazee_managed') === 'alphazee_managed' ? 'is-selected' : ''}">
                    <input type="radio" name="stock_management_source" value="alphazee_managed" ${(product.stock_management_source || 'alphazee_managed') === 'alphazee_managed' ? 'checked' : ''} id="source-alphazee">
                    <div class="source-card-content">
                      <strong class="source-card-title">AlphaZee Internal</strong>
                      <span class="source-card-desc">Stock counted and held directly in-house without an external vendor.</span>
                    </div>
                  </label>
                  <label class="stock-source-card ${product.stock_management_source === 'vendor_managed' ? 'is-selected' : ''}">
                    <input type="radio" name="stock_management_source" value="vendor_managed" ${product.stock_management_source === 'vendor_managed' ? 'checked' : ''} id="source-vendor">
                    <div class="source-card-content">
                      <strong class="source-card-title">Vendor Shop</strong>
                      <span class="source-card-desc">Inventory allocated and counted by an authorized vendor partner.</span>
                    </div>
                  </label>
                </div>
                <div id="vendor-selection-wrapper" style="display: ${product.stock_management_source === 'vendor_managed' ? 'block' : 'none'}; margin-top: 12px;">
                  <label>Assigned Vendor Shop
                    <select name="vendor_id" id="catalog-vendor-id" class="vendor-select-dropdown">
                      <option value="">-- Choose active vendor shop --</option>
                      ${vendorOptions}
                    </select>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Card 3: Specifications & Care Instructions -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Fabric & Specifications</h3>
              <p class="catalog-form-card-desc">Material composition, wash care instructions, and sizing advice.</p>
            </div>
            <div class="form-rows-stack">
              <div class="form-row">
                ${field('material', 'Material & Fabric Composition', product.material, { textarea: true })}
              </div>
              <div class="form-row">
                ${field('care', 'Care Instructions', product.care, { textarea: true })}
              </div>
              <div class="form-row">
                ${field('sizing', 'Sizing Details & Fit Guide', product.sizing, { textarea: true })}
              </div>
            </div>
          </div>

          <!-- Card 4: Homepage Hero Placement -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Homepage Hero Placement</h3>
              <p class="catalog-form-card-desc">Showcase this product prominently in the homepage hero carousel.</p>
            </div>
            <div class="form-rows-stack">
              <div class="form-row">
                <label class="hero-checkbox-label">
                  <input name="is_hero" type="checkbox" ${product.is_hero ? 'checked' : ''}>
                  <span>Feature this product in the homepage hero banner</span>
                </label>
              </div>
              <div class="form-row-2col">
                ${field('hero_order', 'Hero Slide Order (0 = first)', product.hero_order, { type: 'number' })}
                ${field('hero_benefit', 'Hero Benefit / Headline Tagline', product.hero_benefit, { max: 2000 })}
              </div>
            </div>
          </div>

          <!-- Card 5: Colors & Available Sizes -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header catalog-variants-card-header">
              <div>
                <h3 class="catalog-form-card-title">Colors & Available Sizes</h3>
                <p class="catalog-form-card-desc">Define each color variant and choose sizes offered. Each size creates an inventory-tracked variant.</p>
              </div>
              <button type="button" class="btn btn-secondary btn-add-color-head" id="catalog-add-color">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                <span>Add Color</span>
              </button>
            </div>
            ${product.id && product.variants?.length ? renderStockMatrix(product.variants) : ''}
            <div id="catalog-variants">${initialColorGroupsHtml}</div>
          </div>

          <!-- Card 6: Storefront Card Images -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Storefront Card Images</h3>
              <p class="catalog-form-card-desc">Explicitly select the Card Front image and Card Hover/Back image shown in product listings.</p>
            </div>
            <div class="role-selector-grid">
              <div class="role-selector-card" id="card-front-selector-card">
                <div class="role-thumbnail" id="card-front-thumb">No front image</div>
                <div class="role-selector-info">
                  <strong class="role-info-title">Card Front Image (Primary)</strong>
                  <p class="role-info-desc">Main image displayed on category pages, search results, and hero.</p>
                  <label class="role-select-label">Select front image:
                    <select id="catalog-select-front"></select>
                  </label>
                  <button type="button" class="btn btn-secondary btn-clear-role" id="catalog-clear-front">Clear front image</button>
                </div>
              </div>
              <div class="role-selector-card" id="card-hover-selector-card">
                <div class="role-thumbnail" id="card-hover-thumb">No hover image</div>
                <div class="role-selector-info">
                  <strong class="role-info-title">Card Hover / Back Image</strong>
                  <p class="role-info-desc">Revealed on desktop cursor hover. Defaults to front image if unset.</p>
                  <label class="role-select-label">Select hover image:
                    <select id="catalog-select-hover"></select>
                  </label>
                  <button type="button" class="btn btn-secondary btn-clear-role" id="catalog-clear-hover">Clear hover image</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Card 7: Product Gallery & Library Upload -->
          <div class="catalog-form-card">
            <div class="catalog-form-card-header">
              <h3 class="catalog-form-card-title">Product Gallery & Media</h3>
              <p class="catalog-form-card-desc">Uploaded files are securely stored. Detaching keeps the file available in your library.</p>
            </div>
            <div id="catalog-product-media"></div>
            <div class="media-library-toolbar">
              <div class="media-toolbar-selects">
                <label class="media-select-label">Library asset
                  <select id="catalog-attach-asset">${options([['', 'Choose library asset…'], ...assets.map(a => [a.id, `${a.original_name} (${a.kind})`])])}</select>
                </label>
                <label class="media-select-label">Role
                  <select id="catalog-attach-role">${options([['gallery', 'Gallery'], ['primary', 'Primary image (card front)'], ['hover_image', 'Hover image (card back)'], ['hero_image', 'Hero image'], ['hero_video', 'Hero video'], ['hero_poster', 'Hero poster']])}</select>
                </label>
                <button type="button" class="btn btn-secondary btn-icon-only" id="catalog-attach" title="Attach asset to product" aria-label="Attach asset">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                </button>
              </div>
              <div class="media-toolbar-pagination">
                <button type="button" class="btn-pagination" id="catalog-library-prev" ${mediaPage === 1 ? 'disabled' : ''} title="Previous library page" aria-label="Previous library page">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
                </button>
                <span class="catalog-page-indicator"><span>Page </span><strong>${mediaPage}</strong></span>
                <button type="button" class="btn-pagination" id="catalog-library-next" ${mediaPage * 100 >= assetTotal ? 'disabled' : ''} title="Next library page" aria-label="Next library page">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
                </button>
              </div>
            </div>
            <div id="catalog-upload-box"></div>
          </div>

          <!-- Invisible publication requirements container to satisfy existing JS methods -->
          <ul id="catalog-requirements" style="display: none;" hidden></ul>
        </fieldset>
      </form>
    `);
    requirements(product); renderLinks(); wireRoleSelectors(); updateRoleSelectors();
    if (!archived) mountUploadBox(() => loadAssets().then(updateAssetChoices));
    const form = query('#catalog-product-form'); wireDirty(form);
    const sourceAlphazee = query('#source-alphazee');
    const sourceVendor = query('#source-vendor');
    const vendorWrapper = query('#vendor-selection-wrapper');
    const vendorSelect = query('#catalog-vendor-id');
    const updateVendorVisibility = () => {
      const isVendor = sourceVendor?.checked;
      if (vendorWrapper) {
        vendorWrapper.style.display = isVendor ? 'block' : 'none';
      }
      if (!isVendor && vendorSelect) {
        vendorSelect.value = '';
      }
      query('#source-alphazee')?.closest('.stock-source-card')?.classList.toggle('is-selected', !isVendor);
      query('#source-vendor')?.closest('.stock-source-card')?.classList.toggle('is-selected', isVendor);
      markDirty();
    };
    sourceAlphazee?.addEventListener('change', updateVendorVisibility);
    sourceVendor?.addEventListener('change', updateVendorVisibility);
    form.querySelectorAll('.col-checkbox').forEach(cb => {
      cb.addEventListener('change', () => {
        cb.closest('.collection-chip')?.classList.toggle('is-selected', cb.checked);
        markDirty();
      });
    });
    bind('#catalog-back-products', () => { if (context.canLeave()) action(products); });
    bind('#catalog-reload-product', () => { if (context.canLeave()) action(() => api.fetchOwnerProduct(product.id), p => editProduct(p)); });

    container.querySelectorAll('.color-group-card').forEach(wireColorGroup);
    wireRemoveVariants();

    bind('#catalog-add-color', () => {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = colorCardMarkup('', [], query('#catalog-variants').children.length);
      const newCard = wrapper.firstElementChild || wrapper;
      query('#catalog-variants').appendChild(newCard);
      wireColorGroup(newCard);
      newCard.querySelector('.color-group-name')?.focus();
      markDirty();
    });
    let supplierRequest;
    const suppliers = () => {
      // Refresh after creation, and share concurrent initial reads between variants.
      if (!supplierRequest) supplierRequest = api.fetchAdminSuppliers().finally(() => { supplierRequest = null; });
      return supplierRequest;
    };
    for (const variant of product.variants || []) {
      if (archived) continue;
      stockViews.push(mountVariantStock(query(`[data-variant-stock="${variant.id}"]`), variant, {
        isCurrent: current, suppliers, product,
        getProduct: () => ({
          ...product,
          stock_management_source: form.querySelector('input[name="stock_management_source"]:checked')?.value || product.stock_management_source || 'alphazee_managed',
          vendor_id: form.querySelector('#catalog-vendor-id')?.value || product.vendor_id || null,
        }),
        onDirty(id, value) { if (value) dirtyStock.add(id); else dirtyStock.delete(id); parentContext.setDirty(catalogDirty || dirtyStock.size > 0); },
      }));
    }
    bind('#catalog-attach', () => {
      const asset = assets.find(a => a.id === query('#catalog-attach-asset').value), role = query('#catalog-attach-role').value;
      if (!asset) { status('Choose a library asset first.', true); return; }
      if ((role === 'hero_video') !== (asset.kind === 'video') && role !== 'gallery') { status('This role requires a different media type.', true); return; }
      syncLinks();
      if (role !== 'gallery') links = links.filter(l => l.role !== role);
      if (!links.some(l => l.asset_id === asset.id && l.role === role && !l.variant_id)) links.push({ asset, asset_id: asset.id, role, variant_id: null, alt_text: '', display_order: links.length });
      renderLinks(); updateRoleSelectors(); markDirty();
    });
    async function changeLibraryPage(delta) { mediaPage += delta; await loadAssets(); updateAssetChoices(); }
    bind('#catalog-library-prev', () => action(() => changeLibraryPage(-1)));
    bind('#catalog-library-next', () => action(() => changeLibraryPage(1)));
    form.addEventListener('submit', event => {
      event.preventDefault();
      action(async () => {
        if (dirtyStock.size) throw new Error('Save or reload the unsaved supplier/stock inputs before saving product details.');

        const colorCards = query('#catalog-variants')?.querySelectorAll('.color-group-card') || [];
        for (const card of colorCards) {
          const varRows = card.querySelectorAll('.catalog-variant');
          const nameInput = card.querySelector('.color-group-name');
          const cName = nameInput?.value?.trim();
          if (varRows.length > 0 && !cName) {
            nameInput?.focus();
            throw new Error('Color name is required for each color section with sizes.');
          }
        }

        const selectedColIds = [...form.querySelectorAll('input[name="collection_ids"]:checked')].map(cb => cb.value);
        const fields = Object.fromEntries(['title', 'slug', 'badge', 'description', 'short_description', 'material', 'care', 'sizing', 'hero_benefit'].map(name => [name, value(form, name).trim() || null]));
        fields.collection_ids = selectedColIds;
        fields.collection_id = selectedColIds[0] || null;
        fields.is_hero = form.querySelector('[name="is_hero"]').checked;
        const order = value(form, 'hero_order'); fields.hero_order = order === '' ? null : Number(order);
        if (fields.hero_order !== null && (!Number.isSafeInteger(fields.hero_order) || fields.hero_order < 0)) throw new Error('Hero order must be a nonnegative whole number.');
        fields.variants = [...query('#catalog-variants').querySelectorAll('.catalog-variant')].map(collectVariant);
        const sourceVal = form.querySelector('input[name="stock_management_source"]:checked')?.value || 'alphazee_managed';
        fields.stock_management_source = sourceVal;
        if (sourceVal === 'vendor_managed') {
          const rawVid = form.querySelector('[name="vendor_id"]')?.value?.trim();
          fields.vendor_id = rawVid || null;
        } else {
          fields.vendor_id = null;
        }
        syncLinks();
        const mediaItems = links.map((l, index) => ({ asset_id: l.asset_id, role: l.role, variant_id: l.variant_id, alt_text: l.alt_text, display_order: index }));
        const untouchedLegacyMedia = currentProduct.image_url && !currentProduct.media?.length && !mediaItems.length;
        return api.updateOwnerProduct(currentProduct.id, { ...fields, expected_version: currentProduct.edit_version,
          ...(!untouchedLegacyMedia ? { media: mediaItems } : {}) });
      }, async saved => { await editProduct(saved); status('Product and media saved.'); });
    });
    for (const [id, transition] of [['#catalog-publish', product.status === 'published' ? 'unpublish' : 'publish'], ['#catalog-archive', 'archive'], ['#catalog-restore', 'restore']]) {
      bind(id, () => {
        if (!context.canLeave()) return;
        if (transition === 'archive' && !window.confirm('Archive this product? Its history will remain available.')) return;
        action(() => api.transitionOwnerProduct(currentProduct.id, transition, currentProduct.edit_version), async saved => { await editProduct(saved); status(`Product ${saved.status}.`); });
      });
    }
    bind('#catalog-delete-product', () => {
      if (currentProduct.status === 'published') {
        status('Make it unpublished first then delete', true);
        if (typeof window !== 'undefined' && typeof window.alert === 'function') {
          window.alert('Make it unpublished first then delete');
        }
        return;
      }
      if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
        if (!window.confirm('Delete this product permanently? This action cannot be undone.')) return;
      }
      action(() => api.deleteOwnerProduct(currentProduct.id), async () => {
        context.setDirty(false);
        await products();
        status('Product deleted.');
      });
    });
  }

  function requirements(product) {
    const list = query('#catalog-requirements');
    if (list) list.innerHTML = product.publication_requirements?.length ? product.publication_requirements.map(x => `<li>${esc(x.field)}: ${esc(x.message)}</li>`).join('') : '<li>All required fields are complete. Stock is managed separately.</li>';
  }

  function updateRoleSelectors() {
    const frontNode = query('#card-front-thumb');
    const hoverNode = query('#card-hover-thumb');
    const frontSelect = query('#catalog-select-front');
    const hoverSelect = query('#catalog-select-hover');
    const clearFrontBtn = query('#catalog-clear-front');
    const clearHoverBtn = query('#catalog-clear-hover');

    const frontLink = links.find(l => l.role === 'primary');
    const frontAsset = frontLink?.asset || (frontLink?.asset_id ? knownAssets.get(frontLink.asset_id) : null);

    const hoverLink = links.find(l => l.role === 'hover_image');
    const hoverAsset = hoverLink?.asset || (hoverLink?.asset_id ? knownAssets.get(hoverLink.asset_id) : null);

    const availableImages = new Map();
    assets.filter(a => a.kind === 'image').forEach(a => availableImages.set(a.id, a));
    links.filter(l => l.asset?.kind === 'image').forEach(l => availableImages.set(l.asset.id, l.asset));

    const imgOpts = [...availableImages.values()].map(a => [a.id, a.original_name || 'Image']);

    if (frontSelect) frontSelect.innerHTML = options([['', 'Choose front image'], ...imgOpts], frontAsset?.id);
    if (hoverSelect) hoverSelect.innerHTML = options([['', 'Choose hover image (optional)'], ...imgOpts], hoverAsset?.id);

    if (frontNode) {
      frontNode.innerHTML = frontAsset ? `<img src="${esc(sanitizeMediaUrl(frontAsset.url))}" alt="Card front" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">` : 'No front image';
    }
    if (hoverNode) {
      hoverNode.innerHTML = hoverAsset ? `<img src="${esc(sanitizeMediaUrl(hoverAsset.url))}" alt="Card hover" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">` : 'No hover image';
    }

    if (clearFrontBtn) clearFrontBtn.style.display = frontAsset ? 'inline-block' : 'none';
    if (clearHoverBtn) clearHoverBtn.style.display = hoverAsset ? 'inline-block' : 'none';
  }

  function wireRoleSelectors() {
    query('#catalog-select-front')?.addEventListener('change', event => {
      const assetId = event.target.value;
      const asset = knownAssets.get(assetId) || assets.find(a => a.id === assetId) || links.find(l => l.asset_id === assetId)?.asset;
      syncLinks();
      links = links.filter(l => l.role !== 'primary');
      if (asset) {
        links.unshift({ asset, asset_id: asset.id, role: 'primary', variant_id: null, alt_text: '', display_order: 0 });
      }
      updateRoleSelectors();
      renderLinks();
      markDirty();
    });

    query('#catalog-clear-front')?.addEventListener('click', () => {
      if (currentProduct?.status === 'published') {
        status('Published products require a primary front image. Choose a replacement or unpublish first.', true);
        return;
      }
      syncLinks();
      links = links.filter(l => l.role !== 'primary');
      updateRoleSelectors();
      renderLinks();
      markDirty();
    });

    query('#catalog-select-hover')?.addEventListener('change', event => {
      const assetId = event.target.value;
      const asset = knownAssets.get(assetId) || assets.find(a => a.id === assetId) || links.find(l => l.asset_id === assetId)?.asset;
      syncLinks();
      links = links.filter(l => l.role !== 'hover_image');
      if (asset) {
        links.push({ asset, asset_id: asset.id, role: 'hover_image', variant_id: null, alt_text: '', display_order: links.length });
      }
      updateRoleSelectors();
      renderLinks();
      markDirty();
    });

    query('#catalog-clear-hover')?.addEventListener('click', () => {
      syncLinks();
      links = links.filter(l => l.role !== 'hover_image');
      updateRoleSelectors();
      renderLinks();
      markDirty();
    });
  }

  function wireRemoveVariants() {
    query('#catalog-variants')?.querySelectorAll('[data-remove-variant]').forEach(node => {
      node.onclick = () => {
        const row = node.closest('.catalog-variant');
        if (!row) return;
        if (row.dataset.variantId) {
          if (!window.confirm(`Variant #${row.dataset.variantId} is saved in catalog. Remove this variant?`)) return;
        }
        const size = row.dataset.size;
        const colorCard = row.closest('.color-group-card');
        row.remove();
        if (colorCard && size) {
          const pill = [...colorCard.querySelectorAll('.size-pill')].find(p => p.dataset.size === size);
          if (pill) {
            pill.classList.remove('is-active');
            pill.classList.add('is-inactive');
            pill.textContent = `+ ${size}`;
          }
        }
        markDirty();
      };
    });
  }
  function updateAssetChoices() {
    if (!current()) return;
    const picker = query('#catalog-attach-asset');
    if (picker) picker.innerHTML = options([['', 'Choose an asset'], ...assets.map(a => [a.id, `${a.original_name} (${a.kind})`])]);
    const prev = query('#catalog-library-prev'), next = query('#catalog-library-next');
    if (prev) prev.disabled = mediaPage === 1;
    if (next) next.disabled = mediaPage * 100 >= assetTotal;
    updateRoleSelectors();
  }
  function syncLinks() {
    query('#catalog-product-media')?.querySelectorAll('[data-link-index]').forEach(node => {
      const link = links[Number(node.dataset.linkIndex)];
      link.alt_text = node.querySelector('[name="alt_text"]').value;
      const variant = node.querySelector('[name="media_variant"]').value;
      link.variant_id = variant ? Number(variant) : null;
    });
  }
  function renderLinks() {
    const node = query('#catalog-product-media'); if (!node) return;
    node.innerHTML = links.length ? links.map((link, index) => `<article class="catalog-media-card" data-link-index="${index}">
      ${preview(link.asset)}<div><strong>${esc(link.role.replaceAll('_', ' '))}</strong>${field('alt_text', 'Alt text', link.alt_text, { max: 1000 })}
      <label>Variant association<select name="media_variant" ${link.role !== 'gallery' ? 'disabled' : ''}>${options([['', 'All variants'], ...(currentProduct.variants || []).map(v => [v.id, v.sku])], link.variant_id)}</select></label>
      <div class="media-card-actions">
        <button type="button" class="btn btn-secondary btn-icon-only" data-link-up="${index}" ${index === 0 ? 'disabled' : ''} title="Move up" aria-label="Move up">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
        </button>
        <button type="button" class="btn btn-secondary btn-icon-only" data-link-down="${index}" ${index === links.length-1 ? 'disabled' : ''} title="Move down" aria-label="Move down">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </button>
        <button type="button" class="btn btn-secondary btn-icon-only" data-link-remove="${index}" title="Detach media" aria-label="Detach media" style="color: #f87171;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      </div>
      ${link.asset.kind === 'video' ? `
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #344b3c;">
          <label>Video poster image (required for publish)
            <select name="video_poster_id" data-video-asset="${link.asset.id}">
              ${options([['', 'Choose poster image'], ...imageChoices()], link.asset.poster_id)}
            </select>
          </label>
          ${button('Save poster', '', `data-save-video-poster="${link.asset.id}" style="margin-top: 4px; padding: 4px 8px; font-size: 0.75rem;"`)}
        </div>
      ` : ''}</div></article>`).join('') : '<p>No attached media. Upload or choose from the library.</p>';

    node.querySelectorAll('[data-save-video-poster]').forEach(btn => btn.addEventListener('click', () => {
      const vidId = btn.dataset.saveVideoPoster;
      const select = node.querySelector(`[data-video-asset="${vidId}"]`);
      const posterId = select?.value || null;
      const asset = knownAssets.get(vidId) || assets.find(a => a.id === vidId) || links.find(l => l.asset_id === vidId)?.asset;
      if (!asset) return;
      action(async () => {
        await api.saveMediaPoster(vidId, { expected_version: asset.edit_version, poster_id: posterId });
        asset.poster_id = posterId;
      }, async () => {
        status('Video poster saved.');
        renderLinks();
      });
    }));

    for (const [attribute, delta] of [['linkUp', -1], ['linkDown', 1], ['linkRemove', 0]]) {
      const kebab = attribute.replace(/[A-Z]/g, x => '-' + x.toLowerCase());
      node.querySelectorAll(`[data-${kebab}]`).forEach(control => control.addEventListener('click', () => {
        syncLinks(); const index = Number(control.dataset[attribute]);
        if (!delta) links.splice(index, 1); else [links[index], links[index + delta]] = [links[index + delta], links[index]];
        renderLinks(); updateRoleSelectors(); markDirty();
        const nextIndex = delta ? index + delta : Math.min(index, links.length - 1);
        const nextControl = query('#catalog-product-media')?.querySelector(`[data-${kebab}="${nextIndex}"]`);
        if (nextControl && !nextControl.disabled) nextControl.focus();
        else query('#catalog-product-media')?.querySelector(`[data-link-remove="${nextIndex}"]`)?.focus();
      }));
    }
  }

  async function collectionList() {
    const data = await api.fetchOwnerCollections(); await loadAssets();
    if (!current()) return;
    currentCollection = null; collections = data.collections || []; context.setDirty(false);
    shell(`<div class="catalog-toolbar">${button('New collection', 'catalog-new-collection')}</div>
      <p>Deactivating a collection hides its products without deleting them.</p>
      <div class="catalog-grid">${collections.map((c, index) => `<article class="catalog-card"><h3>${esc(c.name)}</h3><p>${esc(c.slug)} · ${c.is_active ? 'Active' : 'Inactive'}</p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
          ${button('Edit collection', '', `data-edit-collection="${esc(c.id)}"`)}
          ${button('Delete', '', `data-delete-collection="${esc(c.id)}" class="btn btn-danger" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);"`)}
        </div>
        <div class="catalog-toolbar">
        ${button('Move up', '', `data-collection-move="${index}" data-delta="-1" ${index === 0 ? 'disabled' : ''}`)}
        ${button('Move down', '', `data-collection-move="${index}" data-delta="1" ${index === collections.length-1 ? 'disabled' : ''}`)}</div></article>`).join('') || '<p>No collections yet.</p>'}</div><div id="catalog-collection-editor"></div>`);
    bind('#catalog-new-collection', () => { if (context.canLeave()) collectionEditor({ is_active: true }); });
    container.querySelectorAll('[data-edit-collection]').forEach(node => node.addEventListener('click', () => { if (context.canLeave()) collectionEditor(collections.find(c => c.id === node.dataset.editCollection)); }));
    container.querySelectorAll('[data-delete-collection]').forEach(node => node.addEventListener('click', () => {
      const col = collections.find(c => c.id === node.dataset.deleteCollection);
      if (col) confirmDeleteCollection(col);
    }));
    container.querySelectorAll('[data-collection-move]').forEach(node => node.addEventListener('click', () => {
      if (!context.canLeave()) return;
      const reordered = [...collections], from = Number(node.dataset.collectionMove), to = from + Number(node.dataset.delta);
      [reordered[from], reordered[to]] = [reordered[to], reordered[from]];
      action(() => api.reorderOwnerCollections(reordered.map(c => ({ id: c.id, expected_version: c.edit_version }))), collectionList);
    }));
  }

  const confirmDeleteCollection = (col) => {
    if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
      if (!window.confirm(`Are you sure you want to delete collection "${col.name}"? Products linked to this collection will not be deleted, but will simply be unlinked from this collection.`)) {
        return;
      }
    }
    action(async () => {
      await api.deleteOwnerCollection(col.id);
    }, async () => {
      query('#catalog-collection-editor').innerHTML = '';
      await collectionList();
      status(`Collection "${col.name}" deleted.`);
    });
  };
  async function collectionEditor(collection) {
    currentCollection = collection;
    context.setDirty(false);
    let memberProducts = [];
    let unassignedProducts = [];
    if (collection.id) {
      try {
        const [memberRes, unassignedRes] = await Promise.all([
          api.fetchOwnerProducts({ collection_id: collection.id, page_size: 100 }),
          api.fetchOwnerProducts({ collection_id: 'unassigned', page_size: 100 })
        ]);
        memberProducts = memberRes.products || [];
        unassignedProducts = unassignedRes.products || [];
      } catch (err) {
        console.warn('Could not load collection products', err);
      }
    }
    const publishedCount = memberProducts.filter(p => p.status === 'published').length;

    query('#catalog-collection-editor').innerHTML = `
      <form id="catalog-collection-form">
        <h3>${collection.id ? 'Edit' : 'Create'} collection</h3>
        <div class="catalog-fields">
          ${field('name', 'Name', collection.name, { max: 200 })}
          ${field('slug', 'URL slug', collection.slug, { max: 100 })}
          ${field('description', 'Description', collection.description, { textarea: true })}
          <label>Collection banner image<select name="image_media_id">${options(imageChoices().concat(collection.image_media_id && !assets.some(a => a.id === collection.image_media_id) ? [[collection.image_media_id, 'Current saved image']] : []), collection.image_media_id)}</select></label>
          <label><input name="is_active" id="catalog-col-is-active" type="checkbox" ${collection.is_active ? 'checked' : ''}> Active collection</label>
        </div>
        <div id="catalog-col-deactivation-warning" style="display: ${!collection.is_active && publishedCount > 0 ? 'block' : 'none'}; padding: 10px 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: var(--admin-radius-sm); color: #f87171; font-size: 0.8125rem; margin-top: 8px;">
          Warning: Deactivating this collection will hide ${publishedCount} published product(s) from customer catalog listings and checkout, because published products require an active collection.
        </div>
        <div class="catalog-toolbar" style="margin-top: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
          <button type="submit" class="btn btn-primary" id="catalog-save-collection">Save collection details</button>
          ${collection.id ? button('Delete collection', 'catalog-delete-collection-btn', 'class="btn btn-danger" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);"') : ''}
          ${button('Close editor', 'catalog-close-collection')}
        </div>
      </form>
      ${collection.id ? `
        <section style="margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--admin-border-hairline);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0; font-size: 0.9375rem; font-weight: 500; color: var(--admin-text-primary);">Products in this collection (${memberProducts.length})</h4>
            ${button('Create product here', 'catalog-col-create-prod', 'class="btn btn-secondary" style="font-size: 0.8125rem; padding: 6px 12px;"')}
          </div>
          <p style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.6); margin-bottom: 12px;">
            Products can belong to multiple collections simultaneously. Adding or removing a collection preserves its SKU, variants, inventory, and order history.
          </p>

          <div class="catalog-toolbar" style="margin-bottom: 16px; padding: 12px; background: #101713; border: 1px solid #2d3e33; border-radius: 6px;">
            <label style="flex: 1; min-width: 220px;">Add existing unassigned product:
              <select id="catalog-col-add-prod-select">
                ${options([['', unassignedProducts.length ? 'Choose unassigned product...' : 'No unassigned drafts available'], ...unassignedProducts.map(p => [p.id, `${p.title || 'Untitled'} (${p.status})`])])}
              </select>
            </label>
            ${button('Add to collection', 'catalog-col-add-prod-btn', unassignedProducts.length ? '' : 'disabled')}
          </div>

          <div class="collection-members-list">
            ${memberProducts.length ? memberProducts.map(p => `
              <div class="collection-member-item" data-product-id="${p.id}">
                <div>
                  <span class="collection-member-title">${esc(p.title || 'Untitled draft')}</span>
                  <span class="collection-member-status status-${esc(p.status)}">${esc(p.status)}</span>
                  <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">
                    slug: ${esc(p.slug || 'no-slug')} · ${p.variants?.length || 0} variant(s)
                  </div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                  ${button('Open', '', `data-open-member-prod="${p.id}" style="padding: 4px 8px; font-size: 0.75rem;"`)}
                  <select data-move-target="${p.id}" style="padding: 4px 8px; font-size: 0.75rem; background: #141715; color: #FFF; border: 1px solid #486352; border-radius: 4px;">
                    ${options([['', 'Move to other collection...'], ['__unassign__', 'Unassign (Choose later)'], ...collections.filter(c => c.id !== collection.id).map(c => [c.id, c.name])])}
                  </select>
                  ${button('Move', '', `data-move-member-prod="${p.id}" style="padding: 4px 8px; font-size: 0.75rem;"`)}
                </div>
              </div>
            `).join('') : '<p style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem;">No products in this collection yet.</p>'}
          </div>
        </section>
      ` : ''}
    `;

    const form = query('#catalog-collection-form'); wireDirty(form); form.querySelector('[name="name"]').focus();
    bind('#catalog-close-collection', () => { if (context.canLeave()) { query('#catalog-collection-editor').innerHTML = ''; context.setDirty(false); } });
    bind('#catalog-delete-collection-btn', () => { confirmDeleteCollection(collection); });

    query('#catalog-col-is-active')?.addEventListener('change', event => {
      const warning = query('#catalog-col-deactivation-warning');
      if (warning) warning.style.display = (!event.target.checked && publishedCount > 0) ? 'block' : 'none';
      markDirty();
    });

    bind('#catalog-col-create-prod', () => {
      if (!context.canLeave()) return;
      action(async () => {
        const newProd = await api.createOwnerProduct({ collection_id: collection.id });
        return newProd;
      }, p => editProduct(p));
    });

    bind('#catalog-col-add-prod-btn', () => {
      const prodId = query('#catalog-col-add-prod-select')?.value;
      const targetProd = unassignedProducts.find(p => p.id === prodId);
      if (!targetProd) return;
      const existingCols = targetProd.collection_ids || (targetProd.collection_id ? [targetProd.collection_id] : []);
      const nextCols = [...new Set([...existingCols, collection.id])];
      action(() => api.updateOwnerProduct(targetProd.id, {
        expected_version: targetProd.edit_version,
        collection_ids: nextCols,
        collection_id: nextCols[0] || null,
      }), async () => {
        await collectionEditor(collection);
        status(`Product "${targetProd.title || 'Untitled'}" added to collection.`);
      });
    });

    container.querySelectorAll('[data-open-member-prod]').forEach(btn => btn.addEventListener('click', () => {
      if (!context.canLeave()) return;
      action(() => api.fetchOwnerProduct(btn.dataset.openMemberProd), p => editProduct(p));
    }));

    container.querySelectorAll('[data-move-member-prod]').forEach(btn => btn.addEventListener('click', () => {
      const prodId = btn.dataset.moveMemberProd;
      const select = container.querySelector(`[data-move-target="${prodId}"]`);
      const targetColId = select?.value;
      if (!targetColId) {
        status('Select a destination collection or Unassign.', true);
        return;
      }
      const prod = memberProducts.find(p => p.id === prodId);
      if (!prod) return;
      const existingCols = prod.collection_ids || (prod.collection_id ? [prod.collection_id] : []);
      let nextCols;
      if (targetColId === '__unassign__') {
        nextCols = existingCols.filter(id => id !== collection.id);
      } else {
        nextCols = [...new Set([...existingCols.filter(id => id !== collection.id), targetColId])];
      }
      action(() => api.updateOwnerProduct(prod.id, {
        expected_version: prod.edit_version,
        collection_ids: nextCols,
        collection_id: nextCols[0] || null,
      }), async () => {
        await collectionEditor(collection);
        status(`Product collection updated.`);
      });
    }));

    form.addEventListener('submit', event => {
      event.preventDefault();
      action(async () => {
        const fields = { name: value(form, 'name').trim(), slug: value(form, 'slug').trim(), description: value(form, 'description').trim() || null, is_active: form.querySelector('[name="is_active"]').checked };
        if (!fields.name || !fields.slug) throw new Error('Enter a collection name and slug.');
        fields.image_media_id = value(form, 'image_media_id') || null;
        return currentCollection.id ? api.updateOwnerCollection(currentCollection.id, { ...fields, expected_version: currentCollection.edit_version }) : api.createOwnerCollection(fields);
      }, async () => { await collectionList(); status('Collection saved.'); });
    });
  }

  function mountUploadBox(onAccepted) {
    const box = query('#catalog-upload-box'); if (!box) return;
    box.innerHTML = `
      <div class="custom-file-upload-wrap">
        <label class="custom-file-upload-box" for="catalog-file-input" tabindex="0">
          <svg class="upload-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <div class="upload-text-group">
            <span class="upload-main-title">Click to choose image or video files</span>
            <span class="upload-sub-desc">JPEG, PNG, WebP (up to 10 MB) · MP4, WebM (up to 100 MB)</span>
          </div>
          <input type="file" id="catalog-file-input" class="visually-hidden-file-input" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" multiple>
        </label>
      </div>
      <div id="catalog-upload-queue"></div>`;
    const uploadBoxLabel = box.querySelector('.custom-file-upload-box');
    uploadBoxLabel?.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        query('#catalog-file-input')?.click();
      }
    });
    query('#catalog-file-input').addEventListener('change', event => {
      const files = [...(event.target.files || [])]; event.target.value = '';
      for (const file of files) {
        let url = '';
        try { url = URL.createObjectURL(file); objectUrls.add(url); } catch {}
        queue.push({ file, url, state: 'queued', progress: 0, controller: null, message: '' });
      }
      if (files.length) markDirty();
      renderQueue(); processQueue(onAccepted);
    });
    renderQueue();
  }
  function renderQueue() {
    const node = query('#catalog-upload-queue'); if (!node || !current()) return;
    node.innerHTML = queue.map((item, index) => `<article class="catalog-upload-row">${item.asset ? preview(item.asset) : item.url ? (item.file.type.startsWith('video/') ? `<video controls preload="metadata" src="${esc(item.url)}" aria-label="Local video preview"></video>` : `<img src="${esc(item.url)}" alt="Local preview of ${esc(item.file.name)}">`) : ''}<span>${esc(item.file.name)}</span><progress max="100" value="${item.progress}" aria-label="Upload ${esc(item.file.name)}"></progress>
      <span>${esc(item.state === 'uploading' && item.progress === 100 ? 'Validating on server…' : item.state)} ${esc(item.message)}</span>
      ${['queued', 'uploading'].includes(item.state) ? button('Cancel upload', '', `data-upload-cancel="${index}"`) : ''}
      ${['failed', 'canceled'].includes(item.state) ? button('Retry upload', '', `data-upload-retry="${index}"`) : ''}</article>`).join('');
    node.querySelectorAll('[data-upload-cancel]').forEach(control => control.addEventListener('click', () => {
      const item = queue[Number(control.dataset.uploadCancel)];
      if (item.asset) return;
      item.state = 'canceled'; item.controller?.abort();
      if (item.url) { URL.revokeObjectURL(item.url); objectUrls.delete(item.url); item.url = ''; }
      renderQueue();
    }));
    node.querySelectorAll('[data-upload-retry]').forEach(control => control.addEventListener('click', () => {
      const item = queue[Number(control.dataset.uploadRetry)]; item.state = 'queued'; item.progress = 0; item.message = ''; renderQueue(); processQueue();
    }));
  }
  let afterUpload = null;
  async function processQueue(onAccepted) {
    if (onAccepted) afterUpload = onAccepted;
    if (uploading) return;
    uploading = true;
    try {
      while (current()) {
        const item = queue.find(x => x.state === 'queued'); if (!item) break;
        const limit = item.file.type.startsWith('image/') ? 10 * 1024 * 1024 : 100 * 1024 * 1024;
        if (!['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/webm'].includes(item.file.type) || !item.file.size || item.file.size > limit) {
          item.state = 'failed'; item.message = 'Choose a supported nonempty file within its size limit.'; renderQueue(); continue;
        }
        item.controller = new AbortController(); controllers.add(item.controller); item.state = 'uploading'; renderQueue();
        try {
          const accepted = await api.uploadOwnerMedia(item.file, { signal: item.controller.signal, onProgress: percent => { item.progress = percent; renderQueue(); } });
          item.state = 'accepted'; item.progress = 100; item.message = 'Saved in library'; item.asset = accepted;
          renderQueue();
          if (item.url) { URL.revokeObjectURL(item.url); objectUrls.delete(item.url); item.url = ''; }
          if (current()) {
            try { await afterUpload?.(accepted); }
            catch (error) { status(`File was accepted. Library refresh failed: ${error.message}`, true); }
          }
        } catch (error) { item.state = error.name === 'AbortError' ? 'canceled' : 'failed'; item.message = catalogError(error); }
        finally { controllers.delete(item.controller); item.controller = null; renderQueue(); }
      }
    } finally { uploading = false; if (current() && section === 'media' && queue.every(item => item.state === 'accepted')) context.setDirty(posterDrafts.size > 0); }
  }

  async function mediaLibrary() {
    await loadAssets(); if (!current()) return;
    shell(`<p>Public catalog files only. Payment evidence belongs to orders and must not be uploaded here.</p><div id="catalog-upload-box"></div><div id="catalog-library-cards"></div>
      <div class="catalog-toolbar">${button('Previous', 'catalog-media-prev', mediaPage === 1 ? 'disabled' : '')}<span>Page ${mediaPage} · ${assetTotal} files</span>${button('Next', 'catalog-media-next', mediaPage * 100 >= assetTotal ? 'disabled' : '')}</div>`);
    mountUploadBox(async () => { await loadAssets(); renderLibraryCards(); }); renderLibraryCards();
    bind('#catalog-media-prev', () => { if (context.canLeave()) { mediaPage--; action(mediaLibrary); } });
    bind('#catalog-media-next', () => { if (context.canLeave()) { mediaPage++; action(mediaLibrary); } });
  }
  function renderLibraryCards() {
    const node = query('#catalog-library-cards'); if (!node || !current()) return;
    node.innerHTML = `<div class="catalog-grid">${assets.map(asset => `<article class="catalog-card" data-library-asset="${asset.id}">${preview(asset)}<h3>${esc(asset.original_name)}</h3>
      <p>${asset.width} × ${asset.height} · ${(asset.byte_size / 1024 / 1024).toFixed(2)} MiB${asset.duration_ms ? ` · ${(asset.duration_ms / 1000).toFixed(1)} seconds` : ''}</p>
      <p>Usage: ${asset.usage?.products?.length || 0} product roles, ${asset.usage?.collections?.length || 0} collections, ${asset.usage?.posters_for?.length || 0} posters.</p>
      ${asset.usage?.products?.map(x => `<p>${esc(x.product_title || 'Product')} · ${esc(x.role.replaceAll('_', ' '))}${x.variant_id ? ' · variant image' : ''}</p>`).join('') || ''}
      ${asset.kind === 'video' ? `<label>Poster image<select name="poster_id">${options(imageChoices(), posterDrafts.has(asset.id) ? posterDrafts.get(asset.id) : asset.poster_id)}</select></label>${button('Save poster', '', `data-save-poster="${asset.id}"`)}` : ''}
      ${button('Delete unused file', '', `data-delete-asset="${asset.id}"`)}</article>`).join('') || '<p>No files uploaded yet.</p>'}</div>`;
    node.querySelectorAll('[data-save-poster]').forEach(control => control.addEventListener('click', () => {
      const asset = assets.find(a => a.id === control.dataset.savePoster), card = control.closest('[data-library-asset]');
      action(() => api.saveMediaPoster(asset.id, { expected_version: asset.edit_version, poster_id: card.querySelector('[name="poster_id"]').value || null }), async () => { posterDrafts.delete(asset.id); await loadAssets(); renderLibraryCards(); status('Video poster saved.'); context.setDirty(posterDrafts.size > 0); });
    }));
    node.querySelectorAll('[name="poster_id"]').forEach(control => control.addEventListener('change', () => {
      posterDrafts.set(control.closest('[data-library-asset]').dataset.libraryAsset, control.value); markDirty();
    }));
    node.querySelectorAll('[data-delete-asset]').forEach(control => control.addEventListener('click', () => {
      const asset = assets.find(a => a.id === control.dataset.deleteAsset);
      if (!window.confirm('Delete this unused public file? Attached files cannot be deleted.')) return;
      action(() => api.deleteOwnerMedia(asset.id, asset.edit_version), async () => { knownAssets.delete(asset.id); posterDrafts.delete(asset.id); await loadAssets(); renderLibraryCards(); status('Unused file deleted.'); });
    }));
  }

  async function heroPlaylist() {
    await loadAssets();
    if (!current()) return;
    let slides = [];
    let allProds = [];
    let allCols = [];
    try {
      const [slidesRes, prodsRes, colsRes] = await Promise.all([
        api.fetchAdminHeroSlides(),
        api.fetchOwnerProducts({ page_size: 100 }),
        api.fetchOwnerCollections(),
      ]);
      slides = slidesRes.slides || [];
      allProds = prodsRes.products || [];
      allCols = colsRes.collections || [];
    } catch (err) {
      status(catalogError(err), true);
    }
    if (!current()) return;
    context.setDirty(false);

    shell(`
      <div class="catalog-toolbar">
        ${button('Add hero slide', 'catalog-new-hero-slide', 'class="btn btn-primary"')}
        ${button('Reload playlist', 'catalog-reload-hero')}
      </div>

      <div class="hero-guidelines-card" style="margin: 16px 0 20px 0; padding: 18px 20px; background: var(--admin-bg-card); border: 1px solid var(--admin-border-hairline); border-radius: var(--admin-radius-card); color: var(--admin-text-primary);">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
          <strong style="font-size: 0.9375rem; font-weight: 500; color: var(--admin-text-primary);">Homepage hero video & picture showcase specifications</strong>
        </div>
        <p style="margin: 0 0 12px 0; font-size: 0.8125rem; line-height: 1.5; color: var(--admin-text-secondary);">
          The Hero section plays an ambient, atmospheric background video full-bleed behind a subtle blur and vignette, while featured product pictures scroll horizontally in front without text clutter.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 0.8125rem;">
          <div style="background: var(--admin-bg-raised); padding: 10px 14px; border-radius: var(--admin-radius-control); border: 1px solid var(--admin-border-hairline);">
            <strong style="color: var(--admin-text-primary); display: block; margin-bottom: 4px; font-weight: 500;">Dimensions & breadth</strong>
            <span style="color: var(--admin-text-secondary);"><strong>1920 × 1080 px</strong> (16:9 Full HD) or <strong>2560 × 1440 px</strong> (2K). Keep central subject in the middle 60% of frame for flawless mobile cropping.</span>
          </div>
          <div style="background: var(--admin-bg-raised); padding: 10px 14px; border-radius: var(--admin-radius-control); border: 1px solid var(--admin-border-hairline);">
            <strong style="color: var(--admin-text-primary); display: block; margin-bottom: 4px; font-weight: 500;">Duration & length</strong>
            <span style="color: var(--admin-text-secondary);"><strong>10 to 30 seconds</strong> seamless ambient loop. Avoid jarring camera cuts; prefer slow pans, model motion, or fabric drape.</span>
          </div>
          <div style="background: var(--admin-bg-raised); padding: 10px 14px; border-radius: var(--admin-radius-control); border: 1px solid var(--admin-border-hairline);">
            <strong style="color: var(--admin-text-primary); display: block; margin-bottom: 4px; font-weight: 500;">File size & codec</strong>
            <span style="color: var(--admin-text-secondary);">Under <strong>15 MB</strong> (max 25 MB). Format: <strong>MP4 (H.264 video, muted / no audio)</strong> for instant autoplay without buffering.</span>
          </div>
          <div style="background: var(--admin-bg-raised); padding: 10px 14px; border-radius: var(--admin-radius-control); border: 1px solid var(--admin-border-hairline);">
            <strong style="color: var(--admin-text-primary); display: block; margin-bottom: 4px; font-weight: 500;">Featured pictures strip</strong>
            <span style="color: var(--admin-text-secondary);">Active slides with images and products marked "Featured in hero" scroll horizontally. Hovering pauses scroll; clicking lands on the product page.</span>
          </div>
        </div>
      </div>

      <div id="catalog-hero-editor" style="margin-bottom: 20px;"></div>
      <div id="catalog-hero-slides"></div>
    `);

    function renderSlideList() {
      const containerNode = query('#catalog-hero-slides');
      if (!containerNode || !current()) return;
      if (!slides.length) {
        containerNode.innerHTML = `<div class="admin-empty-state"><p>No hero slides configured. Click "Add new hero slide" to create one.</p></div>`;
        return;
      }
      containerNode.innerHTML = slides.map((slide, index) => {
        const dest = slide.product ? `Product: ${esc(slide.product.title)}` : slide.collection ? `Collection: ${esc(slide.collection.name)}` : 'None (Brand slide)';
        const mediaPreview = slide.video_url
          ? `<video preload="metadata" muted playsinline src="${esc(sanitizeMediaUrl(slide.video_url, ''))}" ${slide.poster_url ? `poster="${esc(sanitizeMediaUrl(slide.poster_url))}"` : ''} class="hero-slide-preview"></video>`
          : slide.image_url
            ? `<img src="${esc(sanitizeMediaUrl(slide.image_url))}" class="hero-slide-preview" alt="Slide preview">`
            : `<div class="hero-slide-preview" style="display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.4);">No media</div>`;
        return `
          <article class="hero-slide-card" data-slide-id="${slide.id}">
            <div>${mediaPreview}</div>
            <div class="hero-slide-info">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                <strong style="font-size: 1rem; color: #FFF;">Slide #${index + 1}: ${esc(slide.title || 'Untitled slide')}</strong>
                <span class="hero-slide-badge ${slide.is_enabled ? 'hero-badge-enabled' : 'hero-badge-disabled'}">
                  ${slide.is_enabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              ${slide.benefit ? `<p style="margin: 0; font-size: 0.85rem; color: #38BDF8;">${esc(slide.benefit)}</p>` : ''}
              <p style="margin: 0; font-size: 0.75rem; color: rgba(255,255,255,0.5);">Destination: ${dest}</p>
              <div class="catalog-toolbar" style="margin-top: auto; padding-top: 8px;">
                ${button('Move up', '', `data-slide-up="${index}" ${index === 0 ? 'disabled' : ''}`)}
                ${button('Move down', '', `data-slide-down="${index}" ${index === slides.length - 1 ? 'disabled' : ''}`)}
                ${button(slide.is_enabled ? 'Disable' : 'Enable', '', `data-slide-toggle="${slide.id}"`)}
                ${button('Edit', '', `data-slide-edit="${slide.id}"`)}
                ${button('Delete', '', `data-slide-delete="${slide.id}"`)}
              </div>
            </div>
          </article>
        `;
      }).join('');

      containerNode.querySelectorAll('[data-slide-up]').forEach(btn => btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.slideUp);
        if (idx <= 0) return;
        const reordered = [...slides];
        [reordered[idx], reordered[idx - 1]] = [reordered[idx - 1], reordered[idx]];
        action(() => api.reorderAdminHeroSlides({ expected_version: 1, slide_ids: reordered.map(s => s.id) }), updated => {
          slides = updated.slides || reordered;
          renderSlideList();
          status('Slide reordered.');
        });
      }));

      containerNode.querySelectorAll('[data-slide-down]').forEach(btn => btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.slideDown);
        if (idx >= slides.length - 1) return;
        const reordered = [...slides];
        [reordered[idx], reordered[idx + 1]] = [reordered[idx + 1], reordered[idx]];
        action(() => api.reorderAdminHeroSlides({ expected_version: 1, slide_ids: reordered.map(s => s.id) }), updated => {
          slides = updated.slides || reordered;
          renderSlideList();
          status('Slide reordered.');
        });
      }));

      containerNode.querySelectorAll('[data-slide-toggle]').forEach(btn => btn.addEventListener('click', () => {
        const slide = slides.find(s => s.id === btn.dataset.slideToggle);
        if (!slide) return;
        action(() => api.updateAdminHeroSlide(slide.id, { expected_version: slide.edit_version, is_enabled: !slide.is_enabled }), updated => {
          const idx = slides.findIndex(s => s.id === slide.id);
          if (idx !== -1) slides[idx] = updated;
          renderSlideList();
          status(`Slide ${updated.is_enabled ? 'enabled' : 'disabled'}.`);
        });
      }));

      containerNode.querySelectorAll('[data-slide-edit]').forEach(btn => btn.addEventListener('click', () => {
        const slide = slides.find(s => s.id === btn.dataset.slideEdit);
        if (slide) renderSlideEditor(slide);
      }));

      containerNode.querySelectorAll('[data-slide-delete]').forEach(btn => btn.addEventListener('click', () => {
        const slide = slides.find(s => s.id === btn.dataset.slideDelete);
        if (!slide) return;
        if (!window.confirm(`Delete hero slide "${slide.title || 'Untitled'}"?`)) return;
        action(() => api.deleteAdminHeroSlide(slide.id, slide.edit_version), () => {
          slides = slides.filter(s => s.id !== slide.id);
          renderSlideList();
          status('Hero slide deleted.');
        });
      }));
    }

    function renderSlideEditor(slide = null) {
      const editorNode = query('#catalog-hero-editor');
      if (!editorNode) return;
      const isNew = !slide;
      const videoAssets = [...knownAssets.values()].filter(a => a.kind === 'video');
      const imageAssets = [...knownAssets.values()].filter(a => a.kind === 'image');

      editorNode.innerHTML = `
        <form id="catalog-hero-form" style="padding: 16px; background: #101713; border: 1px solid #40574a; border-radius: 8px; margin-bottom: 20px;">
          <h3 style="margin-top: 0;">${isNew ? 'Create New Hero Slide' : 'Edit Hero Slide'}</h3>
          <div class="catalog-fields">
            ${field('title', 'Slide Title', slide?.title || '', { max: 200 })}
            ${field('benefit', 'Benefit / Headline', slide?.benefit || '', { textarea: true, max: 2000 })}
            <label>Background video asset (plays continuously & blurred behind hero)
              <select name="video_asset_id">
                ${options([['', 'None (image slide)'], ...videoAssets.map(a => [a.id, `${a.original_name} (${(a.byte_size / 1024 / 1024).toFixed(1)} MiB)`])], slide?.video_asset_id)}
              </select>
            </label>
            <label>Video poster image (instant background display & product card image)
              <select name="poster_asset_id">
                ${options([['', 'Choose poster image'], ...imageAssets.map(a => [a.id, a.original_name])], slide?.poster_asset_id)}
              </select>
            </label>
            <label>Image asset (for image-only featured cards)
              <select name="image_asset_id">
                ${options([['', 'None (use video above)'], ...imageAssets.map(a => [a.id, a.original_name])], slide?.image_asset_id)}
              </select>
            </label>
            <label>Destination product (clicking featured image navigates here)
              <select name="target_product_id">
                ${options([['', 'None (no product link)'], ...allProds.map(p => [p.id, `${p.title || 'Untitled'} (${p.status})`])], slide?.target_product_id)}
              </select>
            </label>
            <label>Destination collection (optional click target)
              <select name="target_collection_id">
                ${options([['', 'None (no collection link)'], ...allCols.map(c => [c.id, c.name])], slide?.target_collection_id)}
              </select>
            </label>
            <label><input name="is_enabled" type="checkbox" ${slide ? (slide.is_enabled ? 'checked' : '') : 'checked'}> Enabled in active carousel</label>
          </div>
          <div class="catalog-toolbar" style="margin-top: 14px;">
            <button type="submit" class="btn btn-primary" id="catalog-save-hero-slide">${isNew ? 'Add Slide' : 'Save Slide'}</button>
            ${button('Cancel', 'catalog-cancel-hero-slide')}
          </div>
        </form>
      `;

      bind('#catalog-cancel-hero-slide', () => {
        editorNode.innerHTML = '';
      });

      const form = query('#catalog-hero-form');
      form.addEventListener('submit', event => {
        event.preventDefault();
        action(async () => {
          const payload = {
            title: value(form, 'title').trim() || null,
            benefit: value(form, 'benefit').trim() || null,
            video_asset_id: value(form, 'video_asset_id') || null,
            poster_asset_id: value(form, 'poster_asset_id') || null,
            image_asset_id: value(form, 'image_asset_id') || null,
            target_product_id: value(form, 'target_product_id') || null,
            target_collection_id: value(form, 'target_collection_id') || null,
            is_enabled: form.querySelector('[name="is_enabled"]').checked,
          };
          if (!payload.video_asset_id && !payload.poster_asset_id && !payload.image_asset_id) {
            throw new Error('Hero slide requires either a video asset with poster or an image asset.');
          }
          if (payload.video_asset_id && !payload.poster_asset_id) {
            const vidAsset = knownAssets.get(payload.video_asset_id);
            if (!vidAsset?.poster_id) {
              throw new Error('Featured hero video requires an image poster.');
            }
          }
          if (isNew) {
            const created = await api.createAdminHeroSlide(payload);
            slides.push(created);
          } else {
            const updated = await api.updateAdminHeroSlide(slide.id, { ...payload, expected_version: slide.edit_version });
            const idx = slides.findIndex(s => s.id === slide.id);
            if (idx !== -1) slides[idx] = updated;
          }
        }, () => {
          editorNode.innerHTML = '';
          renderSlideList();
          status(`Hero slide ${isNew ? 'created' : 'saved'}.`);
        });
      });
    }

    renderSlideList();
    bind('#catalog-new-hero-slide', () => renderSlideEditor(null));
    bind('#catalog-reload-hero', () => action(heroPlaylist));
  }

  const ready = section === 'products' ? products() : section === 'collections' ? collectionList() : section === 'hero' ? heroPlaylist() : mediaLibrary();
  return { ready, destroy() { alive = false; stockViews.forEach(v => v.destroy()); controllers.forEach(c => c.abort()); objectUrls.forEach(url => URL.revokeObjectURL(url)); objectUrls.clear(); } };
}
