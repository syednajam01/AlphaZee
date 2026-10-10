import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createProductModal } from '../src/components/ProductModal.js';
import { cart } from '../src/utils/cart.js';

// Minimal DOM mock
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
      toggle(cls, force) {
        if (force === undefined) {
          if (this._classes.has(cls)) this._classes.delete(cls);
          else this._classes.add(cls);
        } else if (force) {
          this._classes.add(cls);
        } else {
          this._classes.delete(cls);
        }
      },
    },

    querySelector(selector) {
      const results = this.querySelectorAll(selector);
      return results.length > 0 ? results[0] : null;
    },

    querySelectorAll(selector) {
      const parts = selector.trim().split(/\s+/);
      if (parts.length > 1) {
        let currentNodes = [this];
        for (const part of parts) {
          const nextNodes = [];
          for (const node of currentNodes) {
            nextNodes.push(...node.querySelectorAll(part));
          }
          currentNodes = nextNodes;
        }
        return currentNodes;
      }

      const matches = [];

      function search(node) {
        if (selector.startsWith('#')) {
          const id = selector.slice(1);
          if (node.id === id) matches.push(node);
        } else if (selector.startsWith('.')) {
          const cls = selector.slice(1);
          if (node.className && node.className.split(/\s+/).includes(cls)) {
            matches.push(node);
          }
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

        if (node.children) {
          node.children.forEach(search);
        }
      }

      if (this.children) {
        this.children.forEach(search);
      }

      return matches;
    },
  };

  Object.defineProperty(el, 'innerHTML', {
    get() {
      return this._innerHTML;
    },
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
    if (match[0].startsWith('<!--')) {
      continue;
    }
    const isClosing = match[1] === '/';
    const tagName = match[2];
    const attrsStr = match[3];
    const textContent = match[4];

    if (textContent) {
      const top = stack[stack.length - 1];
      if (top) {
        top.textContent = (top.textContent || '') + textContent;
      }
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
          if (name === 'class') el.className = val;
          else if (name === 'id') el.id = val;
          else if (name === 'disabled') el.disabled = true;
          else if (name.startsWith('data-')) {
            el.dataset[name.slice(5)] = val;
          }
          el.setAttribute(name, val);
        }
      }

      const top = stack[stack.length - 1];
      if (top) {
        top.appendChild(el);
      }

      const isSelfClosing = attrsStr.trim().endsWith('/') || VOID_TAGS.has(tagName.toLowerCase());
      if (!isSelfClosing) {
        stack.push(el);
      }
    }
  }
}

describe('ProductModal Variant Selection & Cart Invariants', () => {
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
      body: createMockElement('body'),
    };
    cart.clear();
  });

  afterEach(() => {
    global.document = originalDocument;
    global.localStorage = originalLocalStorage;
  });

  it('correctly manages sparse variant combinations and prevents ordering missing combinations', async () => {
    const sparseProduct = {
      id: 'prod-sparse-1',
      slug: 'minimal-tote',
      title: 'Minimal Tote',
      image_url: 'https://cdn.alphazee.pk/tote.jpg',
      variants: [
        {
          id: 101,
          sku: 'AZ-TOTE-S-BLK',
          size: 'Small',
          color: 'Black',
          price: { minor: 250000, currency: 'PKR', formatted: 'PKR 2,500' },
          availability: 'available',
        },
        {
          id: 102,
          sku: 'AZ-TOTE-L-WHT',
          size: 'Large',
          color: 'White',
          price: { minor: 320000, currency: 'PKR', formatted: 'PKR 3,200' },
          availability: 'available',
        },
      ],
    };

    let addedCallbackInvoked = false;
    const modal = createProductModal(() => {
      addedCallbackInvoked = true;
    });

    // Open modal directly with product object
    await modal.open(sparseProduct);

    const btnAddToCart = modal.element.querySelector('#btn-modal-add-to-cart');
    assert.ok(btnAddToCart, 'Add to Cart button should exist');
    assert.strictEqual(btnAddToCart.disabled, false, 'Initial combination (Small, Black) is available');
    assert.match(btnAddToCart.textContent, /Add to Cart • PKR 2,500/);

    // Now user selects size "Large" while color is still "Black" -> (Large, Black) DOES NOT EXIST
    const largeBtn = modal.element.querySelector('[data-size="Large"]');
    assert.ok(largeBtn, 'Large option button should exist');
    largeBtn.click();

    const btnAfterLarge = modal.element.querySelector('#btn-modal-add-to-cart');
    assert.strictEqual(btnAfterLarge.disabled, true, 'Add to cart must be disabled for non-existent combination');
    assert.match(btnAfterLarge.textContent, /Unavailable Combination/);

    // Attempting to click add to cart must NOT add to cart
    btnAfterLarge.click();
    assert.strictEqual(cart.getState().items.length, 0, 'Cart must remain empty when combination does not exist');
    assert.strictEqual(addedCallbackInvoked, false);

    // Now user selects color "White" -> (Large, White) DOES EXIST
    const whiteBtn = modal.element.querySelector('[data-color="White"]');
    assert.ok(whiteBtn, 'White option button should exist');
    whiteBtn.click();

    const btnAfterWhite = modal.element.querySelector('#btn-modal-add-to-cart');
    assert.strictEqual(btnAfterWhite.disabled, false, 'Add to cart should be enabled for valid (Large, White) variant');
    assert.match(btnAfterWhite.textContent, /Add to Cart • PKR 3,200/);

    // Click Add to Cart
    btnAfterWhite.click();
    assert.strictEqual(addedCallbackInvoked, true);

    const cartItems = cart.getState().items;
    assert.strictEqual(cartItems.length, 1);
    const addedItem = cartItems[0];

    // Verify authoritative variant parameters are passed into the cart
    assert.strictEqual(addedItem.variant_id, 102);
    assert.strictEqual(addedItem.sku, 'AZ-TOTE-L-WHT');
    assert.strictEqual(addedItem.size, 'Large');
    assert.strictEqual(addedItem.color, 'White');
    assert.strictEqual(addedItem.price_minor, 320000);
  });

  it('disables add to cart when the selected variant is out of stock', async () => {
    const oosProduct = {
      id: 'prod-oos-1',
      slug: 'tailored-trouser',
      title: 'Tailored Trouser',
      image_url: 'https://cdn.alphazee.pk/trouser.jpg',
      variants: [
        {
          id: 103,
          sku: 'AZ-TR-32-BLK',
          size: '32',
          color: 'Black',
          price: { minor: 490000, currency: 'PKR', formatted: 'PKR 4,900' },
          availability: 'out_of_stock',
        },
      ],
    };

    const modal = createProductModal();
    await modal.open(oosProduct);

    const btnAddToCart = modal.element.querySelector('#btn-modal-add-to-cart');
    assert.ok(btnAddToCart);
    assert.strictEqual(btnAddToCart.disabled, true);
    assert.match(btnAddToCart.textContent, /Out of Stock/);

    btnAddToCart.click();
    assert.strictEqual(cart.getState().items.length, 0);
  });

  it('disables add to cart when the selected variant has missing or invalid price', async () => {
    const invalidPriceProduct = {
      id: 'prod-inv-price',
      slug: 'sample-hoodie',
      title: 'Sample Hoodie',
      variants: [
        {
          id: 104,
          sku: 'AZ-HD-L-GRY',
          size: 'L',
          color: 'Grey',
          price: null,
          price_minor: -1,
          availability: 'available',
        },
      ],
    };

    const modal = createProductModal();
    await modal.open(invalidPriceProduct);

    const btnAddToCart = modal.element.querySelector('#btn-modal-add-to-cart');
    assert.ok(btnAddToCart);
    assert.strictEqual(btnAddToCart.disabled, true);
    assert.match(btnAddToCart.textContent, /Price Unavailable/);

    btnAddToCart.click();
    assert.strictEqual(cart.getState().items.length, 0);
  });
});
