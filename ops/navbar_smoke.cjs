// Browser-only SAMPLE responses. This test never writes to any application DB.
const { chromium, webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const origin = process.env.SMOKE_ORIGIN || 'http://127.0.0.1:8080';
const product = { id: 'sample-nav', slug: 'sample-nav', title: 'SAMPLE navbar tee', description: 'SAMPLE browser only', image_url: '/images/storefront-empty.svg', availability: 'available', min_price_minor: 100000,
  variants: [{ id: 991, sku: 'SAMPLE-NAV', size: 'M', color: 'Ink', price_minor: 100000, availability: 'available', is_active: true }], media: [] };
const collection = { id: 'sample-nav', slug: 'sample-nav', name: 'SAMPLE collection', description: 'SAMPLE browser only', image_url: '/images/storefront-empty.svg' };
(async () => {
  const engine = process.env.NAVBAR_ENGINE === 'webkit' ? webkit : chromium;
  const browser = await engine.launch(engine === chromium ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined } : {});
  const results = [];
  try {
    for (const width of (process.env.NAVBAR_WIDTHS ? process.env.NAVBAR_WIDTHS.split(',').map(Number) : [360, 390, 768, 1440])) {
      const context = await browser.newContext({ viewport: { width, height: 844 }, reducedMotion: process.env.NAVBAR_MOTION === 'normal' ? 'no-preference' : 'reduce', ...(width < 768 ? { isMobile: true, hasTouch: true } : {}) });
      const page = await context.newPage();
      const errors = [];
      let announcementMode = 'normal';
      page.on('pageerror', e => errors.push(e.message));
      await page.route('https://fonts.googleapis.com/**', route => route.fulfill({ contentType: 'text/css', body: '' }));
      await page.route('https://fonts.gstatic.com/**', route => route.abort());
      await page.route('**/api/v1/**', route => {
        assert.equal(route.request().method(), 'GET', 'navbar smoke must never mutate application state');
        const path = new URL(route.request().url()).pathname;
        let body = {}, status = 200;
        if (path.includes('/auth/')) { body = { detail: 'Not signed in' }; status = 401; }
        else if (path.endsWith('/storefront/capabilities')) body = { checkout_enabled: false, test_mode: false, payment_methods: ['cod'] };
        else if (path.endsWith('/settings')) body = { announcement_banner_enabled: announcementMode !== 'disabled', announcement_banner_text: announcementMode === 'long' ? 'SAMPLE shipping announcement with a deliberately long delivery message that wraps on narrow mobile screens. '.repeat(3) : 'SAMPLE shipping announcement', accent_color: '#243f31' };
        else if (path.endsWith('/products/sample-nav')) body = product;
        else if (path.endsWith('/collections/sample-nav')) body = collection;
        else if (path.endsWith('/products')) body = { products: [product], total: 1 };
        else if (path.endsWith('/collections')) body = { collections: [collection], total: 1 };
        else if (path.endsWith('/hero/slides')) body = { slides: [] };
        else if (path.endsWith('/products/hero')) body = [];
        return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
      });
      for (const path of (process.env.NAVBAR_PATHS ? process.env.NAVBAR_PATHS.split(',') : ['/', '/products', '/collections', '/collections/sample-nav', '/products/sample-nav'])) {
        await page.waitForLoadState('networkidle');
        await page.goto(origin + path);
        await page.locator('#btn-cart').waitFor();
        await page.waitForFunction(() => document.querySelector('.announcement-bar')?.textContent.includes('SAMPLE shipping'));
        await page.waitForFunction(() => document.querySelector('#site-header').offsetHeight === document.querySelector('.header-panel').offsetHeight);
        // Each real route may be shorter than the viewport with this tiny fixture.
        // Extend main for scrolling only, without changing header geometry.
        await page.locator('#main-content').evaluate(el => { el.style.minHeight = '2400px'; });
        await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo({ top: 0, behavior: 'instant' }); });
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'top');
        const beforeHeight = await page.locator('#site-header').evaluate(el => el.offsetHeight);
        await page.evaluate(() => window.scrollTo({ top: 100, behavior: 'instant' }));
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'compact');
        await page.waitForFunction(() => getComputedStyle(document.querySelector('.header-panel')).opacity === '0');
        const compact = await page.evaluate(() => {
          const header = document.querySelector('#site-header'), panel = header.querySelector('.header-panel'), logo = header.querySelector('.brand-logo-link'), box = logo.getBoundingClientRect();
          return { inert: panel.inert, opacity: getComputedStyle(panel).opacity, x: box.x, y: box.y, width: box.width, height: box.height, headerHeight: header.offsetHeight, labHeight: document.querySelector('.checkout-lab-notice')?.offsetHeight || 0, overflow: document.documentElement.scrollWidth > innerWidth };
        });
        assert(compact.inert); assert.equal(compact.opacity, '0'); assert.equal(compact.headerHeight, beforeHeight);
        assert(compact.x >= 0 && compact.x <= 24 && compact.y >= compact.labHeight && compact.y <= compact.labHeight + 16);
        assert(compact.width >= 44 && compact.height >= 44); assert(!compact.overflow);
        assert(await page.evaluate(() => !document.elementFromPoint(innerWidth - 24, (document.querySelector('.checkout-lab-notice')?.offsetHeight || 0) + 40)?.closest('#site-header')), 'hidden header must not intercept the page');
        await page.evaluate(() => window.scrollTo({ top: 180, behavior: 'instant' }));
        await page.waitForTimeout(50);
        assert.equal(await page.locator('#site-header').getAttribute('data-nav-state'), 'compact');
        await page.evaluate(() => window.scrollTo({ top: 168, behavior: 'instant' }));
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'expanded');
        await page.waitForFunction(() => getComputedStyle(document.querySelector('.header-panel')).opacity === '1');
        await page.locator('#btn-cart').click();
        await page.locator('#cart-drawer.is-open').waitFor();
        await page.locator('#cart-close-btn').click();
        assert.equal(await page.locator('.header-panel').getAttribute('aria-hidden'), 'false');
        if (width < 1100) {
          await page.locator('#btn-mobile-menu').click();
          await page.waitForFunction(() => document.querySelector('#btn-mobile-menu').getAttribute('aria-expanded') === 'true');
          await page.keyboard.press('Escape');
          await page.waitForFunction(() => document.querySelector('#btn-mobile-menu').getAttribute('aria-expanded') === 'false');
        } else {
          await page.locator('#nav-track-order').click();
          await page.locator('#tracking-modal.is-open').waitFor();
          await page.locator('#tracking-close-btn').click();
        }
        // Keyboard focus must reveal the panel before its controls receive Tab.
        await page.locator('#main-content').click({ position: { x: 10, y: 300 } });
        await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo({ top: 300, behavior: 'instant' }); });
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'compact');
        await page.locator('#header-logo-slot a').focus();
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'expanded');
        await page.keyboard.press('Tab');
        assert(await page.locator('.header-panel').evaluate(el => el.contains(document.activeElement)));
        results.push({ width, path, pass: true });
        await page.waitForLoadState('networkidle');
      }
      if (width === 390 && engine === chromium) {
        await page.evaluate(() => { document.activeElement?.blur(); document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo({ top: 0, behavior: 'instant' }); });
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'top');
        const touch = await context.newCDPSession(page);
        async function swipe(start, end) {
          await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 180, y: start, id: 1 }] });
          for (let step = 1; step <= 10; step++) {
            await touch.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 180, y: start + (end - start) * step / 10, id: 1 }] });
            await page.waitForTimeout(25);
          }
          await touch.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
        }
        await swipe(650, 350);
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'compact');
        await page.waitForTimeout(500);
        await swipe(400, 550);
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'expanded');
        await touch.detach();
      }
      if (width === 1440) {
        await page.evaluate(() => document.activeElement?.blur());
        await page.mouse.wheel(0, 200);
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'compact');
        await page.mouse.wheel(0, -50);
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'expanded');
      }
      for (const variant of ['disabled', 'long']) {
        announcementMode = variant;
        await page.goto(origin + '/');
        await page.locator('#btn-cart').waitFor();
        if (variant === 'long') {
          await page.waitForFunction(() => document.querySelector('.announcement-bar')?.textContent.includes('wraps'));
          await page.waitForFunction(() => document.querySelector('#site-header').offsetHeight === document.querySelector('.header-panel').offsetHeight);
          const sizes = await page.evaluate(() => ({ header: document.querySelector('#site-header').offsetHeight, panel: document.querySelector('.header-panel').offsetHeight, overflow: document.documentElement.scrollWidth > innerWidth }));
          assert.equal(sizes.header, sizes.panel); assert(!sizes.overflow);
        } else {
          assert.equal(await page.locator('.announcement-bar').isVisible(), false);
        }
        await page.waitForLoadState('networkidle');
      }
      if (process.env.NAVBAR_ARTIFACTS) {
        fs.mkdirSync(process.env.NAVBAR_ARTIFACTS, { recursive: true });
        await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo({ top: 400, behavior: 'instant' }); });
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'compact');
        await page.screenshot({ path: `${process.env.NAVBAR_ARTIFACTS}/${width}-compact.png` });
        await page.evaluate(() => window.scrollTo({ top: 380, behavior: 'instant' }));
        await page.waitForFunction(() => document.querySelector('#site-header').dataset.navState === 'expanded');
        await page.screenshot({ path: `${process.env.NAVBAR_ARTIFACTS}/${width}-expanded.png` });
      }
      assert.deepEqual(errors, []);
      console.log(`PASS: navbar ${process.env.NAVBAR_ENGINE || 'chromium'} ${width}px, five routes and announcement variants`);
      await context.close();
    }
    console.log(JSON.stringify({ engine: process.env.NAVBAR_ENGINE || 'chromium', scenarios: results.length, results }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
