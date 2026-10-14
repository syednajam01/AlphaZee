import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { initApp } from '../src/app.js';
import { cart } from '../src/utils/cart.js';

function installDom() {
  const body = createMockElement('body');
  const app = createMockElement('div');
  app.id = 'app';
  body.appendChild(app);
  const doc = createMockElement('document');
  Object.assign(doc, {
    body, createElement: createMockElement,
    getElementById: id => body.querySelector(`#${id}`),
    querySelector: selector => body.querySelector(selector),
    querySelectorAll: selector => body.querySelectorAll(selector),
    activeElement: body,
  });
  globalThis.document = doc;
  globalThis.window = { addEventListener() {}, location: { search: '' }, matchMedia: () => ({ matches: false }) };
  return { doc, app };
}

test('offline storefront mounts, closed overlays are inert, and shell controls respond', async () => {
  installDom();
  globalThis.fetch = async () => { throw new Error('SAMPLE offline API'); };
  initApp();
  await new Promise(resolve => setTimeout(resolve, 10));
  for (const id of ['product-modal', 'checkout-modal', 'tracking-modal', 'cart-drawer', 'mobile-nav-drawer']) {
    const root = document.getElementById(id);
    assert.ok(root, `${id} must mount`);
    assert.equal(root.hidden, true, `${id} must be removed from hit testing when closed`);
    assert.equal(root.inert, true, `${id} must not accept focus while closed`);
  }
  const cartTrigger = document.getElementById('btn-cart');
  cartTrigger.focus();
  cartTrigger.click();
  assert.equal(document.getElementById('cart-drawer').hidden, false);
  document.getElementById('cart-close-btn').click();
  assert.equal(document.getElementById('cart-drawer').hidden, true);
  assert.equal(document.activeElement, cartTrigger);
  assert.equal(document.body.style.overflow, '');
  document.getElementById('btn-mobile-menu').click();
  assert.equal(document.getElementById('mobile-nav-drawer').hidden, false);
  document.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault() {} });
  assert.equal(document.getElementById('mobile-nav-drawer').hidden, true);
  document.getElementById('nav-track-order').click();
  assert.equal(document.getElementById('tracking-modal').hidden, false);
  document.getElementById('tracking-close-btn').click();
  assert.ok(document.querySelector('a[href="/admin"]'));
  assert.equal(document.getElementById('admin-modal'), null);

  // Every tracking trigger, including mobile/footer, is wired identically.
  const trackingLinks = document.querySelectorAll('a[href="#track"]');
  assert.equal(trackingLinks.length, 3);
  for (const link of trackingLinks) {
    link.click();
    assert.equal(document.getElementById('tracking-modal').hidden, false);
    document.getElementById('tracking-close-btn').click();
  }
  document.getElementById('btn-browse-catalog').click();
  assert.ok(document.getElementById('featured').scrolledIntoView);
  const questions = document.querySelectorAll('.faq-question');
  questions[1].click();
  assert.equal(questions[1].getAttribute('aria-expanded'), 'true');
  questions[1].click();
  assert.equal(questions[1].getAttribute('aria-expanded'), 'false');
  const deadLinks = ['#shop', '#privacy', '#terms', 'https://wa.me/yourwhatsapp'];
  for (const href of deadLinks) assert.equal(document.querySelector(`a[href="${href}"]`), null);

  // Recover from unavailable API with explicitly labelled in-memory sample data.
  const requests = [];
  const product = {
    id: 'sample-tee', slug: 'sample-tee', title: 'SAMPLE / TEST Tee',
    image_url: '/favicon.svg', min_price: { minor: 250000 },
    variants: [{ id: 1001, sku: 'SAMPLE-M', size: 'M', color: 'Black', availability: 'available', price: { minor: 250000 } },
      { id: 1002, sku: 'SAMPLE-L', size: 'L', color: 'Black', availability: 'available', price: { minor: 250000 } }],
  };
  globalThis.fetch = async url => {
    requests.push(String(url));
    const data = String(url).includes('capabilities') ? { checkout_enabled: false, test_mode: false }
      : String(url).includes('/collections') ? { collections: [{ id: 'sample', name: 'SAMPLE / TEST', image_url: '/favicon.svg' }] }
        : String(url).includes('/products/sample-tee') ? product
          : { products: [product], total: 1 };
    return { ok: true, json: async () => data };
  };
  document.querySelectorAll('.btn-retry').forEach(button => button.click());
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.ok(document.querySelector('.product-card-btn'));
  document.querySelector('.collection-card').click();
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.ok(requests.some(url => url.includes('collection_id=sample')));
  document.querySelector('.product-card-btn').click();
  assert.equal(document.getElementById('product-modal').hidden, false);
  document.querySelector('[data-size="L"]').click();
  document.getElementById('btn-modal-add-to-cart').click();
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(document.getElementById('product-modal').hidden, true);
  assert.equal(document.getElementById('cart-drawer').hidden, false);
  assert.equal(cart.getState().items[0].variant_id, 1002);
  document.querySelector('.btn-qty-inc').click();
  assert.equal(cart.getState().count, 2);
  document.querySelector('.btn-qty-dec').click();
  assert.equal(cart.getState().count, 1);
  assert.equal(document.getElementById('btn-checkout').disabled, true);
  document.querySelector('.btn-remove-item').click();
  assert.equal(cart.getState().count, 0);
  document.getElementById('cart-drawer-backdrop').click();
  assert.equal(document.getElementById('cart-drawer').hidden, true);
  assert.equal(document.body.style.overflow, '');
});
