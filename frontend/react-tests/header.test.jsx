import { test } from 'node:test';
import assert from 'node:assert/strict';
import { act } from 'react';
import { installDom } from './dom.js';
import { createHeader } from '../src/components/Header.js';
import { cart } from '../src/utils/cart.js';
import { capabilities } from '../src/utils/capabilities.js';
import { createHeaderScroll } from '../src/utils/headerScroll.js';

test('direction hysteresis, overscroll bounds, interaction locks and route reset', () => {
  const state = createHeaderScroll();
  assert.equal(state.update(10), 'top');
  assert.equal(state.update(33), 'compact');
  assert.equal(state.update(200), 'compact');
  assert.equal(state.update(198), 'compact');
  assert.equal(state.update(201), 'compact');
  assert.equal(state.update(195), 'expanded');
  assert.equal(state.update(197), 'expanded');
  assert.equal(state.update(210), 'compact');
  assert.equal(state.update(5000, 210), 'compact');
  assert.equal(state.update(209, 210), 'compact');
  assert.equal(state.update(204, 210), 'expanded');
  assert.equal(state.update(260, 500, true), 'expanded');
  assert.equal(state.reset(0), 'top');
  assert.equal(state.update(-100), 'top');
});

test('React header preserves actions, settings, subscriptions and focus reveal', async () => {
  const { dom, app } = installDom();
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ announcement_banner_enabled: true, announcement_banner_text: 'SAMPLE delivery announcement', accent_color: '#243f31' }) });
  let cartClicks = 0, menuClicks = 0, trackClicks = 0;
  const subscribers = cart.listeners.size;
  let host;
  try {
    await act(async () => {
      host = createHeader({ onCart: () => cartClicks++, onMenu: () => menuClicks++, onTrack: () => trackClicks++ });
      app.appendChild(host);
    });
    assert.equal(host.querySelector('.announcement-bar').textContent, 'SAMPLE delivery announcement');
    assert.equal(host.querySelectorAll('a[aria-label="AlphaZee home"]').length, 1);
    await act(async () => {
      host.querySelector('#btn-cart').click(); host.querySelector('#btn-mobile-menu').click(); host.querySelector('#nav-track-order').click();
      cart.items = [{ quantity: 3, price_minor: 100, is_available: true }]; cart.notify();
    });
    assert.deepEqual([cartClicks, menuClicks, trackClicks], [1, 1, 1]);
    assert.equal(host.querySelector('#header-cart-count').textContent, '3');
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 80, writable: true });
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: 3000 });
    await act(async () => { window.dispatchEvent(new window.Event('scroll')); await new Promise(resolve => setTimeout(resolve, 35)); });
    assert.equal(host.dataset.navState, 'compact');
    assert.equal(host.querySelector('.header-panel').getAttribute('inert'), '');
    await act(async () => { host.querySelector('.brand-logo-link').focus(); });
    assert.equal(host.dataset.navState, 'expanded');
    assert.equal(host.querySelector('.header-panel').hasAttribute('inert'), false);
    await act(async () => { host.setActiveNav('#faq'); });
    assert.equal(host.querySelector('a[href="#faq"]').getAttribute('aria-current'), 'page');
    await act(async () => host.destroy()); host = null;
    assert.equal(cart.listeners.size, subscribers);
  } finally {
    if (host) await act(async () => host.destroy());
    cart.items = []; cart.notify(); dom.window.close();
    globalThis.IS_REACT_ACT_ENVIRONMENT = false;
  }
});

test('offline settings never show an invented announcement', async () => {
  const { dom, app } = installDom();
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.fetch = async () => { throw new Error('SAMPLE offline'); };
  let host;
  await act(async () => { host = createHeader(); app.appendChild(host); });
  assert.equal(host.querySelector('.announcement-bar').style.display, 'none');
  await act(async () => host.destroy());
  dom.window.close(); globalThis.IS_REACT_ACT_ENVIRONMENT = false;
});
