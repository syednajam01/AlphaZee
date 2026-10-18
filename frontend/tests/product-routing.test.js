import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createProductPage } from '../src/components/ProductPage.js';
import { cart } from '../src/utils/cart.js';

// Minimal DOM mock for Node test runner
function createMockElement(tagName) {
  const el = {
    tagName: tagName.toUpperCase(),
    className: '',
    id: '',
    style: {},
    dataset: {},
    children: [],
    _listeners: {},
    _innerHTML: '',
    disabled: false,

    setAttribute(name, val) {
      if (name === 'disabled') {
        this.disabled = val !== false && val !== 'false';
      } else {
        this[name] = val;
      }
    },
    getAttribute(name) {
      if (name === 'disabled') return this.disabled ? '' : null;
      return this[name] || null;
    },
    removeAttribute(name) {
      if (name === 'disabled') this.disabled = false;
      delete this[name];
    },
    appendChild(child) {
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    addEventListener(event, fn) {
      if (!this._listeners[event]) this._listeners[event] = [];
      this._listeners[event].push(fn);
    },
    dispatchEvent(event) {
      const type = typeof event === 'string' ? event : (event.type || 'click');
      const fns = this._listeners[type] || [];
      fns.forEach(fn => fn(typeof event === 'string' ? { type } : event));
    },
    click() {
      this.dispatchEvent('click');
    },
    classList: {
      _classes: new Set(),
      add(cls) { this._classes.add(cls); },
      remove(cls) { this._classes.delete(cls); },
      contains(cls) { return this._classes.has(cls); },
    },
    querySelector(selector) {
      const results = this.querySelectorAll(selector);
      return results.length > 0 ? results[0] : null;
    },
    querySelectorAll(selector) {
      const matches = [];
      function search(node) {
        if (selector.startsWith('#')) {
          if (node.id === selector.slice(1)) matches.push(node);
        } else if (selector.startsWith('.')) {
          const cls = selector.slice(1);
          if (node.className && node.className.split(/\s+/).includes(cls)) matches.push(node);
        } else if (selector.includes('[')) {
          const attrMatch = /\[([a-z0-9_-]+)(?:="?([^"\]]*)"?)?\]/i.exec(selector);
          if (attrMatch) {
            const attr = attrMatch[1];
            const val = attrMatch[2];
            if (attr.startsWith('data-')) {
              const dataKey = attr.replace('data-', '');
              if (val !== undefined ? node.dataset && node.dataset[dataKey] === val : node.dataset && node.dataset[dataKey] !== undefined) {
                matches.push(node);
              }
            } else if (val !== undefined ? node[attr] === val : node[attr] !== undefined) {
              matches.push(node);
            }
          }
        } else if (node.tagName === selector.toUpperCase()) {
          matches.push(node);
        }
        if (node.children) node.children.forEach(search);
      }
      if (this.children) this.children.forEach(search);
      return matches;
    },
  };

  Object.defineProperty(el, 'innerHTML', {
    get() { return this._innerHTML; },
    set(html) {
      this._innerHTML = html;
      this.children = [];
      parseHtmlIntoChildren(html, this);
    },
  });

  return el;
}

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

function parseHtmlIntoChildren(html, root) {
  if (typeof html !== 'string') return;
  const stack = [root];
  const tokenRegex = /<!--[\s\S]*?-->|<(\/)?([a-z0-9-]+)([^>]*)>|([^<]+)/gi;
  let match;

  while ((match = tokenRegex.exec(html)) !== null) {
    if (match[0].startsWith('<!--')) continue;
    const isClosing = match[1] === '/';
    const tagName = match[2];
    const attrsStr = match[3];
    const textContent = match[4];

    if (textContent) {
      const top = stack[stack.length - 1];
      if (top) top.textContent = (top.textContent || '') + textContent;
      continue;
    }

    if (isClosing) {
      const lower = tagName.toLowerCase();
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].tagName.toLowerCase() === lower) {
          stack.splice(i);
          break;
        }
      }
    } else {
      const el = createMockElement(tagName);
      if (attrsStr) {
        const attrRegex = /([a-z0-9_-]+)(?:=(?:"([^"]*)"|'([^']*)'|(\S+)))?/gi;
        let attrMatch;
        while ((attrMatch = attrRegex.exec(attrsStr)) !== null) {
          const name = attrMatch[1].toLowerCase();
          const val = attrMatch[2] ?? attrMatch[3] ?? attrMatch[4] ?? '';
          if (name === 'class') {
            el.className = val;
            val.split(/\s+/).filter(Boolean).forEach(c => el.classList.add(c));
          } else if (name === 'id') {
            el.id = val;
          } else if (name.startsWith('data-')) {
            const dataKey = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
            el.dataset[dataKey] = val;
          }
          el.setAttribute(name, val);
        }
      }
      const top = stack[stack.length - 1];
      if (top) top.appendChild(el);
      if (!VOID_TAGS.has(tagName.toLowerCase())) stack.push(el);
    }
  }
}

describe('Product Page & Routing Invariants', () => {
  let originalDocument;
  let originalLocalStorage;

  beforeEach(() => {
    originalDocument = global.document;
    originalLocalStorage = global.localStorage;

    const mockStorage = {};
    global.localStorage = {
      getItem: (k) => mockStorage[k] || null,
      setItem: (k, v) => { mockStorage[k] = String(v); },
      removeItem: (k) => { delete mockStorage[k]; },
      clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
    };

    global.document = {
      createElement: (tag) => createMockElement(tag),
      head: createMockElement('head'),
      body: createMockElement('body'),
      title: '',
      querySelector: (sel) => {
        if (sel === 'meta[name="description"]') return null;
        if (sel === 'link[rel="canonical"]') return null;
        return null;
      }
    };
    cart.clear();
  });

  afterEach(() => {
    global.document = originalDocument;
    global.localStorage = originalLocalStorage;
  });

  const sampleProduct = {
    id: 'prod-001',
    slug: 'architectural-heavyweight-tee',
    title: 'Architectural Heavyweight Tee',
    description: 'Minimalist streetwear engineered from 240 GSM combed cotton.',
    collection_name: 'Heavyweight Essentials',
    availability: 'available',
    min_price_minor: 350000,
    media: [
      { id: 1, role: 'primary', kind: 'image', url: '/images/tee-black.jpg', alt_text: 'Black Tee' },
      { id: 2, role: 'gallery', kind: 'image', url: '/images/tee-olive.jpg', alt_text: 'Olive Tee', variant_id: 202 }
    ],
    variants: [
      { id: 201, sku: 'TEE-BLK-M', size: 'M', color: 'Black', price_minor: 350000, availability: 'available' },
      { id: 202, sku: 'TEE-OLV-L', size: 'L', color: 'Olive', price_minor: 380000, availability: 'available' },
      { id: 203, sku: 'TEE-BLK-XL', size: 'XL', color: 'Black', price_minor: 350000, availability: 'unavailable' }
    ]
  };

  it('renders product details, breadcrumb, and sets document title on successful load', async () => {
    globalThis.fetch = async (url) => {
      if (String(url).includes('/products/architectural-heavyweight-tee')) {
        return { ok: true, json: async () => sampleProduct };
      }
      return { ok: false, status: 404 };
    };

    let addedToCartCalled = false;
    let navigatedTo = null;

    const page = createProductPage({
      onAddedToCart: () => { addedToCartCalled = true; },
      onNavigate: (url) => { navigatedTo = url; }
    });

    await page.load('architectural-heavyweight-tee');

    assert.equal(document.title, 'Architectural Heavyweight Tee — AlphaZee');

    const titleEl = page.element.querySelector('.product-page-title');
    assert.ok(titleEl);
    assert.equal(titleEl.textContent, 'Architectural Heavyweight Tee');

    const breadcrumbCurrent = page.element.querySelector('.product-breadcrumb-current');
    assert.ok(breadcrumbCurrent);
    assert.equal(breadcrumbCurrent.textContent, 'Architectural Heavyweight Tee');

    const priceEl = page.element.querySelector('#product-detail-price');
    assert.ok(priceEl);
    assert.match(priceEl.textContent, /PKR/);

    page.destroy();
  });

  it('renders honest unavailable screen when slug does not exist (404)', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Product not found' })
    });

    const page = createProductPage({
      onAddedToCart: () => {},
      onNavigate: () => {}
    });

    await page.load('nonexistent-slug');

    assert.equal(document.title, 'Piece Unavailable — AlphaZee');

    const unavailableTitle = page.element.querySelector('.product-unavailable-title');
    assert.ok(unavailableTitle);
    assert.match(unavailableTitle.textContent, /Piece Unavailable/);

    page.destroy();
  });

  it('restores requested variant from query parameter if valid', async () => {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => sampleProduct
    });

    const page = createProductPage({
      onAddedToCart: () => {},
      onNavigate: () => {}
    });

    // Request variant 202 (Olive, L)
    await page.load('architectural-heavyweight-tee', '202');

    const selectedColor = page.element.querySelector('#selected-color-name');
    const selectedSize = page.element.querySelector('#selected-size-name');

    assert.equal(selectedColor?.textContent, 'Olive');
    assert.equal(selectedSize?.textContent, 'L');

    page.destroy();
  });

  it('gracefully falls back to first available variant if variant query is invalid', async () => {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => sampleProduct
    });

    const page = createProductPage({
      onAddedToCart: () => {},
      onNavigate: () => {}
    });

    // Request bogus variant id 99999
    await page.load('architectural-heavyweight-tee', '99999');

    const selectedColor = page.element.querySelector('#selected-color-name');
    const selectedSize = page.element.querySelector('#selected-size-name');

    assert.equal(selectedColor?.textContent, 'Black');
    assert.equal(selectedSize?.textContent, 'M');

    page.destroy();
  });

  it('adds selected variant with quantity to cart', async () => {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => sampleProduct
    });

    let addedTriggered = false;
    const page = createProductPage({
      onAddedToCart: () => { addedTriggered = true; },
      onNavigate: () => {}
    });

    await page.load('architectural-heavyweight-tee');

    // Increase quantity to 2
    const plusBtn = page.element.querySelector('#btn-qty-plus');
    plusBtn?.click();

    const addBtn = page.element.querySelector('#btn-add-to-cart');
    assert.ok(addBtn);
    assert.equal(addBtn.disabled, false);

    addBtn.click();

    assert.equal(addedTriggered, true);
    const cartState = cart.getState();
    assert.equal(cartState.items.length, 1);
    assert.equal(cartState.items[0].product_id, 'prod-001');
    assert.equal(cartState.items[0].variant_id, 201);
    assert.equal(cartState.items[0].quantity, 2);

    page.destroy();
  });
});
