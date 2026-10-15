import * as api from '../../utils/api.js';
import { escapeHtml as esc } from '../../utils/dom.js';
import { parseCatalogPkr, formatPkr } from '../../utils/money.js';
import { mountStockHolds } from './StockHolds.js';

export function mountVariantStock(host, variant, { isCurrent, onDirty, suppliers }) {
  let alive = true, busy = false, dirty = false, snapshot, holdViews = [];
  const current = () => alive && isCurrent();
  const q = selector => host.querySelector(selector);
  const get = name => (q(`[name="${name}"]`).value || '').trim();
  const groups = { mapping: ['stock_supplier','stock_cost'], supplier: ['stock_new_name','stock_new_slug','stock_new_notes'], adjustment: ['stock_delta','stock_reason','stock_reference','stock_notes'] };
  const changed = new Set();
  async function reloadAfter(savedGroup) {
    const retained = [...changed].filter(group => group !== savedGroup);
    const inputs = retained.flatMap(group => groups[group]).filter(name => q(`[name="${name}"]`)).map(name => [name, get(name)]);
    await load();
    if (!current()) return;
    inputs.forEach(([name,value]) => { const input = q(`[name="${name}"]`); if (input) input.value = value; });
    retained.forEach(group => changed.add(group));
    mark(changed.size > 0);
  }
  function mark(value) { dirty = value; onDirty(variant.id, value); }
  function feedback(message) { if (current()) q('[data-stock-feedback]').textContent = message; }
  async function action(operation, success) {
    if (busy || !current()) return;
    busy = true;
    const controls = [...host.querySelectorAll('button,input,select,textarea')].map(n => [n, n.disabled]); controls.forEach(([n]) => { n.disabled = true; });
    feedback('Working…');
    try { const result = await operation(); if (current()) await success?.(result); }
    catch (error) { feedback(error.status === 409 ? 'Stock changed. Your input is retained; reload stock and review before retrying.' : error.message); }
    finally { busy = false; controls.forEach(([n, disabled]) => { n.disabled = disabled; }); }
  }
  async function load() {
    const [state, list] = await Promise.all([api.fetchVariantStock(variant.id), suppliers()]);
    if (!current()) return;
    snapshot = state; changed.clear(); mark(false); holdViews.forEach(v => v.destroy()); holdViews = [];
    const mapping = state.mapping;
    const choices = (list.suppliers || []).filter(s => s.status === 'active');
    if (mapping && !choices.some(s => s.id === mapping.supplier_id)) choices.unshift({ id: mapping.supplier_id, name: mapping.supplier_name + ' (inactive)' });
    const cost = mapping?.supplier_cost_minor;
    const price = cost === null || cost === undefined ? '' : `${Math.floor(cost/100)}.${String(cost%100).padStart(2,'0')}`;
    host.innerHTML = `<section class="variant-stock-panel"><h4>Supplier and stock · ${esc(variant.sku)}</h4><p data-stock-feedback role="status" aria-live="polite"></p>
      <p>Purchase availability: <strong>${esc(state.public_availability)}</strong>. ${state.readiness_reasons.map(esc).join('; ') || 'Ready for sale.'}</p>
      <div class="catalog-fields"><label>Supplying vendor<select name="stock_supplier"><option value="">Choose supplier</option>${choices.map(s => `<option value="${esc(s.id)}" ${mapping?.supplier_id === s.id ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select></label>
      <label>Wholesale cost PKR<input name="stock_cost" inputmode="decimal" value="${price}"></label></div>
      <button type="button" class="btn btn-secondary" data-save-mapping>Save supplier and cost</button>
      <p>Changing supplier keeps each supplier's stock, existing reservations and order costs intact.</p>
      <details><summary>Register a supplier here</summary><div class="catalog-fields">
      <label>Supplier name<input name="stock_new_name" maxlength="200"></label><label>Supplier slug<input name="stock_new_slug" maxlength="100"></label>
      <label>Supplier notes<textarea name="stock_new_notes" maxlength="500"></textarea></label></div>
      <button type="button" class="btn btn-secondary" data-new-supplier>Register supplier</button></details>
      ${mapping ? `<div data-current-holds></div><div class="catalog-fields">
      <label>Quantity change<input name="stock_delta" type="number" step="1" placeholder="+ received / − damaged"></label>
      <label>Reason<select name="stock_reason"><option value="supplier_receipt">Supplier receipt</option><option value="manual_count">Physical count correction</option><option value="adjustment_correction">Damage or correction</option></select></label>
      <label>Invoice / reference<input name="stock_reference" maxlength="100"></label><label>Adjustment note<textarea name="stock_notes" maxlength="500"></textarea></label></div>
      <button type="button" class="btn btn-secondary" data-adjust-stock ${mapping.version === null ? 'disabled' : ''}>Save stock adjustment</button>` : '<p>No supplier mapping yet. Save a supplier/cost before receiving stock.</p>'}
      <button type="button" class="btn btn-secondary" data-reload-stock>Reload saved stock</button>
      ${state.historical_mappings.map((m, index) => `<details><summary>Previous supplier: ${esc(m.supplier_name)} · ${m.physical_on_hand} physical / ${m.held_reservations} reserved</summary><div data-history-holds="${index}"></div></details>`).join('')}</section>`;
    if (mapping) holdViews.push(mountStockHolds(q('[data-current-holds]'), mapping.supplier_variant_id, mapping, current));
    state.historical_mappings.forEach((m,index) => holdViews.push(mountStockHolds(q(`[data-history-holds="${index}"]`), m.supplier_variant_id, m, current)));
    q('[data-save-mapping]').addEventListener('click', () => action(async () => {
      const cost = parseCatalogPkr(get('stock_cost')), supplier = get('stock_supplier');
      if (!supplier || cost === null) throw new Error('Choose an active supplier and enter an exact nonnegative PKR cost (up to two decimals).');
      await api.assignSupplierVariant(supplier, { variant_id: variant.id, supplier_cost_minor: cost, active: true });
      await reloadAfter('mapping'); feedback('Supplier and wholesale cost saved.');
    }));
    q('[data-new-supplier]').addEventListener('click', () => action(async () => {
      const name = get('stock_new_name'), slug = get('stock_new_slug');
      if (name.length < 2 || slug.length < 2) throw new Error('Enter a supplier name and slug (at least two characters each).');
      const created = await api.createAdminSupplier({ name, slug, notes: get('stock_new_notes') || null });
      await reloadAfter('supplier'); if (!current()) return; q('[name="stock_supplier"]').value = created.id; changed.add('mapping'); mark(true); feedback('Supplier registered. Choose its cost and save the mapping.');
    }));
    q('[data-adjust-stock]')?.addEventListener('click', () => action(async () => {
      const text = get('stock_delta'), delta = Number(text);
      if (changed.has('mapping')) throw new Error('Save or reload the supplier mapping before adjusting its stock.');
      if (!text || !Number.isSafeInteger(delta) || !delta || Math.abs(delta)>2147483647) throw new Error('Enter a nonzero whole-unit stock change.');
      await api.adjustAdminInventory({ supplier_variant_id: snapshot.mapping.supplier_variant_id, expected_version: snapshot.mapping.version,
        quantity_delta: delta, reason: get('stock_reason'), reference_id: get('stock_reference') || null, notes: get('stock_notes') || null });
      await reloadAfter('adjustment'); feedback('Stock adjustment saved.');
    }));
    q('[data-reload-stock]').addEventListener('click', () => { if (!dirty || window.confirm('Discard unsaved supplier/stock inputs and reload?')) action(load); });
  }
  for (const type of ['input','change']) host.addEventListener(type, event => { event.stopPropagation(); const group = Object.keys(groups).find(key => groups[key].includes(event.target.name)); if (group) { changed.add(group); mark(true); } });
  host.addEventListener('keydown', event => { if (event.key === 'Enter' && event.target.tagName !== 'BUTTON' && event.target.tagName !== 'TEXTAREA') { event.preventDefault(); event.stopPropagation(); } });
  host.innerHTML = '<button type="button" class="btn btn-secondary" data-load-stock>Load supplier and stock</button><p data-stock-feedback role="status"></p>';
  q('button').addEventListener('click', () => action(load));
  return { destroy() { alive = false; holdViews.forEach(v => v.destroy()); onDirty(variant.id, false); } };
}
