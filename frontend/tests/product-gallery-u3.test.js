import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { mountProductGallery } from '../src/components/ProductGallery.js';

const sampleProductWithMultiMedia = {
  id: 'prod-multi',
  slug: 'streetwear-tee',
  title: 'Streetwear Heavyweight Tee',
  media: [
    { id: 'm1', role: 'primary', kind: 'image', url: '/images/tee-front.png', alt_text: 'Front view' },
    { id: 'm2', role: 'gallery', kind: 'image', url: '/images/tee-back.png', alt_text: 'Back view' },
    { id: 'm3', role: 'gallery', kind: 'video', url: '/videos/tee-look.mp4', poster_url: '/images/tee-poster.png', content_type: 'video/mp4' },
  ],
  variants: [
    { id: 10, sku: 'TEE-BLK', size: 'M', color: 'Black', price_minor: 300000, availability: 'available' }
  ]
};

function setupTestHost() {
  function makeMock(tag) {
    const el = createMockElement(tag);
    el.remove = function() {
      if (this.parentElement && this.parentElement.children) {
        const idx = this.parentElement.children.indexOf(this);
        if (idx !== -1) this.parentElement.children.splice(idx, 1);
      }
    };
    return el;
  }
  const body = makeMock('body');
  body.style = {};
  globalThis.document = {
    createElement: makeMock,
    body,
    addEventListener(event, fn) {
      if (!this._listeners) this._listeners = {};
      if (!this._listeners[event]) this._listeners[event] = [];
      this._listeners[event].push(fn);
    },
    removeEventListener(event, fn) {
      if (!this._listeners || !this._listeners[event]) return;
      this._listeners[event] = this._listeners[event].filter(f => f !== fn);
    },
    dispatchEvent(event) {
      const type = event.type || event;
      const fns = this._listeners?.[type] || [];
      fns.forEach(fn => fn(event));
    }
  };
  globalThis.window = {};
  return makeMock('div');
}

test('U3 Gallery: Next and Prev navigation controls update active media and counter', () => {
  const host = setupTestHost();
  const gallery = mountProductGallery(host, sampleProductWithMultiMedia, 10);

  const prevBtn = host.querySelector('#gallery-prev-btn');
  const nextBtn = host.querySelector('#gallery-next-btn');
  const counterCurrent = host.querySelector('.gallery-current-num');
  const counterTotal = host.querySelector('.gallery-total-num');

  assert.ok(prevBtn);
  assert.ok(nextBtn);
  assert.equal(counterCurrent.textContent, '1');
  assert.equal(counterTotal.textContent, '3');
  assert.equal(host.querySelector('img').src, '/images/tee-front.png');

  // Click Next
  nextBtn.click();
  assert.equal(counterCurrent.textContent, '2');
  assert.equal(host.querySelector('img').src, '/images/tee-back.png');

  // Click Next again -> reaches video (slide 3)
  nextBtn.click();
  assert.equal(counterCurrent.textContent, '3');
  const video = host.querySelector('video');
  assert.ok(video);
  assert.equal(video.src, '/videos/tee-look.mp4');

  // Click Prev -> back to slide 2
  prevBtn.click();
  assert.equal(counterCurrent.textContent, '2');
  assert.equal(host.querySelector('img').src, '/images/tee-back.png');

  gallery.destroy();
});

test('U3 Gallery: Keyboard arrow navigation on stage moves slides and wraps circularly', () => {
  const host = setupTestHost();
  const gallery = mountProductGallery(host, sampleProductWithMultiMedia, 10);

  const stage = host.querySelector('.product-gallery-stage');
  const counterCurrent = host.querySelector('.gallery-current-num');

  // Initial is slide 1
  assert.equal(counterCurrent.textContent, '1');

  // ArrowRight -> slide 2
  stage.dispatchEvent({ type: 'keydown', key: 'ArrowRight', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '2');

  // ArrowRight -> slide 3
  stage.dispatchEvent({ type: 'keydown', key: 'ArrowRight', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '3');

  // ArrowRight wraps to slide 1
  stage.dispatchEvent({ type: 'keydown', key: 'ArrowRight', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '1');

  // ArrowLeft wraps to last slide (3)
  stage.dispatchEvent({ type: 'keydown', key: 'ArrowLeft', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '3');

  // Home key jumps to slide 1
  stage.dispatchEvent({ type: 'keydown', key: 'Home', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '1');

  // End key jumps to slide 3
  stage.dispatchEvent({ type: 'keydown', key: 'End', preventDefault() {} });
  assert.equal(counterCurrent.textContent, '3');

  gallery.destroy();
});

test('U3 Gallery: Lightbox image enlargement opens on zoom click and closes on Escape', () => {
  const host = setupTestHost();
  const gallery = mountProductGallery(host, sampleProductWithMultiMedia, 10);

  const zoomBtn = host.querySelector('#gallery-zoom-btn');
  assert.ok(zoomBtn);

  // Click zoom button to open lightbox
  zoomBtn.click();

  const lightbox = document.body.querySelector('#gallery-lightbox');
  assert.ok(lightbox);
  assert.ok(document.body.classList.contains('lightbox-open'));
  assert.equal(document.body.style.overflow, 'hidden');

  const enlargedImg = lightbox.querySelector('.gallery-lightbox-img');
  assert.ok(enlargedImg);
  assert.equal(enlargedImg.src, '/images/tee-front.png');

  // Press Escape to close lightbox
  document.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault() {} });

  assert.equal(document.body.querySelector('#gallery-lightbox'), null);
  assert.ok(!document.body.classList.contains('lightbox-open'));
  assert.equal(document.body.style.overflow, '');

  gallery.destroy();
});

test('U3 Gallery: Touch swipe simulation advances slides when horizontal intent dominates', () => {
  const host = setupTestHost();
  const gallery = mountProductGallery(host, sampleProductWithMultiMedia, 10);

  const stage = host.querySelector('.product-gallery-stage');
  const counterCurrent = host.querySelector('.gallery-current-num');

  assert.equal(counterCurrent.textContent, '1');

  // Simulate swipe left (deltaX = -60px, deltaY = 5px) -> next slide
  stage.dispatchEvent({ type: 'touchstart', touches: [{ clientX: 200, clientY: 150 }] });
  stage.dispatchEvent({ type: 'touchmove', touches: [{ clientX: 140, clientY: 155 }] });
  stage.dispatchEvent({ type: 'touchend' });

  assert.equal(counterCurrent.textContent, '2');

  // Simulate vertical scroll (deltaX = 10px, deltaY = 80px) -> does NOT change slide
  stage.dispatchEvent({ type: 'touchstart', touches: [{ clientX: 200, clientY: 150 }] });
  stage.dispatchEvent({ type: 'touchmove', touches: [{ clientX: 210, clientY: 230 }] });
  stage.dispatchEvent({ type: 'touchend' });

  assert.equal(counterCurrent.textContent, '2');

  gallery.destroy();
});

test('U3 Gallery: Visibility change pauses playing video on tab hide', () => {
  const host = setupTestHost();
  const gallery = mountProductGallery(host, sampleProductWithMultiMedia, 10);

  // Jump to video slide
  host.querySelector('[data-gallery-index="2"]').click();
  const video = host.querySelector('video');
  assert.ok(video);

  let pauseCalls = 0;
  video.pause = () => { pauseCalls++; };

  // Tab hidden
  document.hidden = true;
  document.dispatchEvent({ type: 'visibilitychange' });

  assert.equal(pauseCalls, 1);

  gallery.destroy();
});
