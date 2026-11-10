import { groupVendorStock, MAX_VENDOR_COUNT, parseVendorCount } from '../utils/vendorMatrix.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';
import { formatPkr } from '../utils/money.js';

const icons = {
  edit: '<path d="m16 3 5 5M4 20l5-1L21 7a2 2 0 0 0-5-5L4 14l-1 7Z"/>',
  alert: '<path d="m10.3 3-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 8v4m0 4h.01"/>',
};
function icon(type) { return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[type]}</svg>`; }

export function createVendorStockMatrix({ items, totalItems, limit, drafts, saving, onSave, onCount, onShortage, onDiscard }) {
  const root = document.createElement('div');
  root.className = 'vp-matrix-workspace';
  root.innerHTML = '<div class="vp-draft-summary"><p class="vp-draft-total" role="status"></p><button type="button" class="vp-btn vp-btn-subtle vp-discard-drafts">Discard pending edits</button></div>';
  root.querySelector('.vp-discard-drafts').addEventListener('click', onDiscard);
  const rows = [], buttons = [];
  for (const [index, group] of groupVendorStock(items).entries()) {
    const ids = group.items.map(item => item.variant_id);
    const section = document.createElement('section');
    section.className = 'vp-stock-group';
    section.setAttribute('aria-labelledby', `vp-group-title-${index}`);
    section.innerHTML = `
      <header class="vp-group-header">
        <img src="${escapeHtml(sanitizeMediaUrl(group.thumbnail, '/images/storefront-empty.svg'))}" width="44" height="56" loading="lazy" alt="" />
        <div><h2 id="vp-group-title-${index}">${escapeHtml(group.title)}</h2><p>${escapeHtml(group.color)} <span aria-hidden="true">·</span> ${ids.length} ${ids.length === 1 ? 'size' : 'sizes'} shown</p></div>
      </header>
      <table class="vp-matrix"><caption class="vp-sr-only">${escapeHtml(group.title)}, ${escapeHtml(group.color)} stock counts</caption>
        <thead><tr><th scope="col">Size</th><th scope="col">SKU</th><th scope="col" title="Agreed wholesale rate for supplying AlphaZee">Unit cost</th><th scope="col">Your stock</th><th scope="col">Holds</th><th scope="col">Available</th><th scope="col">Actions</th></tr></thead><tbody></tbody>
      </table>
      <footer class="vp-group-footer"><p class="vp-group-pending"></p><button type="button" class="vp-btn vp-btn-primary vp-save-all-btn" id="vp-save-group-${index}">Save all sizes for ${escapeHtml(group.color)}</button></footer>`;
    for (const item of group.items) {
      const id = item.variant_id, label = `${item.product_title}, ${item.color || 'Standard'}, ${item.size || 'One size'}, ${item.variant_sku}`;
      const row = document.createElement('tr');
      row.className = 'vp-matrix-row'; row.id = `vp-card-${id}`;
      row.innerHTML = `
        <th scope="row" class="vp-matrix-size"><span class="vp-mobile-label vp-size-prefix" aria-hidden="true">Size</span>${escapeHtml(item.size || 'One size')}</th>
        <td class="vp-matrix-sku">${escapeHtml(item.variant_sku)}</td>
        <td class="vp-matrix-cost"><span class="vp-mobile-label" aria-hidden="true">Unit cost</span>${item.supplier_cost_minor == null ? '<span class="vp-unagreed-cost">Not agreed</span>' : escapeHtml(formatPkr(item.supplier_cost_minor))}</td>
        <td class="vp-matrix-count"><span class="vp-mobile-label" aria-hidden="true">Your stock</span><div class="vp-inline-stepper">
          <button type="button" class="vp-step-btn vp-inline-minus" aria-label="Decrease count for ${escapeHtml(label)}">−</button>
          <label class="vp-sr-only" for="vp-matrix-count-${id}">Your stock for ${escapeHtml(label)}</label>
          <input id="vp-matrix-count-${id}" class="vp-input vp-matrix-stock-input" type="text" inputmode="numeric" pattern="[0-9]*" aria-describedby="vp-row-status-${id}" />
          <button type="button" class="vp-step-btn vp-inline-plus" aria-label="Increase count for ${escapeHtml(label)}">+</button>
        </div><span class="vp-recorded-count">Recorded: ${item.allocated_on_hand}</span></td>
        <td class="vp-matrix-held"><span class="vp-mobile-label" aria-hidden="true">Holds</span>${item.held_quantity}</td>
        <td class="vp-matrix-available"><span class="vp-mobile-label" aria-hidden="true">Available</span>${item.available_quantity}</td>
        <td class="vp-matrix-actions"><div class="vp-row-buttons">
          <button type="button" class="vp-btn vp-btn-outline vp-save-row" id="vp-save-row-${id}" aria-label="Save count for ${escapeHtml(label)}">Save</button>
          <button type="button" class="vp-btn vp-btn-subtle vp-icon-button vp-update-btn" id="vp-count-open-${id}" title="Detailed count and notes" aria-label="Detailed count for ${escapeHtml(label)}">${icon('edit')}</button>
          <button type="button" class="vp-btn vp-btn-subtle vp-icon-button vp-shortage-btn" id="vp-shortage-open-${id}" title="Report shortage or damage" aria-label="Report shortage for ${escapeHtml(label)}">${icon('alert')}</button>
          <button type="button" class="vp-btn vp-btn-subtle vp-use-latest" title="Discard this edit and use the recorded server count">Use latest</button>
        </div><p id="vp-row-status-${id}" class="vp-row-status" role="status"></p></td>`;
      const input = row.querySelector('.vp-matrix-stock-input');
      const edit = value => { drafts.edit(item, value); refresh(); };
      input.addEventListener('input', () => edit(input.value));
      row.querySelector('.vp-inline-minus').addEventListener('click', () => { const value = parseVendorCount(input.value); if (value !== null) edit(String(Math.max(0, value - 1))); });
      row.querySelector('.vp-inline-plus').addEventListener('click', () => { const value = parseVendorCount(input.value); if (value !== null && value < MAX_VENDOR_COUNT) edit(String(value + 1)); });
      row.querySelector('.vp-save-row').addEventListener('click', () => onSave([id], `vp-save-row-${id}`));
      row.querySelector('.vp-update-btn').addEventListener('click', () => onCount(item));
      row.querySelector('.vp-shortage-btn').addEventListener('click', () => onShortage(item));
      row.querySelector('.vp-use-latest').addEventListener('click', () => { drafts.reset(id); refresh(); });
      rows.push({ row, input, item }); section.querySelector('tbody').appendChild(row);
    }
    const button = section.querySelector('.vp-save-all-btn');
    button.addEventListener('click', () => onSave(ids, button.id));
    buttons.push({ button, section, ids }); root.appendChild(section);
  }
  function refresh() {
    const pending = drafts.pending().length;
    root.querySelector('.vp-draft-total').textContent = pending ? `${pending} unsaved ${pending === 1 ? 'count' : 'counts'} · edits stay while you search or change pages` : 'Enter new totals, not amounts sold · include customer holds';
    root.querySelector('.vp-discard-drafts').hidden = !pending;
    root.querySelector('.vp-discard-drafts').disabled = saving;
    for (const { row, input, item } of rows) {
      const draft = drafts.get(item.variant_id), value = draft?.value ?? String(item.allocated_on_hand);
      if (input.value !== value) input.value = value;
      const valid = parseVendorCount(value) !== null;
      input.disabled = saving; input.setAttribute('aria-invalid', String(!valid));
      row.dataset.status = draft?.status || 'clean';
      const warning = draft?.dirty && valid && Number(value) < item.held_quantity;
      row.querySelector('.vp-row-status').textContent = !valid ? 'Enter a whole number from 0 to 2,147,483,647' : draft?.message || (draft?.needsReview ? 'Server count changed · use latest before editing again' : warning ? `Below ${item.held_quantity} customer holds · review required before saving` : draft?.dirty ? 'Unsaved count' : '');
      row.querySelector('.vp-save-row').disabled = saving || !draft?.dirty || !valid || draft.needsReview;
      row.querySelector('.vp-recorded-count').hidden = !draft?.dirty && draft?.status !== 'reported';
      row.querySelector('.vp-use-latest').hidden = !draft?.dirty;
      row.querySelectorAll('.vp-inline-minus,.vp-inline-plus,.vp-update-btn,.vp-shortage-btn,.vp-use-latest').forEach(button => { button.disabled = saving; });
    }
    for (const { button, section, ids } of buttons) {
      const changes = drafts.snapshot(ids);
      button.disabled = saving || !changes.length || changes.some(draft => draft.count === null || draft.needsReview);
      section.querySelector('.vp-group-pending').textContent = changes.length ? `${changes.length} changed · each size saves separately${totalItems > limit ? ' · shown rows only' : ''}` : totalItems > limit ? 'Only sizes shown on this page are saved; more may appear on another page' : 'Only changed sizes are sent';
    }
  }
  refresh();
  return root;
}
