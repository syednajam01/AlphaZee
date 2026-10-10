import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isValidMediaUrl, sanitizeMediaUrl, createSafeImageElement, escapeHtml } from '../src/utils/dom.js';

describe('DOM & Media URL Security (Attribute Injection Prevention)', () => {
  it('accepts legitimate http, https, and root-relative URLs', () => {
    assert.strictEqual(isValidMediaUrl('https://cdn.alphazee.pk/products/tee-1.jpg'), true);
    assert.strictEqual(isValidMediaUrl('http://127.0.0.1:8000/media/hoodie.jpg'), true);
    assert.strictEqual(isValidMediaUrl('/assets/images/logo.svg'), true);
    assert.strictEqual(isValidMediaUrl('/products/oversized-tee.jpg'), true);
  });

  it('rejects dangerous protocols (javascript, data, vbscript)', () => {
    assert.strictEqual(isValidMediaUrl('javascript:alert(1)'), false);
    assert.strictEqual(isValidMediaUrl('JAVASCRIPT:alert(document.cookie)'), false);
    assert.strictEqual(isValidMediaUrl('data:text/html,<script>alert(1)</script>'), false);
    assert.strictEqual(isValidMediaUrl('vbscript:msgbox("xss")'), false);
  });

  it('rejects crafted URLs containing quotes, angle brackets, or control characters that could break out of HTML attributes', () => {
    // Double quote attribute breakout
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg" onerror="alert(1)'), false);
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg" onmouseover="alert(1)" class="injected'), false);

    // Single quote attribute breakout
    assert.strictEqual(isValidMediaUrl("https://example.com/pic.jpg' onerror='alert(1)"), false);

    // Tag breakout
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg><script>alert(1)</script>'), false);
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg<img src=x onerror=alert(1)>'), false);

    // Backticks and newlines
    assert.strictEqual(isValidMediaUrl('https://example.com/`alert(1)`'), false);
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg\nonerror=alert(1)'), false);
    assert.strictEqual(isValidMediaUrl('https://example.com/pic.jpg\r\n'), false);

    // Protocol-relative evasion
    assert.strictEqual(isValidMediaUrl('//malicious.com/exploit.jpg'), false);
  });

  it('sanitizeMediaUrl safely substitutes fallback when provided injection URL', () => {
    const malicious = 'https://example.com/pic.jpg" onerror="alert(1)';
    const fallback = 'https://cdn.alphazee.pk/fallback.jpg';

    const result = sanitizeMediaUrl(malicious, fallback);
    assert.strictEqual(result, fallback);
  });

  it('createSafeImageElement sets attributes via DOM properties without attribute injection', () => {
    // Mock minimal DOM document if running in Node
    const originalDocument = global.document;
    const mockEl = {
      tagName: 'IMG',
      src: '',
      alt: '',
      className: '',
      loading: '',
      width: undefined,
      height: undefined,
    };
    global.document = {
      createElement: () => mockEl,
    };

    try {
      const img = createSafeImageElement({
        src: 'https://example.com/pic.jpg" onerror="alert(1)',
        alt: 'Test Product" onload="alert(2)',
        className: 'product-card-img',
        fallback: 'https://cdn.alphazee.pk/fallback.jpg',
        width: 320,
        height: 320,
        loading: 'lazy',
      });

      // Src should be sanitized to fallback
      assert.strictEqual(img.src, 'https://cdn.alphazee.pk/fallback.jpg');
      // Alt is set as a raw property value (safe in DOM, not interpolated in HTML string)
      assert.strictEqual(img.alt, 'Test Product" onload="alert(2)');
      assert.strictEqual(img.className, 'product-card-img');
      assert.strictEqual(img.width, 320);
      assert.strictEqual(img.height, 320);
      assert.strictEqual(img.loading, 'lazy');
    } finally {
      global.document = originalDocument;
    }
  });

  it('escapeHtml correctly encodes HTML special characters', () => {
    assert.strictEqual(escapeHtml('<script>alert("XSS & \'more\'")</script>'), '&lt;script&gt;alert(&quot;XSS &amp; &#39;more&#39;&quot;)&lt;/script&gt;');
    assert.strictEqual(escapeHtml(null), '');
    assert.strictEqual(escapeHtml(undefined), '');
  });
});
