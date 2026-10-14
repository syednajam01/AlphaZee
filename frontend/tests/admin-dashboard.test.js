import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { initAdminDashboard, adminSection } from '../src/components/AdminDashboard.js';

const flush = () => new Promise(resolve => setTimeout(resolve, 15));

function install(path = '/admin/orders') {
  const doc = createMockElement('document');
  doc.body = createMockElement('body'); doc.createElement = createMockElement;
  const app = createMockElement('div'); app.id = 'app'; doc.body.appendChild(app);
  doc.getElementById = id => doc.body.querySelector(`#${id}`);
  doc.activeElement = doc.body;
  globalThis.document = doc;
  const listeners = new Map();
  const location = { pathname: path };
  const history = { state: null,
    replaceState(state, _, path) { this.state = state; location.pathname = path; },
    pushState(state, _, path) { this.state = state; location.pathname = path; },
    go() {},
  };
  globalThis.window = { location, history, confirm: () => true,
    addEventListener(type, fn) { listeners.set(type, fn); },
    removeEventListener(type) { listeners.delete(type); },
  };
  return { app, doc, listeners, location };
}

test('direct dashboard login preserves route, restores session and supports navigation/back/unknown/logout', async () => {
  const { doc, listeners, location } = install();
  let authenticated = false;
  const requests = [];
  globalThis.fetch = async url => {
    requests.push(url);
    if (url.endsWith('/auth/login')) authenticated = true;
    if (url.endsWith('/auth/logout')) authenticated = false;
    const status = authenticated || url.endsWith('/auth/logout') ? 200 : 401;
    const data = url.includes('/auth/') ? { csrf_token: 'SAMPLE-csrf' }
      : url.endsWith('/orders') || url.includes('/orders?') ? { orders: [] }
      : url.endsWith('/suppliers') ? { suppliers: [] }
      : {};
    return { ok: status === 200, status, json: async () => data };
  };
  const dashboard = initAdminDashboard();
  await dashboard.ready;
  assert.ok(dashboard.element.querySelector('#admin-auth-form'));
  assert.equal(dashboard.element.querySelector('#admin-sidebar').hidden, true);
  assert.equal(doc.body.style.overflow, undefined);
  dashboard.element.querySelector('#admin-username').value = 'sample_owner';
  dashboard.element.querySelector('#admin-password').value = 'SAMPLE-password';
  dashboard.element.querySelector('#admin-auth-form').dispatchEvent({ type: 'submit', preventDefault() {} });
  await flush();
  assert.equal(dashboard.element.querySelector('#admin-auth-form'), null);
  assert.equal(location.pathname, '/admin/orders');
  assert.ok(requests.some(url => url.includes('/admin/orders')));
  dashboard.element.querySelector('[data-tab="products"]').click(); await flush();
  assert.equal(location.pathname, '/admin/products');
  assert.match(dashboard.element.querySelector('#admin-tab-content').textContent, /coming next/);
  location.pathname = '/admin/suppliers'; listeners.get('popstate')({ state: { adminIndex: 0 } });
  await flush();
  assert.match(dashboard.element.querySelector('#admin-view-title').textContent, /Suppliers/);
  location.pathname = '/admin/not-a-section'; listeners.get('popstate')({ state: { adminIndex: 0 } });
  await flush();
  assert.match(dashboard.element.querySelector('#admin-tab-content').textContent, /Section not found/);
  dashboard.element.querySelector('#btn-admin-logout').click(); await flush();
  assert.ok(dashboard.element.querySelector('#admin-auth-form'));
  dashboard.destroy();
  assert.equal(listeners.has('popstate'), false);
  assert.equal(listeners.has('beforeunload'), false);
});

test('late private responses cannot overwrite login after session expiry', async () => {
  install('/admin');
  let release;
  globalThis.fetch = async url => {
    if (url.endsWith('/overview')) return await new Promise(resolve => { release = resolve; });
    return { ok: true, status: 200, json: async () => ({ csrf_token: 'SAMPLE-csrf' }) };
  };
  const dashboard = initAdminDashboard(); await flush();
  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ detail: 'Expired' }) });
  dashboard.selectTab('orders'); await flush();
  assert.ok(dashboard.element.querySelector('#admin-auth-form'));
  release({ ok: true, status: 200, json: async () => ({ total_orders: 987654 }) });
  await dashboard.ready;
  assert.ok(dashboard.element.querySelector('#admin-auth-form'));
  assert.doesNotMatch(dashboard.element.querySelector('#admin-tab-content').textContent, /987654/);
  dashboard.destroy();
});

test('section parsing distinguishes admin root, reports and unknown paths', () => {
  assert.equal(adminSection('/admin/'), 'overview');
  assert.equal(adminSection('/admin/reports'), 'reports');
  assert.equal(adminSection('/admin/orders/extra'), 'not-found');
  assert.equal(adminSection('/administrator'), 'not-found');
});

test('unsaved owner input guards navigation, refresh and page exit', async () => {
  const { listeners, location } = install('/admin/products');
  let requests = 0;
  globalThis.fetch = async () => { requests++; return { ok: true, status: 200,
    json: async () => ({ csrf_token: 'SAMPLE-csrf' }) }; };
  const dashboard = initAdminDashboard(); await dashboard.ready;
  dashboard.element.querySelector('[data-tab="media"]').click(); await flush();
  assert.equal(location.pathname, '/admin/media');
  dashboard.element.dispatchEvent({ type: 'input', target: { closest: () => ({}) } });
  window.confirm = () => false;
  dashboard.element.querySelector('[data-tab="inventory"]').click();
  assert.equal(location.pathname, '/admin/media');
  const before = requests;
  dashboard.element.querySelector('#btn-refresh-admin-tab').click();
  assert.equal(requests, before);
  let prevented = false;
  listeners.get('beforeunload')({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  let confirmations = 0;
  window.confirm = () => { confirmations++; return false; };
  window.history.go = () => { location.pathname = '/admin/media'; listeners.get('popstate')({ state: { adminIndex: 1 } }); };
  location.pathname = '/admin/products';
  listeners.get('popstate')({ state: { adminIndex: 0 } });
  assert.equal(confirmations, 1);
  assert.equal(location.pathname, '/admin/media');
  window.confirm = () => true;
  dashboard.element.querySelector('[data-tab="media"]').click(); await flush();
  assert.equal(location.pathname, '/admin/media');
  dashboard.destroy();
});
