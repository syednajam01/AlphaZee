import { fetchStockHolds } from '../../utils/api.js';
import { escapeHtml as esc } from '../../utils/dom.js';

export function mountStockHolds(host, id, initial, isCurrent = () => true) {
  let alive = true, busy = false, data = initial;
  const current = () => alive && isCurrent();
  async function load(page) {
    if (busy) return;
    busy = true;
    const buttons = [...host.querySelectorAll('button')].map(button => [button, button.disabled]); buttons.forEach(([button]) => { button.disabled = true; });
    try { const result = await fetchStockHolds(id, { page, page_size: 20 }); if (current()) { data = result; render(); } }
    catch (error) { if (current()) host.querySelector('[role="status"]').textContent = error.message; }
    finally { busy = false; buttons.forEach(([button, disabled]) => { button.disabled = disabled; }); }
  }
  function render() {
    if (!current()) return;
    if (!data) { host.innerHTML = '<button type="button" class="btn btn-secondary" data-load-holds>Show stock holds</button><p role="status"></p>'; host.querySelector('button').addEventListener('click', () => load(1)); return; }
    host.innerHTML = `<p>Physical <strong>${data.physical_on_hand}</strong> / Reserved <strong>${data.held_reservations}</strong> / Available <strong>${data.available_to_sell}</strong></p>
      <p>${data.held_reservations} units reserved across ${data.total} holds.</p>
      <ul>${data.holds.map(h => `<li>${h.quantity} units · ${esc(h.stage)}${h.legacy_stock_hold ? ' · legacy reconciliation required' : ''} · ${h.order_link
        ? `<a class="admin-return-link" href="/admin/orders?order_id=${encodeURIComponent(h.order_id)}">Order #${esc(h.order_number)}</a>` : 'Order reference unavailable (retained legacy hold)'}</li>`).join('') || '<li>No active holds.</li>'}</ul>
      <div class="catalog-toolbar"><button type="button" class="btn btn-secondary" data-holds-prev ${data.page <= 1 ? 'disabled' : ''}>Previous holds</button>
      <span>Page ${data.page}</span><button type="button" class="btn btn-secondary" data-holds-next ${data.page * data.page_size >= data.total ? 'disabled' : ''}>Next holds</button>
      <button type="button" class="btn btn-secondary" data-holds-refresh>Refresh holds</button></div><p role="status"></p>`;
    host.querySelector('[data-holds-prev]').addEventListener('click', () => load(data.page - 1));
    host.querySelector('[data-holds-next]').addEventListener('click', () => load(data.page + 1));
    host.querySelector('[data-holds-refresh]').addEventListener('click', () => load(data.page));
  }
  render();
  return { destroy() { alive = false; } };
}
