import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHero } from '../src/components/Hero.js';

// Minimal DOM mock with media element and hierarchy support
function createMockElement(tagName) {
  const el = {
    tagName: tagName.toUpperCase(),
    className: '',
    id: '',
    src: '',
    poster: '',
    muted: false,
    loop: false,
    playsInline: false,
    paused: true,
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
    removeAttribute(name) {
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
    play() {
      this.paused = false;
      return Promise.resolve();
    },
    pause() {
      this.paused = true;
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

  let _className = '';
  el.classList = {
    _classes: new Set(),
    add(cls) {
      this._classes.add(cls);
      _className = Array.from(this._classes).join(' ');
    },
    remove(cls) {
      this._classes.delete(cls);
      _className = Array.from(this._classes).join(' ');
    },
    contains(cls) {
      return this._classes.has(cls);
    },
    toggle(cls, force) {
      if (force === undefined) {
        if (this._classes.has(cls)) this._classes.delete(cls);
        else this._classes.add(cls);
      } else if (force) {
        this._classes.add(cls);
      } else {
        this._classes.delete(cls);
      }
      _className = Array.from(this._classes).join(' ');
    },
  };

  Object.defineProperty(el, 'className', {
    get() {
      return _className;
    },
    set(val) {
      _className = val || '';
      el.classList._classes = new Set(_className.trim().split(/\s+/).filter(Boolean));
    },
  });

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
    if (match[0].startsWith('<!--')) continue;
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

describe('Hero Carousel Component & Media Streaming', () => {
  let originalDocument;
  let originalFetch;
  let originalMatchMedia;

  beforeEach(() => {
    originalDocument = global.document;
    originalFetch = global.fetch;
    originalMatchMedia = global.window ? global.window.matchMedia : undefined;

    global.document = {
      createElement: (tag) => createMockElement(tag),
      body: createMockElement('body'),
    };

    global.window = {
      matchMedia: () => ({ matches: false }),
    };
    try {
      Object.defineProperty(global.navigator, 'connection', {
        value: { saveData: false },
        configurable: true,
        writable: true,
      });
    } catch {
      // navigator.connection may already exist or cannot be configured
    }
  });

  afterEach(() => {
    global.document = originalDocument;
    global.fetch = originalFetch;
    try {
      delete global.navigator.connection;
    } catch {}
  });

  it('renders hero carousel with on-demand video loading and pauses inactive videos', async () => {
    const mockHeroItems = [
      {
        id: 'hero-1',
        slug: 'heavyweight-tee',
        title: 'Heavyweight Boxy Tee',
        hero_benefit: 'Engineered heavyweight drape',
        hero_poster_url: 'https://cdn.alphazee.pk/tee-poster.jpg',
        hero_video_url: 'https://cdn.alphazee.pk/tee-video.mp4',
        min_price: { minor: 450000, currency: 'PKR', formatted: 'PKR 4,500' },
      },
      {
        id: 'hero-2',
        slug: 'architectural-hoodie',
        title: 'Architectural Hoodie',
        hero_benefit: '500 GSM French Terry Fleece',
        hero_poster_url: 'https://cdn.alphazee.pk/hoodie-poster.jpg',
        hero_video_url: 'https://cdn.alphazee.pk/hoodie-video.mp4',
        min_price: { minor: 850000, currency: 'PKR', formatted: 'PKR 8,500' },
      },
    ];

    global.fetch = async (url) => {
      if (url.includes('/api/v1/products/hero')) {
        return {
          ok: true,
          status: 200,
          json: async () => mockHeroItems,
        };
      }
      return { ok: false, status: 404 };
    };

    let clickedSlug = null;
    const heroSection = createHero((slug) => {
      clickedSlug = slug;
    });

    // Wait for loadHero async fetch to finish and render
    await new Promise(resolve => setTimeout(resolve, 20));

    // Verify slides exist
    const slides = heroSection.querySelectorAll('.hero-slide');
    assert.strictEqual(slides.length, 2);
    assert.match(slides[0].innerHTML, /Heavyweight Boxy Tee/);
    assert.match(slides[0].innerHTML, /Engineered heavyweight drape/);
    assert.match(slides[0].innerHTML, /From PKR 4,500/);

    assert.match(slides[1].innerHTML, /Architectural Hoodie/);
    assert.match(slides[1].innerHTML, /500 GSM French Terry Fleece/);
    assert.match(slides[1].innerHTML, /From PKR 8,500/);

    // Verify video media elements and on-demand streaming
    const bgMedia = heroSection.querySelectorAll('.hero-bg-media');
    assert.strictEqual(bgMedia.length, 2);

    const video0 = bgMedia[0];
    const video1 = bgMedia[1];

    assert.strictEqual(video0.tagName, 'VIDEO');
    assert.strictEqual(video1.tagName, 'VIDEO');

    // Slide 0 is initially active -> video0.src is loaded and playing
    assert.strictEqual(video0.src, 'https://cdn.alphazee.pk/tee-video.mp4');
    assert.strictEqual(video0.paused, false, 'Slide 0 video should be playing initially');
    assert.strictEqual(video0.classList.contains('is-active'), true);

    // Slide 1 is initially inactive -> video1.dataset.videoSrc is saved, but video1.src is empty
    assert.strictEqual(video1.dataset.videoSrc, 'https://cdn.alphazee.pk/hoodie-video.mp4');
    assert.strictEqual(video1.src, '', 'Slide 1 video.src must not load before activation to save bandwidth');
    assert.strictEqual(video1.classList.contains('is-active'), false);

    // Navigate to slide 1 via next button
    const nextBtn = heroSection.querySelector('#hero-next');
    assert.ok(nextBtn, 'Next slide button should exist');
    nextBtn.click();

    // Now Slide 1 is active:
    // 1. video1.src should be populated on demand from dataset.videoSrc
    // 2. video1 should be playing
    assert.strictEqual(video1.src, 'https://cdn.alphazee.pk/hoodie-video.mp4');
    assert.strictEqual(video1.paused, false, 'Slide 1 video should be playing when activated');
    assert.strictEqual(video1.classList.contains('is-active'), true);

    // 3. video0 should now be paused and inactive
    assert.strictEqual(video0.paused, true, 'Slide 0 video must be paused when navigated away');
    assert.strictEqual(video0.classList.contains('is-active'), false);

    // Indicator should update
    const indicator = heroSection.querySelector('#hero-indicator');
    assert.ok(indicator);
    assert.strictEqual(indicator.textContent, '2 / 2');

    // CTA button click triggers product click callback
    const slide1Cta = slides[1].querySelector('.hero-cta-btn');
    assert.ok(slide1Cta);
    slide1Cta.click();
    assert.strictEqual(clickedSlug, 'architectural-hoodie');
    heroSection.destroy();
  });

  it('renders graceful brand fallback when API returns empty hero list', async () => {
    global.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => [],
    });

    const heroSection = createHero();
    await new Promise(resolve => setTimeout(resolve, 20));

    assert.match(heroSection.innerHTML, /Architectural Cuts/);
    assert.match(heroSection.innerHTML, /Explore Collection/);
    heroSection.destroy();
  });
});
