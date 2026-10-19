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
  const sku = value('sku');
  if (!sku) throw new Error('Every saved variant needs a unique SKU. Remove an unfinished new row to save a draft without it.');
  const is_active = row.querySelector('[name="variant_active"]').checked;
  if (is_active && price_minor === null) throw new Error('Enter a price before activating this variant.');
  return { ...(row.dataset.variantId ? { id: Number(row.dataset.variantId) } : {}), sku,
    size: value('size') || null, color: value('color') || null, price_minor, is_active, availability: value('availability') };
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
    const [data, categories] = await Promise.all([api.fetchOwnerProducts({ ...productFilter, page: productsPage }), api.fetchOwnerCollections()]);
    if (!current()) return;
    currentProduct = null; collections = categories.collections || []; context.setDirty(false);
    shell(`<div class="catalog-toolbar">${button('New draft', 'catalog-new-product')}</div>
      <form id="catalog-search" class="catalog-toolbar">
        <label>Search title, slug or SKU<input name="search" value="${esc(productFilter.search)}" maxlength="200"></label>
        <label>Status<select name="status">${options([['', 'All statuses'], ['draft', 'Draft'], ['published', 'Published'], ['archived', 'Archived']], productFilter.status)}</select></label>
        <label>Collection<select name="collection_id">${options([['', 'All collections'], ...collections.map(c => [c.id, c.name])], productFilter.collection_id)}</select></label>
        <button class="btn btn-secondary" type="submit">Apply filters</button></form>
      <p>${data.total || 0} products. Drafts are private in catalog listings; uploaded asset URLs are public.</p>
      ${(data.products || []).length ? `<div class="catalog-grid">${data.products.map(p => `<article class="catalog-card"><h3>${esc(p.title || 'Untitled draft')}</h3>
        <p>${esc(p.status)} · ${esc(p.slug || 'No slug')} · ${p.variants?.length || 0} variants</p>${button('Edit product', '', `data-edit-product="${esc(p.id)}"`)}</article>`).join('')}</div>`
        : '<p>No products match. Create your first draft to begin.</p>'}
      <div class="catalog-toolbar">${button('Previous', 'catalog-products-prev', productsPage === 1 ? 'disabled' : '')}<span>Page ${productsPage}</span>
        ${button('Next', 'catalog-products-next', productsPage * 20 >= (data.total || 0) ? 'disabled' : '')}</div>`);
    bind('#catalog-new-product', () => action(() => api.createOwnerProduct(), product => editProduct(product)));
    container.querySelectorAll('[data-edit-product]').forEach(node => node.addEventListener('click', () => action(() => api.fetchOwnerProduct(node.dataset.editProduct), p => editProduct(p))));
    query('#catalog-search').addEventListener('submit', event => { event.preventDefault(); productFilter = Object.fromEntries(['search', 'status', 'collection_id'].map(n => [n, value(event.target, n)])); productsPage = 1; action(products); });
    bind('#catalog-products-prev', () => { productsPage--; action(products); });
    bind('#catalog-products-next', () => { productsPage++; action(products); });
  }

  function variantMarkup(v, index) {
    const price = v.price_minor === null || v.price_minor === undefined ? '' : `${Math.floor(v.price_minor / 100)}.${String(v.price_minor % 100).padStart(2, '0')}`;
    return `<fieldset class="catalog-variant" ${v.id ? `data-variant-id="${v.id}"` : ''}>
      <legend>Variant ${index + 1}${v.id ? ` · #${v.id}` : ' · new'}</legend><div class="catalog-fields">
      ${field('sku', 'SKU (required to save this row)', v.sku, { max: 100 })}${field('size', 'Size (optional)', v.size, { max: 50 })}${field('color', 'Color (optional)', v.color, { max: 100 })}
      ${field('price', 'Retail price PKR', price, { max: 20 })}
      <label>Owner availability<select name="availability">${options([['unknown', 'Unknown'], ['available', 'Available'], ['unavailable', 'Unavailable']], v.availability || 'unknown')}</select></label>
      <label><input name="variant_active" type="checkbox" ${v.is_active ? 'checked' : ''}> Active variant</label></div>
      ${v.id ? '<p>Deactivate to stop future sales. Existing stock and order history are retained.</p>' : button('Remove unfinished row', '', 'data-remove-variant')}
      ${v.id ? `<div data-variant-stock="${v.id}"></div>` : ''}</fieldset>`;
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
    shell(`<div class="catalog-toolbar">${button('Back to products', 'catalog-back-products')}${button('Reload saved product', 'catalog-reload-product')}
      <strong id="catalog-product-state">${esc(product.status)} · version ${product.edit_version}</strong></div>
      <form id="catalog-product-form"><fieldset ${archived ? 'disabled' : ''}><legend>Product details</legend><div class="catalog-fields">
      ${field('title', 'Title', product.title, { max: 300 })}${field('slug', 'URL slug', product.slug, { max: 100 })}
      <label>Collection<select name="collection_id">${options([['', 'Choose later'], ...collections.map(c => [c.id, c.name + (c.is_active ? '' : ' (inactive)')])], product.collection_id)}</select></label>
      <div class="stock-responsibility-box" style="grid-column: 1 / -1; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; margin: 8px 0;">
        <label style="font-weight: 600; display: block; margin-bottom: 8px; color: #f8fafc;">Who manages this product's stock?</label>
        <div style="display: flex; gap: 24px; margin-bottom: 12px; flex-wrap: wrap;">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #cbd5e1;">
            <input type="radio" name="stock_management_source" value="alphazee_managed" ${(product.stock_management_source || 'alphazee_managed') === 'alphazee_managed' ? 'checked' : ''} id="source-alphazee">
            <span><strong>AlphaZee — no external vendor</strong></span>
          </label>
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #cbd5e1;">
            <input type="radio" name="stock_management_source" value="vendor_managed" ${product.stock_management_source === 'vendor_managed' ? 'checked' : ''} id="source-vendor">
            <span><strong>Vendor — choose an active shop</strong></span>
          </label>
        </div>
        <div id="vendor-selection-wrapper" style="display: ${product.stock_management_source === 'vendor_managed' ? 'block' : 'none'}; margin-top: 10px;">
          <label style="display: block; margin-bottom: 4px; color: #cbd5e1;">Assigned Vendor Shop
            <select name="vendor_id" id="catalog-vendor-id" style="width: 100%; max-width: 400px; padding: 8px; border-radius: 4px; border: 1px solid #475569; background: #1e293b; color: #fff;">
              <option value="">-- Choose active vendor shop --</option>
              ${vendorOptions}
            </select>
          </label>
        </div>
        <p style="font-size: 0.85rem; color: #94a3b8; margin: 8px 0 0 0;">
          Vendor users can update allocated quantities only; AlphaZee controls product pricing, media, publishing, and customer orders.
        </p>
      </div>
      ${field('badge', 'Card badge', product.badge, { max: 100 })}${field('short_description', 'Short description', product.short_description, { textarea: true, max: 2000 })}
      ${field('description', 'Customer description', product.description, { textarea: true, max: 20000 })}
      ${field('material', 'Material', product.material, { textarea: true })}${field('care', 'Care instructions', product.care, { textarea: true })}${field('sizing', 'Sizing details', product.sizing, { textarea: true })}
      <label><input name="is_hero" type="checkbox" ${product.is_hero ? 'checked' : ''}> Featured in hero</label>
      ${field('hero_order', 'Hero order', product.hero_order, { type: 'number' })}${field('hero_benefit', 'Hero benefit', product.hero_benefit, { textarea: true, max: 2000 })}</div>
      <h3>Variants</h3><p>A product without size/color options uses one default variant. Blank prices remain unset.</p>
      <div id="catalog-variants">${(product.variants || []).map(variantMarkup).join('')}</div>${button('Add variant', 'catalog-add-variant')}

      <h3>Storefront Card Images</h3>
      <p>Explicitly select the Card Front image and Card Hover/Back image shown in listings and grids. These selections are independent of gallery order.</p>
      <div class="role-selector-grid">
        <div class="role-selector-card" id="card-front-selector-card">
          <div class="role-thumbnail" id="card-front-thumb">No front image</div>
          <div class="role-selector-info">
            <strong>Card Front Image (Primary)</strong>
            <p>Main product image displayed on category pages, search results, and hero.</p>
            <label>Select front image:
              <select id="catalog-select-front"></select>
            </label>
            <button type="button" class="btn btn-secondary" id="catalog-clear-front" style="font-size: 0.75rem; padding: 4px 8px; align-self: start;">Clear front image</button>
          </div>
        </div>
        <div class="role-selector-card" id="card-hover-selector-card">
          <div class="role-thumbnail" id="card-hover-thumb">No hover image</div>
          <div class="role-selector-info">
            <strong>Card Hover / Back Image</strong>
            <p>Revealed on desktop cursor hover. Defaults to front image if unset.</p>
            <label>Select hover image:
              <select id="catalog-select-hover"></select>
            </label>
            <button type="button" class="btn btn-secondary" id="catalog-clear-hover" style="font-size: 0.75rem; padding: 4px 8px; align-self: start;">Clear hover image</button>
          </div>
        </div>
      </div>

      <h3>Product gallery and featured media</h3><p>Uploaded files are public resources. Detaching keeps the file in the library.</p>
      <div id="catalog-product-media"></div>
      <div class="catalog-toolbar"><label>Library asset<select id="catalog-attach-asset">${options([['', 'Choose an asset'], ...assets.map(a => [a.id, `${a.original_name} (${a.kind})`])])}</select></label>
        <label>Presentation role<select id="catalog-attach-role">${options([['gallery', 'Gallery'], ['primary', 'Primary image (card front)'], ['hover_image', 'Hover image (card back)'], ['hero_image', 'Hero image'], ['hero_video', 'Hero video'], ['hero_poster', 'Hero poster']])}</select></label>${button('Attach asset', 'catalog-attach')}
        ${button('Previous library page', 'catalog-library-prev', mediaPage === 1 ? 'disabled' : '')}${button('Next library page', 'catalog-library-next', mediaPage * 100 >= assetTotal ? 'disabled' : '')}</div>
      <div id="catalog-upload-box"></div><button type="submit" class="btn btn-primary" id="catalog-save-product">Save product and media</button></fieldset></form>
      <section><h3>Publication requirements</h3><ul id="catalog-requirements"></ul><div class="catalog-toolbar">
        ${!archived ? button(product.status === 'published' ? 'Unpublish' : 'Publish', 'catalog-publish') + button('Archive', 'catalog-archive') : button('Restore to draft', 'catalog-restore')}</div></section>`);
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
      markDirty();
    };
    sourceAlphazee?.addEventListener('change', updateVendorVisibility);
    sourceVendor?.addEventListener('change', updateVendorVisibility);
    bind('#catalog-back-products', () => { if (context.canLeave()) action(products); });
    bind('#catalog-reload-product', () => { if (context.canLeave()) action(() => api.fetchOwnerProduct(product.id), p => editProduct(p)); });
    bind('#catalog-add-variant', () => {
      const node = document.createElement('div'); node.innerHTML = variantMarkup({}, query('#catalog-variants').children.length);
      query('#catalog-variants').appendChild(node.firstElementChild || node); wireRemoveVariants(); markDirty();
    });
    wireRemoveVariants();
    let supplierRequest;
    const suppliers = () => {
      // Refresh after creation, and share concurrent initial reads between variants.
      if (!supplierRequest) supplierRequest = api.fetchAdminSuppliers().finally(() => { supplierRequest = null; });
      return supplierRequest;
    };
    for (const variant of product.variants || []) {
      if (archived) continue;
      stockViews.push(mountVariantStock(query(`[data-variant-stock="${variant.id}"]`), variant, {
        isCurrent: current, suppliers,
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
        const fields = Object.fromEntries(['title', 'slug', 'collection_id', 'badge', 'description', 'short_description', 'material', 'care', 'sizing', 'hero_benefit'].map(name => [name, value(form, name).trim() || null]));
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
      node.onclick = () => { node.closest('.catalog-variant')?.remove(); markDirty(); };
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
      <div class="catalog-toolbar">${button('Move up', '', `data-link-up="${index}" ${index === 0 ? 'disabled' : ''}`)}${button('Move down', '', `data-link-down="${index}" ${index === links.length-1 ? 'disabled' : ''}`)}${button('Detach', '', `data-link-remove="${index}"`)}</div>
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
        ${button('Edit collection', '', `data-edit-collection="${esc(c.id)}"`)}<div class="catalog-toolbar">
        ${button('Move up', '', `data-collection-move="${index}" data-delta="-1" ${index === 0 ? 'disabled' : ''}`)}
        ${button('Move down', '', `data-collection-move="${index}" data-delta="1" ${index === collections.length-1 ? 'disabled' : ''}`)}</div></article>`).join('') || '<p>No collections yet.</p>'}</div><div id="catalog-collection-editor"></div>`);
    bind('#catalog-new-collection', () => { if (context.canLeave()) collectionEditor({ is_active: true }); });
    container.querySelectorAll('[data-edit-collection]').forEach(node => node.addEventListener('click', () => { if (context.canLeave()) collectionEditor(collections.find(c => c.id === node.dataset.editCollection)); }));
    container.querySelectorAll('[data-collection-move]').forEach(node => node.addEventListener('click', () => {
      if (!context.canLeave()) return;
      const reordered = [...collections], from = Number(node.dataset.collectionMove), to = from + Number(node.dataset.delta);
      [reordered[from], reordered[to]] = [reordered[to], reordered[from]];
      action(() => api.reorderOwnerCollections(reordered.map(c => ({ id: c.id, expected_version: c.edit_version }))), collectionList);
    }));
  }
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
        <div id="catalog-col-deactivation-warning" style="display: ${!collection.is_active && publishedCount > 0 ? 'block' : 'none'}; padding: 10px 14px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; color: #FCA5A5; font-size: 0.85rem; margin-top: 8px;">
          ⚠️ Warning: Deactivating this collection will hide ${publishedCount} published product(s) from customer catalog listings and checkout, because published products require an active collection.
        </div>
        <div class="catalog-toolbar" style="margin-top: 12px;">
          <button type="submit" class="btn btn-primary" id="catalog-save-collection">Save collection details</button>
          ${button('Close editor', 'catalog-close-collection')}
        </div>
      </form>
      ${collection.id ? `
        <section style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #344b3c;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0; font-size: 1rem;">Products in this Collection (${memberProducts.length})</h4>
            ${button('➕ Create product here', 'catalog-col-create-prod', 'class="btn btn-secondary" style="font-size: 0.8125rem; padding: 6px 12px;"')}
          </div>
          <p style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.6); margin-bottom: 12px;">
            Every product is assigned to one collection. Moving a product preserves its SKU, variants, inventory, and order history.
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
      action(() => api.updateOwnerProduct(targetProd.id, {
        expected_version: targetProd.edit_version,
        collection_id: collection.id,
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
      const newColId = targetColId === '__unassign__' ? null : targetColId;
      action(() => api.updateOwnerProduct(prod.id, {
        expected_version: prod.edit_version,
        collection_id: newColId,
      }), async () => {
        await collectionEditor(collection);
        status(`Product moved successfully.`);
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
    box.innerHTML = `<label>Upload local images or videos<input type="file" id="catalog-file-input" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" multiple></label>
      <p>JPEG / PNG / WebP: 10 MiB and 40 megapixels. H.264 MP4 / VP8 or VP9 WebM: 100 MiB, 120 seconds. Videos need an image poster.</p><div id="catalog-upload-queue"></div>`;
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
        ${button('➕ Add new hero slide', 'catalog-new-hero-slide', 'class="btn btn-primary"')}
        ${button('Reload playlist', 'catalog-reload-hero')}
      </div>
      <p style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); margin-top: 4px;">
        Homepage hero playlist controls the responsive horizontal video and imagery on the storefront.
        The active video starts muted and plays to its end before transitioning to the next. A single video loops continuously.
      </p>
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
            <label>Video asset (for video slides)
              <select name="video_asset_id">
                ${options([['', 'None (image slide)'], ...videoAssets.map(a => [a.id, `${a.original_name} (${(a.byte_size / 1024 / 1024).toFixed(1)} MiB)`])], slide?.video_asset_id)}
              </select>
            </label>
            <label>Video poster image (required for video slides)
              <select name="poster_asset_id">
                ${options([['', 'Choose poster image'], ...imageAssets.map(a => [a.id, a.original_name])], slide?.poster_asset_id)}
              </select>
            </label>
            <label>Image asset (for image-only slides)
              <select name="image_asset_id">
                ${options([['', 'None (use video above)'], ...imageAssets.map(a => [a.id, a.original_name])], slide?.image_asset_id)}
              </select>
            </label>
            <label>Destination product (optional click target)
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
