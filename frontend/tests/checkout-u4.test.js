import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { createCartDrawer } from '../src/components/CartDrawer.js';
import { createCheckoutView } from '../src/components/CheckoutView.js';
import { createOrderTrackingModal } from '../src/components/OrderTrackingModal.js';
import { cart } from '../src/utils/cart.js';
import { capabilities } from '../src/utils/capabilities.js';

function setupMockDom() {
  const body = createMockElement('body');
  const app = createMockElement('div');
  app.id = 'app';
  body.appendChild(app);

  const doc = createMockElement('document');
  Object.assign(doc, {
    body,
    createElement: createMockElement,
    getElementById: id => body.querySelector(`#${id}`),
    querySelector: selector => body.querySelector(selector),
    querySelectorAll: selector => body.querySelectorAll(selector),
    activeElement: body,
  });
  globalThis.document = doc;
  globalThis.window = {
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
    location: { search: '', pathname: '/' },
    navigator: { clipboard: { writeText: async () => {} } },
  };
  return { doc, body, app };
}

describe('Phase U4: Editorial Cart Drawer, 2-Column Checkout & Tracking Stepper', () => {
  beforeEach(() => {
    cart.clear();
    setupMockDom();
  });

  it('Cart Drawer renders editorial empty state and triggers onExplore callback', () => {
    let exploreTriggered = false;
    const cartDrawer = createCartDrawer(() => {}, () => { exploreTriggered = true; });
    document.body.appendChild(cartDrawer.backdrop);
    document.body.appendChild(cartDrawer.drawer);

    cartDrawer.open();
    const emptyTitle = cartDrawer.drawer.querySelector('.drawer-empty-title');
    assert.ok(emptyTitle, 'Expected drawer-empty-title to be present');
    assert.equal(emptyTitle.textContent, 'Your shopping bag is empty');

    const exploreBtn = cartDrawer.drawer.querySelector('#btn-cart-explore');
    assert.ok(exploreBtn, 'Expected #btn-cart-explore button in empty state');
    exploreBtn.click();
    assert.equal(exploreTriggered, true, 'Expected onExplore callback to be called');
  });

  it('Cart Drawer renders tabular prices, 3:4 thumbnail, and accessible stepper controls', () => {
    const cartDrawer = createCartDrawer();
    document.body.appendChild(cartDrawer.backdrop);
    document.body.appendChild(cartDrawer.drawer);

    cart.addItem({
      variant_id: 201,
      product_id: 'prod-hoodie',
      title: 'Relaxed Fleece Hoodie',
      price_minor: 680000,
      size: 'L',
      color: 'Washed Olive',
      image_url: '/media/hoodie.jpg',
    }, {}, 1);

    cartDrawer.open();
    const itemEl = cartDrawer.drawer.querySelector('[data-variant-id="201"]');
    assert.ok(itemEl, 'Expected cart item with data-variant-id 201');

    const img = itemEl.querySelector('.cart-item-img');
    assert.ok(img, 'Expected .cart-item-img thumbnail');

    const price = itemEl.querySelector('.cart-item-price');
    assert.ok(price.classList.contains('price-tabular'), 'Expected price-tabular class on item price');
    assert.equal(price.textContent, 'PKR 6,800');

    const subtotal = cartDrawer.drawer.querySelector('#cart-subtotal');
    assert.ok(subtotal.classList.contains('price-tabular'), 'Expected price-tabular class on subtotal');

    const decBtn = itemEl.querySelector('.btn-qty-dec');
    const incBtn = itemEl.querySelector('.btn-qty-inc');
    assert.ok(decBtn.getAttribute('aria-label').includes('Relaxed Fleece Hoodie'));
    assert.ok(incBtn.getAttribute('aria-label').includes('Relaxed Fleece Hoodie'));
  });

  it('Checkout View features HTML5 autocomplete tokens and 2-column layout', () => {
    const checkoutView = createCheckoutView();
    document.body.appendChild(checkoutView.element);

    const nameInput = checkoutView.element.querySelector('#input-customer-name');
    const phoneInput = checkoutView.element.querySelector('#input-customer-phone');
    const addressInput = checkoutView.element.querySelector('#input-shipping-address-1');
    const cityInput = checkoutView.element.querySelector('#input-shipping-city');
    const provinceInput = checkoutView.element.querySelector('#input-shipping-province');
    const postalInput = checkoutView.element.querySelector('#input-shipping-postal');

    assert.equal(nameInput.getAttribute('autocomplete'), 'name');
    assert.equal(phoneInput.getAttribute('autocomplete'), 'tel');
    assert.equal(addressInput.getAttribute('autocomplete'), 'street-address');
    assert.equal(cityInput.getAttribute('autocomplete'), 'address-level2');
    assert.equal(provinceInput.getAttribute('autocomplete'), 'address-level1');
    assert.equal(postalInput.getAttribute('autocomplete'), 'postal-code');

    const form = checkoutView.element.querySelector('#checkout-form');
    assert.ok(form.classList.contains('checkout-layout-grid'), 'Expected checkout-layout-grid class on form');
    assert.ok(checkoutView.element.querySelector('.checkout-col-main'), 'Expected main form column');
    assert.ok(checkoutView.element.querySelector('.checkout-col-summary'), 'Expected summary column');
  });

  it('Checkout View performs field validation and displays inline errors without submitting', async () => {
    globalThis.fetch = async (url) => {
      if (String(url).includes('capabilities')) {
        return { ok: true, json: async () => ({ checkout_enabled: true, test_mode: true, payment_methods: ['cod', 'bank_transfer'] }) };
      }
      return { ok: true, json: async () => ({}) };
    };
    await capabilities.refresh();

    const checkoutView = createCheckoutView();
    document.body.appendChild(checkoutView.element);

    cart.addItem({
      variant_id: 301,
      title: 'Boxy Heavy Cotton Tee',
      price_minor: 320000,
    }, {}, 1);

    checkoutView.open();
    await new Promise(resolve => setTimeout(resolve, 20));
    const form = checkoutView.element.querySelector('#checkout-form');
    form.dispatchEvent({ type: 'submit', preventDefault: () => {} });

    const nameInput = checkoutView.element.querySelector('#input-customer-name');
    const errName = checkoutView.element.querySelector('#error-customer-name');
    assert.equal(nameInput.getAttribute('aria-invalid'), 'true');
    assert.ok(errName.textContent.includes('full name'));

    const banner = checkoutView.element.querySelector('#checkout-error-banner');
    assert.equal(banner.style.display, 'block');
  });

  it('Order Tracking renders 4-step status progression timeline', async () => {
    const trackingModal = createOrderTrackingModal();
    document.body.appendChild(trackingModal.element);

    const mockOrder = {
      order_number: 'AZ-20261019-U4TEST',
      order_status: 'dispatched',
      payment_status: 'verified',
      payment_method: 'cod',
      customer_name: 'Zainab Ahmed',
      customer_phone: '0300-1234567',
      shipping_address_line1: 'House 4B, Street 10',
      shipping_city: 'Lahore',
      shipping_province: 'Punjab',
      total: { formatted: 'PKR 4,500' },
      lines: [
        {
          id: 'l1',
          fulfillment_kind: 'original',
          product_title: 'Minimalist Tee',
          size: 'M',
          color: 'Black',
          quantity: 1,
          line_total: { formatted: 'PKR 4,500' },
        },
      ],
    };

    globalThis.fetch = async () => ({
      ok: true,
      json: async () => mockOrder,
    });

    const searchForm = trackingModal.element.querySelector('#tracking-search-form');
    trackingModal.element.querySelector('#tracking-order-num').value = 'AZ-20261019-U4TEST';
    searchForm.dispatchEvent({ type: 'submit', preventDefault: () => {} });

    await new Promise(resolve => setTimeout(resolve, 20));

    const stepper = trackingModal.element.querySelector('.tracking-stepper');
    assert.ok(stepper, 'Expected .tracking-stepper to be rendered');
    const steps = stepper.querySelectorAll('.tracking-step');
    assert.equal(steps.length, 4, 'Expected 4 tracking steps (Placed, Confirmed, Dispatched, Delivered)');

    // For 'dispatched': Placed(done), Confirmed(done), Dispatched(active)
    assert.ok(steps[0].classList.contains('is-done'));
    assert.ok(steps[1].classList.contains('is-done'));
    assert.ok(steps[2].classList.contains('is-active'));
  });
});
