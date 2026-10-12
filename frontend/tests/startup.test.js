import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { startStorefront } from '../src/utils/startup.js';

test('startup initializes when the document is already ready', async () => {
  let calls = 0;
  await startStorefront(async () => ({ initApp() { calls++; } }), { readyState: 'complete' });
  assert.equal(calls, 1);
});

test('startup waits for DOMContentLoaded when necessary', async () => {
  let start;
  let calls = 0;
  startStorefront(async () => ({ initApp() { calls++; } }), {
    readyState: 'loading', addEventListener(type, handler, options) {
      assert.equal(type, 'DOMContentLoaded');
      assert.equal(options.once, true);
      start = handler;
    },
  });
  assert.equal(calls, 0);
  await start();
  assert.equal(calls, 1);
});

test('failed module load or component construction displays a working reload action', async () => {
  const originalError = console.error;
  console.error = () => {};
  try {
    for (const load of [async () => { throw new Error('module unavailable'); }, async () => ({ initApp() { throw new Error('constructor failed'); } })]) {
      const app = createMockElement('div');
      let reloaded = false;
      await startStorefront(load, { readyState: 'complete', getElementById: () => app,
        defaultView: { location: { reload() { reloaded = true; } } } });
      assert.match(app.textContent, /Unable to open the store/);
      app.querySelector('#retry-store-startup').click();
      assert.ok(reloaded);
    }
  } finally { console.error = originalError; }
});
