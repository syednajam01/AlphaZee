// Explicit SAMPLE browser-only data; no application database or account writes.
exports.installVendorFixture = async function (page, options = {}) {
  const items = ['S', 'M', 'L', 'XL'].map((size, index) => ({ variant_id: 101 + index, product_id: 'sample-oxford', product_title: 'SAMPLE Oxford shirt', product_slug: 'sample-oxford', color: 'Jet black', size, variant_sku: `SAMPLE-BLK-${size}`, thumbnail_url: '/images/storefront-empty.svg', supplier_cost_minor: index === 3 ? 145050 : 140000, allocated_on_hand: 10 + index, held_quantity: index === 0 ? 3 : 1, available_quantity: 7 + index, version: 2, last_updated_at: null }));
  items.push(...['S', 'M', 'L'].map((size, index) => ({ ...items[index], variant_id: 111 + index, color: 'Chalk white', variant_sku: `SAMPLE-WHT-${size}` })));
  items.push({ ...items[0], product_id: 'sample-other', variant_id: 201, supplier_cost_minor: null, variant_sku: 'SAMPLE-OTHER-S' });
  if (options.pagination) for (let i = 0; items.length < 52; i++) items.push({ ...items[0], product_id: 'sample-extra', product_title: 'SAMPLE extra product', variant_id: 300 + i, size: String(i + 1), variant_sku: `SAMPLE-EXTRA-${i}` });
  const state = { items, calls: [], reads: 0, authenticated: true, failures: new Map(), history: [], shortages: new Set() };
  await page.route('https://fonts.googleapis.com/**', route => route.fulfill({ contentType: 'text/css', body: '' }));
  await page.route('https://fonts.gstatic.com/**', route => route.abort());
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname;
    const reply = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: status === 204 ? undefined : JSON.stringify(body) });
    if (path.endsWith('/vendor/auth/login')) state.authenticated = true;
    if (!state.authenticated) return reply({ detail: 'SAMPLE session expired' }, 401);
    if (path.endsWith('/vendor/auth/session') || path.endsWith('/vendor/auth/login')) return reply({ authenticated: true, username: 'SAMPLE staff', vendor_id: 'sample-shop', vendor_name: 'SAMPLE Karachi Apparel', vendor_slug: 'sample-shop', csrf_token: 'sample-browser-only' });
    if (path.endsWith('/vendor/auth/logout')) { state.authenticated = false; return reply(null, 204); }
    if (path.endsWith('/vendor/stock/history')) return reply({ history: state.history, total: state.history.length });
    if (path.endsWith('/vendor/stock') && request.method() === 'GET') {
      state.reads++;
      const search = (url.searchParams.get('search') || '').toLowerCase();
      const matches = state.items.filter(item => [item.product_title, item.variant_sku, item.size, item.color].some(value => String(value).toLowerCase().includes(search)));
      const offset = Number(url.searchParams.get('offset') || 0), limit = Number(url.searchParams.get('limit') || 50);
      return reply({ items: matches.slice(offset, offset + limit), total_items: matches.length, page: offset / limit + 1, limit });
    }
    const count = path.match(/\/vendor\/stock\/(\d+)\/(count|shortage)$/);
    if (count && request.method() === 'POST') {
      const id = Number(count[1]), body = request.postDataJSON();
      state.calls.push({ id, kind: count[2], body });
      const item = state.items.find(item => item.variant_id === id);
      if (!item) return reply({ detail: 'SAMPLE variant no longer assigned' }, 404);
      if (state.failures.has(id)) {
        const status = state.failures.get(id); state.failures.delete(id);
        if (status === 401) state.authenticated = false;
        if (status === 409) { item.version++; item.allocated_on_hand = 20; item.available_quantity = 20 - item.held_quantity; }
        return reply({ detail: status === 409 ? 'SAMPLE version conflict' : 'SAMPLE request unavailable' }, status);
      }
      if (count[2] === 'shortage') { state.shortages.add(id); item.available_quantity = 0; return reply({ id: 'sample-report', variant_id: id }); }
      if (body.expected_version !== item.version) return reply({ detail: 'SAMPLE version conflict' }, 409);
      const shortage = body.counted_quantity < item.held_quantity;
      if (shortage) state.shortages.add(id);
      if (!shortage) {
        const previous = item.allocated_on_hand;
        item.allocated_on_hand = body.counted_quantity; item.version++;
        state.history.push({ event_id: `sample-${state.history.length}`, variant_id: id, product_title: item.product_title, variant_sku: item.variant_sku, previous_on_hand: previous, new_on_hand: body.counted_quantity, delta: body.counted_quantity - previous, actor_username: 'SAMPLE staff', reason: 'manual_count', occurred_at: '2026-11-10T12:00:00Z' });
      }
      item.available_quantity = state.shortages.has(id) ? 0 : Math.max(0, item.allocated_on_hand - item.held_quantity);
      return reply({ variant_id: id, allocated_on_hand: item.allocated_on_hand, held_quantity: item.held_quantity, available_quantity: item.available_quantity, version: item.version, shortage_detected: shortage, message: shortage ? 'SAMPLE shortage reported; holds preserved' : 'SAMPLE saved' });
    }
    return reply({ detail: 'Unexpected SAMPLE browser request' }, 404);
  });
  return state;
};
