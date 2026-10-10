import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createCollectionsSection } from '../src/components/Collections.js';
import { createFeaturedProducts } from '../src/components/FeaturedProducts.js';

// Minimal DOM mock for Node.js test runner
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

    setAttribute(name, val) {
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
        if (selector.startsWith('#')) {
          const id = selector.slice(1);
          if (node.id === id) matches.push(node);
        } else if (selector.startsWith('.')) {
          const cls = selector.slice(1);
          if (node.className && node.className.split(/\s+/).includes(cls)) {
            matches.push(node);
          }
        } else if (selector.includes('[')) {
          const attr = selector.replace(/[\[\]]/g, '');
          if (node[attr] !== undefined || (node.dataset && node.dataset[attr.replace('data-', '')] !== undefined)) {
            matches.push(node);
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

function parseHtmlIntoChildren(html, parent) {
  if (typeof html !== 'string') return;
  const tagRegex = /<([a-z0-9]+)([^>]*)>(.*?)<\/\1>|<([a-z0-9]+)([^>]*)\/?>/gis;
  let match;
  while ((match = tagRegex.exec(html)) !== null) {
    const tagName = match[1] || match[4];
    const attrsStr = match[2] || match[5] || '';
    const inner = match[3] || '';

    const child = createMockElement(tagName);
    const classMatch = /class="([^"]*)"/i.exec(attrsStr);
    if (classMatch) child.className = classMatch[1];

    const idMatch = /id="([^"]*)"/i.exec(attrsStr);
    if (idMatch) child.id = idMatch[1];

    const dataFilter = /data-filter="([^"]*)"/i.exec(attrsStr);
    if (dataFilter) child.dataset.filter = dataFilter[1];

    const dataCol = /data-collection="([^"]*)"/i.exec(attrsStr);
    if (dataCol) child.dataset.collection = dataCol[1];

    if (inner && inner.includes('<')) {
      child.innerHTML = inner;
    } else {
      child._innerHTML = inner;
    }

    parent.children.push(child);
  }
}

describe('Collections Component & API Contract', () => {
  let originalDocument;
  let originalFetch;

  beforeEach(() => {
    originalDocument = globalThis.document;
    originalFetch = globalThis.fetch;

    globalThis.document = {
      createElement: (tag) => createMockElement(tag),
    };
  });

  afterEach(() => {
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
  });

  it('renders collection cards when API returns { collections: [...], total: 1 }', async () => {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => ({
        collections: [
          {
            id: 'essentials',
            slug: 'essentials',
            name: 'Essential Basics',
            description: 'Minimalist basics crafted with heavyweight cotton',
            image_url: 'https://images.unsplash.com/photo-1',
            display_order: 1,
          },
        ],
        total: 1,
      }),
    });

    const section = createCollectionsSection(() => {});
    await new Promise((r) => setTimeout(r, 20));

    const grid = section.querySelector('#collections-grid-container');
    assert.ok(grid.innerHTML.includes('Essential Basics'));
    assert.ok(grid.innerHTML.includes('data-collection="essentials"'));
    assert.ok(!grid.innerHTML.includes('Collections Unavailable'));
    assert.ok(!grid.innerHTML.includes('No Collections Configured'));
  });

  it('renders "No Collections Configured" when API returns { collections: [], total: 0 }', async () => {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => ({
        collections: [],
        total: 0,
      }),
    });

    const section = createCollectionsSection(() => {});
    await new Promise((r) => setTimeout(r, 20));

    const grid = section.querySelector('#collections-grid-container');
    assert.ok(grid.innerHTML.includes('No Collections Configured'));
    assert.ok(!grid.innerHTML.includes('Collections Unavailable'));
  });

  it('renders "Collections Unavailable" with retry button when API fails', async () => {
    globalThis.fetch = async () => {
      throw new Error('Network error');
    };

    const section = createCollectionsSection(() => {});
    await new Promise((r) => setTimeout(r, 20));

    const grid = section.querySelector('#collections-grid-container');
    assert.ok(grid.innerHTML.includes('Collections Unavailable'));
    assert.ok(grid.innerHTML.includes('btn-retry'));
  });

  it('populates filter tabs in FeaturedProducts from { collections: [...], total: 1 }', async () => {
    globalThis.fetch = async (url) => {
      const urlStr = String(url);
      if (urlStr.includes('/collections')) {
        return {
          ok: true,
          json: async () => ({
            collections: [
              { id: 'streetwear', name: 'Streetwear Core', slug: 'streetwear' },
            ],
            total: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          products: [],
          total: 0,
          page: 1,
          page_size: 20,
        }),
      };
    };

    const featured = createFeaturedProducts(() => {});
    await new Promise((r) => setTimeout(r, 20));

    const tabsContainer = featured.element.querySelector('#filter-tabs-container');
    assert.ok(tabsContainer.innerHTML.includes('All Products'));
    assert.ok(tabsContainer.innerHTML.includes('Streetwear Core'));
    assert.ok(tabsContainer.innerHTML.includes('data-filter="streetwear"'));
  });
});
