import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createFeaturedProducts } from '../src/components/FeaturedProducts.js';
import { createProductModal } from '../src/components/ProductModal.js';
import { createHeader } from '../src/components/Header.js';
import { storeConfig } from '../src/data/store-config.js';

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

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
    _textContent: '',

    setAttribute(name, val) {
      if (name === 'style') {
        if (typeof val === 'string') {
          val.split(';').forEach(rule => {
            const [prop, v] = rule.split(':');
            if (prop && v) this.style[prop.trim()] = v.trim();
          });
        }
        return;
      }
      this[name] = val;
    },
    getAttribute(name) {
      return this[name] || null;
    },
    appendChild(child) {
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    prepend(child) {
      this.children.unshift(child);
      child.parentElement = this;
      return child;
    },
    addEventListener(event, fn) {
      if (!this._listeners[event]) this._listeners[event] = [];
      this._listeners[event].push(fn);
    },
    dispatchEvent(event) {
      const fns = this._listeners[event.type || event] || [];
      fns.forEach(fn => fn(event));
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
        if (!node) return;
        if (selector.startsWith('#')) {
          const id = selector.slice(1);
          if (node.id === id) matches.push(node);
        } else if (selector.startsWith('.')) {
          const cls = selector.slice(1);
          if (node.className && node.className.split(/\s+/).includes(cls)) {
            matches.push(node);
          }
        } else if (selector.startsWith('[')) {
          const attrMatch = selector.match(/\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/);
          if (attrMatch) {
            const attr = attrMatch[1];
            const val = attrMatch[2];
            if (attr.startsWith('data-')) {
              const key = attr.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
              if (val !== undefined) {
                if (node.dataset && node.dataset[key] === val) matches.push(node);
              } else if (node.dataset && node.dataset[key] !== undefined) {
                matches.push(node);
              }
            } else if (val !== undefined) {
              if (node[attr] === val || node.getAttribute?.(attr) === val) matches.push(node);
            } else if (node[attr] !== undefined || node.getAttribute?.(attr) !== null) {
              matches.push(node);
            }
          }
        } else if (node.tagName && node.tagName.toLowerCase() === selector.toLowerCase()) {
          matches.push(node);
        }

        if (Array.isArray(node.children)) {
          for (const child of node.children) {
            search(child);
          }
        }
      }

      if (this.children) {
        for (const child of this.children) {
          search(child);
        }
      }
      return matches;
    },
  };

  Object.defineProperty(el, 'innerHTML', {
    get() { return this._innerHTML; },
    set(html) {
      this._innerHTML = html;
      this.children = [];
      parseHtmlIntoChildren(html, this);
    }
  });

  Object.defineProperty(el, 'textContent', {
    get() {
      if (this.children.length === 0) return this._textContent || this._innerHTML.replace(/<[^>]*>/g, '');
      return this.children.map(c => c.textContent || '').join('');
    },
    set(txt) {
      this._textContent = txt;
      this._innerHTML = txt;
      this.children = [];
    }
  });

  return el;
}

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
      if (top) {
        top._textContent = (top._textContent || '') + textContent;
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

      if (!VOID_TAGS.has(tagName.toLowerCase())) {
        stack.push(el);
      }
    }
  }
}

describe('Catalog Pagination & Out-of-Order Request Sequencing', () => {
  let originalFetch;
  let originalDocument;
  let originalWindow;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    originalDocument = globalThis.document;
    originalWindow = globalThis.window;

    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
      matchMedia: () => ({ matches: false }),
    };

    globalThis.document = {
      createElement: (tag) => createMockElement(tag),
      body: createMockElement('body'),
    };
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    globalThis.document = originalDocument;
    globalThis.window = originalWindow;
  });

  it('renders "Load More" pagination and loads the next page when clicked', async () => {
    const page1Products = [
      { id: 'prod-1', slug: 'tee-1', title: 'Tee One', min_price: { minor: 250000, formatted: 'PKR 2,500' } },
      { id: 'prod-2', slug: 'tee-2', title: 'Tee Two', min_price: { minor: 300000, formatted: 'PKR 3,000' } },
    ];
    const page2Products = [
      { id: 'prod-3', slug: 'tee-3', title: 'Tee Three', min_price: { minor: 350000, formatted: 'PKR 3,500' } },
      { id: 'prod-4', slug: 'tee-4', title: 'Tee Four', min_price: { minor: 400000, formatted: 'PKR 4,000' } },
    ];

    globalThis.fetch = async (url) => {
      const urlStr = String(url);
      if (urlStr.includes('/collections')) {
        return {
          ok: true,
          json: async () => ({ collections: [], total: 0 }),
        };
      }
      if (urlStr.includes('/products')) {
        const u = new URL(urlStr, 'http://localhost');
        const page = u.searchParams.get('page');
        if (page === '2') {
          return {
            ok: true,
            json: async () => ({ products: page2Products, total: 4, page: 2, page_size: 2 }),
          };
        }
        return {
          ok: true,
          json: async () => ({ products: page1Products, total: 4, page: 1, page_size: 2 }),
        };
      }
      return { ok: false, status: 404 };
    };

    const component = createFeaturedProducts();

    // Wait for initial load
    await new Promise(resolve => setTimeout(resolve, 50));

    const loadMoreBtn = component.element.querySelector('#btn-load-more');
    assert.ok(loadMoreBtn, 'Load more button should be rendered when products < total');
    assert.match(loadMoreBtn.textContent, /Load More Products/);

    // Click load more
    loadMoreBtn.dispatchEvent('click');

    // Wait for second page load
    await new Promise(resolve => setTimeout(resolve, 50));

    const cards = component.element.querySelectorAll('.product-card');
    assert.equal(cards.length, 4, 'Should contain all 4 loaded products across both pages');

    const paginationDesc = component.element.querySelector('.catalog-status-desc');
    assert.ok(paginationDesc, 'Status text should display showing all pieces');
    assert.match(paginationDesc.textContent, /Showing all 4 pieces/);
  });

  it('discards stale out-of-order filter responses when switching categories rapidly', async () => {
    let resolveFirstRequest;
    let resolveSecondRequest;

    const firstPromise = new Promise(resolve => { resolveFirstRequest = resolve; });
    const secondPromise = new Promise(resolve => { resolveSecondRequest = resolve; });

    globalThis.fetch = async (url) => {
      const urlStr = String(url);
      if (urlStr.includes('/collections')) {
        return {
          ok: true,
          json: async () => ({
            collections: [{ id: 'col-hoodies', name: 'Hoodies' }],
            total: 1,
          }),
        };
      }
      if (urlStr.includes('/products')) {
        const u = new URL(urlStr, 'http://localhost');
        const colId = u.searchParams.get('collection_id');
        if (!colId) {
          // "all" request is slow
          await firstPromise;
          return {
            ok: true,
            json: async () => ({
              products: [{ id: 'prod-all', slug: 'all-piece', title: 'Slow All Piece', min_price: { minor: 100000, formatted: 'PKR 1,000' } }],
              total: 1,
            }),
          };
        } else if (colId === 'col-hoodies') {
          // Hoodies request is fast
          await secondPromise;
          return {
            ok: true,
            json: async () => ({
              products: [{ id: 'prod-hoodie', slug: 'hoodie-piece', title: 'Fast Hoodie Piece', min_price: { minor: 200000, formatted: 'PKR 2,000' } }],
              total: 1,
            }),
          };
        }
      }
      return { ok: false, status: 404 };
    };

    const component = createFeaturedProducts();

    // Immediately trigger filter to hoodies before "all" finishes
    component.setFilter('col-hoodies');

    // Resolve the second (hoodies) request first
    resolveSecondRequest();
    await new Promise(resolve => setTimeout(resolve, 30));

    let cards = component.element.querySelectorAll('.product-card');
    assert.equal(cards.length, 1);
    assert.ok(component.element.querySelector('#product-prod-hoodie'), 'Hoodie should be rendered');

    // Now resolve the slower first ("all") request
    resolveFirstRequest();
    await new Promise(resolve => setTimeout(resolve, 30));

    // The slower first response must be discarded by request sequencing
    cards = component.element.querySelectorAll('.product-card');
    assert.equal(cards.length, 1, 'Should NOT overwrite with stale "all" response');
    assert.ok(component.element.querySelector('#product-prod-hoodie'), 'Still showing hoodie, not stale all piece');
  });

  it('discards stale out-of-order modal detail fetch responses', async () => {
    let resolveFirstModal;
    let resolveSecondModal;

    const firstPromise = new Promise(resolve => { resolveFirstModal = resolve; });
    const secondPromise = new Promise(resolve => { resolveSecondModal = resolve; });

    globalThis.fetch = async (url) => {
      const urlStr = String(url);
      if (urlStr.includes('slug-slow')) {
        await firstPromise;
        return {
          ok: true,
          json: async () => ({
            id: 'p-slow',
            slug: 'slug-slow',
            title: 'Slow Piece',
            variants: [{ id: 101, sku: 'SKU-S', size: 'M', color: 'Black', price: { minor: 100000, formatted: 'PKR 1,000' }, availability: 'available' }],
          }),
        };
      }
      if (urlStr.includes('slug-fast')) {
        await secondPromise;
        return {
          ok: true,
          json: async () => ({
            id: 'p-fast',
            slug: 'slug-fast',
            title: 'Fast Piece',
            variants: [{ id: 201, sku: 'SKU-F', size: 'L', color: 'White', price: { minor: 200000, formatted: 'PKR 2,000' }, availability: 'available' }],
          }),
        };
      }
      return { ok: false, status: 404 };
    };

    const modal = createProductModal();

    // User clicked slow piece, then quickly clicked fast piece
    modal.open('slug-slow');
    modal.open('slug-fast');

    // Fast piece arrives first
    resolveSecondModal();
    await new Promise(resolve => setTimeout(resolve, 30));

    const bodyContent = modal.element.querySelector('#modal-body-content');
    assert.match(bodyContent.textContent, /Fast Piece/);

    // Slow piece arrives later
    resolveFirstModal();
    await new Promise(resolve => setTimeout(resolve, 30));

    // Stale slow piece must NOT overwrite the fast piece
    assert.match(bodyContent.textContent, /Fast Piece/);
    assert.doesNotMatch(bodyContent.textContent, /Slow Piece/);
  });
});

describe('Storefront Prototype Presentation & Invariants Verification', () => {
  let originalDocument;
  let originalWindow;

  beforeEach(() => {
    originalDocument = globalThis.document;
    originalWindow = globalThis.window;

    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
      matchMedia: () => ({ matches: false }),
    };

    globalThis.document = {
      createElement: (tag) => createMockElement(tag),
      body: createMockElement('body'),
    };
  });

  afterEach(() => {
    globalThis.document = originalDocument;
    globalThis.window = originalWindow;
  });

  it('renders honest prototype demo announcement banner in Header', () => {
    const header = createHeader();
    const banner = header.querySelector('.announcement-bar');
    assert.ok(banner, 'Announcement banner should exist in header');
    assert.match(banner.textContent, /MVP Concept Preview/i);
    assert.match(banner.textContent, /disabled/i);
  });

  it('removes unconfirmed payment gateway, encryption, and placeholder WhatsApp claims from storeConfig', () => {
    // Check FAQs
    const faqAnswers = storeConfig.faqs.map(f => f.a).join(' ');
    assert.doesNotMatch(faqAnswers, /encrypted/i, 'No unconfirmed 256-bit encryption claims');
    assert.doesNotMatch(faqAnswers, /credit cards/i, 'No fake credit card claims');

    // Check Reassurance
    const reassuranceTitles = storeConfig.reassurance.map(r => r.title).join(' ');
    assert.doesNotMatch(reassuranceTitles, /Secure Payments/i, 'Should describe manual verification, not unverified secure gateways');

    // Check Footer Links
    const careHrefs = storeConfig.footerLinks.customerCare.map(l => l.href).join(' ');
    assert.doesNotMatch(careHrefs, /wa\.me\/yourwhatsapp/i, 'No broken placeholder WhatsApp numbers');
  });
});
