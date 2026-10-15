import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { collectVariant, mountCatalogSection } from '../src/components/admin/CatalogWorkspace.js';
import { fetchOwnerSession, uploadOwnerMedia } from '../src/utils/api.js';

const flush = () => new Promise(resolve => setTimeout(resolve, 30));
function install() {
  globalThis.document = { createElement: createMockElement, activeElement: null };
  globalThis.window = { confirm: () => true };
  return createMockElement('div');
}
function fill(form, name, value) { form.querySelector(`[name="${name}"]`).value = value; }

test('variant inputs preserve exact paisas and reject missing active prices/excess precision', () => {
  const row = install();
  row.innerHTML = '<input name="sku"><input name="size"><input name="color"><input name="price"><input name="variant_active" type="checkbox"><select name="availability"></select>';
  fill(row, 'sku', ' SAMPLE-SKU '); fill(row, 'size', ' M '); fill(row, 'color', ' Blue '); fill(row, 'availability', 'available'); fill(row, 'price', '123.45');
  assert.equal(collectVariant(row).price_minor, 12345);
  assert.equal(collectVariant(row).sku, 'SAMPLE-SKU');
  fill(row, 'price', '1.001'); assert.throws(() => collectVariant(row), /two decimal/);
  fill(row, 'price', ''); row.querySelector('[name="variant_active"]').checked = true;
  assert.throws(() => collectVariant(row), /price before activating/);
  row.querySelector('[name="variant_active"]').checked = false;
  assert.equal(collectVariant(row).price_minor, null);
});

test('atomic save rejection retains input and uses the unchanged product version on retry', async () => {
  const container = install(), calls = [];
  let version = 1, failMedia = true, dirty = false;
  const product = () => ({ id: 'sample-product', title: 'SAMPLE', slug: 'sample-product', status: 'draft', edit_version: version,
    variants: [], media: [], publication_requirements: [], collection_id: null });
  globalThis.fetch = async (url, options = {}) => {
    const payload = options.body ? JSON.parse(options.body) : null;
    calls.push({ url, payload });
    let data = {}, status = 200;
    if (url.includes('/admin/products?')) data = { products: [product()], total: 1 };
    else if (url === '/api/v1/admin/collections') data = { collections: [] };
    else if (url.includes('/admin/media?')) data = { assets: [], total: 0 };
    else if (url === '/api/v1/admin/products/sample-product') {
      if (options.method === 'POST') {
        assert.equal(payload.expected_version, version); assert.deepEqual(payload.media, []);
        if (failMedia) { status = 422; data = { detail: { message: 'SAMPLE media failure' } }; }
        else { version++; data = product(); }
      } else data = product();
    }
    return { ok: status < 400, status, json: async () => data };
  };
  const view = mountCatalogSection('products', container, { isCurrent: () => true, setDirty: value => { dirty = value; }, canLeave: () => true });
  await view.ready;
  container.querySelector('[data-edit-product]').click(); await flush();
  const form = container.querySelector('#catalog-product-form'); fill(form, 'title', 'SAMPLE preserved input');
  for (const name of ['slug', 'collection_id', 'badge', 'description', 'short_description', 'material', 'care', 'sizing', 'hero_benefit', 'hero_order']) fill(form, name, '');
  form.dispatchEvent({ type: 'input' });
  form.dispatchEvent({ type: 'submit', preventDefault() {} });
  form.dispatchEvent({ type: 'submit', preventDefault() {} }); await flush();
  assert.match(container.querySelector('#catalog-status').textContent, /SAMPLE media failure/);
  assert.equal(form.querySelector('[name="title"]').value, 'SAMPLE preserved input');
  assert.equal(dirty, true);
  assert.equal(calls.filter(c => c.url === '/api/v1/admin/products/sample-product' && c.payload).length, 1);
  failMedia = false;
  form.dispatchEvent({ type: 'submit', preventDefault() {} }); await flush();
  assert.equal(container.querySelector('#catalog-status').textContent, 'Product and media saved.');
  assert.equal(dirty, false);
  view.destroy();
});

test('destroyed catalog views ignore late responses', async () => {
  const container = install(); let release;
  globalThis.fetch = async url => ({ ok: true, status: 200, json: async () => url.includes('/products?') ? await new Promise(resolve => { release = resolve; }) : { collections: [] } });
  const view = mountCatalogSection('products', container, { isCurrent: () => true, setDirty() {}, canLeave: () => true });
  await flush(); view.destroy(); release({ products: [{ title: 'SAMPLE late private content' }], total: 1 }); await view.ready;
  assert.doesNotMatch(container.textContent, /late private/);
});

test('upload progress represents transport and resolves only on server acceptance; abort remains recoverable', async () => {
  let xhr;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ csrf_token: 'SAMPLE-token' }) });
  await fetchOwnerSession();
  globalThis.XMLHttpRequest = class {
    constructor() { xhr = this; this.headers = {}; this.upload = {}; }
    open(method, url) { this.method = method; this.url = url; }
    setRequestHeader(name, value) { this.headers[name] = value; }
    send(body) { this.body = body; }
    abort() { this.onabort(); }
  };
  const progress = [], controller = new AbortController();
  const promise = uploadOwnerMedia(new Blob(['SAMPLE'], { type: 'image/png' }), { onProgress: value => progress.push(value), signal: controller.signal });
  assert.equal(xhr.headers['X-CSRF-Token'], 'SAMPLE-token');
  assert.equal(xhr.headers['Content-Type'], undefined);
  xhr.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 });
  xhr.upload.onprogress({ lengthComputable: true, loaded: 10, total: 10 });
  assert.deepEqual(progress, [50, 100]);
  xhr.status = 201; xhr.responseText = JSON.stringify({ id: 'sample-media' }); xhr.onload();
  assert.equal((await promise).id, 'sample-media');
  const canceled = uploadOwnerMedia(new Blob(['SAMPLE']), { onProgress() {}, signal: controller.signal });
  controller.abort(); await assert.rejects(canceled, { name: 'AbortError' });
});
