import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { createAdminConsoleModal } from '../src/components/AdminConsole.js';

const flush = () => new Promise(resolve => setTimeout(resolve, 10));

test('owner UI signs in, restores sessions, handles expiry and confirms logout on the server', async () => {
  const doc = createMockElement('document');
  doc.body = createMockElement('body');
  doc.createElement = createMockElement;
  doc.activeElement = doc.body;
  globalThis.document = doc;
  const storage = new Map([['alphazee_admin_key', 'obsolete-key']]);
  globalThis.window = { sessionStorage: { removeItem: key => storage.delete(key) },
    localStorage: { removeItem: key => storage.delete(key) } };
  let signedIn = false;
  let failLogout = false;
  let mutateHeaders;
  globalThis.fetch = async (url, options = {}) => {
    let status = 200;
    let data = {};
    if (url.endsWith('/auth/login')) {
      const body = JSON.parse(options.body);
      signedIn = body.username === 'sample_owner' && body.password === 'SAMPLE-password';
      status = signedIn ? 200 : 401;
      data = signedIn ? { username: 'sample_owner', csrf_token: 'SAMPLE-csrf' } : { detail: 'Invalid username or password' };
    } else if (url.endsWith('/auth/logout')) {
      mutateHeaders = options.headers;
      if (failLogout) { status = 503; data = { detail: 'Offline' }; }
      else signedIn = false;
    } else if (!signedIn) { status = 401; data = { detail: 'Invalid or missing owner session' }; }
    else if (url.endsWith('/auth/session')) data = { username: 'sample_owner', csrf_token: 'SAMPLE-csrf' };
    return { ok: status === 200, status, json: async () => data };
  };
  const first = createAdminConsoleModal();
  doc.body.appendChild(first.element);
  await first.open();
  assert.equal(storage.has('alphazee_admin_key'), false);
  assert.ok(first.element.querySelector('#admin-auth-form'));
  assert.equal(first.element.querySelector('#admin-auth-key-input'), null);
  first.element.querySelector('#admin-username').value = 'sample_owner';
  first.element.querySelector('#admin-password').value = 'wrong';
  first.element.querySelector('#admin-auth-form').dispatchEvent({ type: 'submit', preventDefault() {} });
  await flush();
  assert.match(first.element.querySelector('#admin-login-error').textContent, /Invalid username/);
  assert.equal(first.element.querySelector('#admin-password').value, '');
  first.element.querySelector('#admin-password').value = 'SAMPLE-password';
  first.element.querySelector('#admin-auth-form').dispatchEvent({ type: 'submit', preventDefault() {} });
  await flush();
  assert.equal(first.element.querySelector('#admin-auth-form'), null);
  assert.equal(first.element.querySelector('#btn-admin-logout').hidden, false);

  // A new console instance recovers CSRF/session state from the server.
  first.close();
  const restored = createAdminConsoleModal();
  doc.body.appendChild(restored.element);
  await restored.open();
  assert.equal(restored.element.querySelector('#admin-auth-form'), null);
  failLogout = true;
  restored.element.querySelector('#btn-admin-logout').click();
  await flush();
  assert.match(restored.element.querySelector('#admin-session-message').textContent, /Could not sign out/);
  assert.equal(restored.element.querySelector('#btn-admin-logout').hidden, false);
  failLogout = false;
  restored.element.querySelector('#btn-admin-logout').click();
  await flush();
  assert.equal(mutateHeaders['X-CSRF-Token'], 'SAMPLE-csrf');
  assert.ok(restored.element.querySelector('#admin-auth-form'));
  assert.equal(storage.size, 0);
  signedIn = true;
  await restored.open();
  signedIn = false;
  restored.element.querySelector('#btn-refresh-admin-tab').click();
  await flush();
  assert.ok(restored.element.querySelector('#admin-auth-form'));
  assert.match(restored.element.querySelector('#admin-session-message').textContent, /session has ended/i);
  restored.close();
});
