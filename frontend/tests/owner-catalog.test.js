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
  assert.equal(collectVariant(row).color, 'Blue');
  fill(row, 'color', '   ');
  assert.throws(() => collectVariant(row), /Color is required/);
  fill(row, 'color', 'Blue');
  fill(row, 'price', '1.001'); assert.throws(() => collectVariant(row), /two decimal/);
  fill(row, 'price', ''); row.querySelector('[name="variant_active"]').checked = true;
  assert.throws(() => collectVariant(row), /price before activating/);
  row.querySelector('[name="variant_active"]').checked = false;
  assert.equal(collectVariant(row).price_minor, null);

  // Test initial_stock collection and validation
  row.innerHTML = '<input name="sku"><input name="size"><input name="color"><input name="price"><input name="variant_active" type="checkbox"><select name="availability"></select><input name="initial_stock">';
  fill(row, 'sku', 'SAMPLE-SKU'); fill(row, 'size', 'XL'); fill(row, 'color', 'Black'); fill(row, 'availability', 'available'); fill(row, 'price', '150');
  fill(row, 'initial_stock', '15');
  assert.equal(collectVariant(row).initial_stock, 15);
  fill(row, 'initial_stock', '-5');
  assert.throws(() => collectVariant(row), /non-negative whole integer/);

  // Test wholesale cost_price collection and validation
  row.innerHTML = '<input name="sku"><input name="size"><input name="color"><input name="price"><input name="cost_price"><input name="variant_active" type="checkbox"><select name="availability"></select><input name="initial_stock">';
  fill(row, 'sku', 'SAMPLE-SKU-2'); fill(row, 'size', 'L'); fill(row, 'color', 'White'); fill(row, 'availability', 'available'); fill(row, 'price', '200'); fill(row, 'cost_price', '125.50');
  assert.equal(collectVariant(row).cost_price_minor, 12550);
  fill(row, 'cost_price', '10.999');
  assert.throws(() => collectVariant(row), /Wholesale cost price must be a nonnegative PKR amount/);
  fill(row, 'cost_price', '');
  assert.equal(collectVariant(row).cost_price_minor, null);
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

test('color-first variant builder groups variants by color and generates size variants with batch pricing', async () => {
  const container = install(), calls = [];
  const existingProduct = {
    id: 'sample-tee',
    title: 'Boxy Heavyweight Tee',
    slug: 'boxy-heavyweight-tee',
    status: 'draft',
    edit_version: 1,
    collection_id: null,
    variants: [
      { id: 101, sku: 'TEE-BLK-S', size: 'S', color: 'Black', price_minor: 350000, is_active: true, availability: 'available' },
      { id: 102, sku: 'TEE-BLK-M', size: 'M', color: 'Black', price_minor: 350000, is_active: true, availability: 'available' },
    ],
    media: [],
    publication_requirements: [],
  };
  globalThis.fetch = async (url, options = {}) => {
    const payload = options.body ? JSON.parse(options.body) : null;
    calls.push({ url, payload });
    let data = {}, status = 200;
    if (url.includes('/admin/products?')) data = { products: [existingProduct], total: 1 };
    else if (url === '/api/v1/admin/collections') data = { collections: [] };
    else if (url.includes('/admin/media?')) data = { assets: [], total: 0 };
    else if (url === '/api/v1/admin/products/sample-tee') {
      if (options.method === 'POST') {
        data = { ...existingProduct, ...payload, edit_version: 2 };
      } else {
        data = existingProduct;
      }
    }
    return { ok: status < 400, status, json: async () => data };
  };

  const view = mountCatalogSection('products', container, { isCurrent: () => true, setDirty() {}, canLeave: () => true });
  await view.ready;
  container.querySelector('[data-edit-product]').click();
  await flush();

  const colorCards = container.querySelectorAll('.color-group-card');
  assert.equal(colorCards.length, 1);
  assert.equal(colorCards[0].querySelector('.color-group-name').value, 'Black');

  // Verify existing variants S and M are loaded
  const existingVariants = colorCards[0].querySelectorAll('.catalog-variant');
  assert.equal(existingVariants.length, 2);
  assert.equal(existingVariants[0].dataset.size, 'S');
  assert.equal(existingVariants[1].dataset.size, 'M');

  // Click size L pill to add size L
  const pillL = [...colorCards[0].querySelectorAll('.size-pill')].find(p => p.dataset.size === 'L');
  assert.ok(pillL);
  assert.ok(pillL.classList.contains('is-inactive'));
  pillL.click();

  const updatedVariants = colorCards[0].querySelectorAll('.catalog-variant');
  assert.equal(updatedVariants.length, 3);
  assert.ok(pillL.classList.contains('is-active'));

  // Apply batch price to all sizes in Black
  const batchPriceInput = colorCards[0].querySelector('.color-batch-price');
  batchPriceInput.value = '3950';
  colorCards[0].querySelector('.btn-apply-batch-price').click();

  const priceInputs = colorCards[0].querySelectorAll('.catalog-variant input[name="price"]');
  priceInputs.forEach(inp => assert.equal(inp.value, '3950.00'));

  view.destroy();
});

test('delete draft deletes draft normally but blocks published products with unpublish warning', async () => {
  const container = install(), calls = [];
  let alerts = [];
  globalThis.window.alert = msg => alerts.push(msg);
  globalThis.window.confirm = () => true;

  const draftProduct = { id: 'draft-p1', title: 'Empty Draft', slug: null, status: 'draft', variants: [] };
  const pubProduct = { id: 'pub-p2', title: 'Published Hoodie', slug: 'pub-hoodie', status: 'published', variants: [] };
  let productList = [draftProduct, pubProduct];

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, method: options.method || 'GET' });
    let data = {}, status = 200;
    if (url.includes('/admin/products?')) {
      data = { products: productList, total: productList.length };
    } else if (url === '/api/v1/admin/collections') {
      data = { collections: [] };
    } else if (url === '/api/v1/admin/products/draft-p1' && options.method === 'DELETE') {
      productList = productList.filter(p => p.id !== 'draft-p1');
      data = { deleted: true, id: 'draft-p1' };
    }
    return { ok: status < 400, status, json: async () => data };
  };

  const view = mountCatalogSection('products', container, { isCurrent: () => true, setDirty() {}, canLeave: () => true });
  await view.ready;

  // 1. Attempt to delete published product
  const pubDeleteBtn = container.querySelector('[data-delete-product="pub-p2"]');
  assert.ok(pubDeleteBtn);
  pubDeleteBtn.click();
  await flush();
  assert.equal(calls.filter(c => c.method === 'DELETE').length, 0);
  assert.ok(alerts.some(a => a.includes('Make it unpublished first then delete')));
  assert.match(container.querySelector('#catalog-status').textContent, /Make it unpublished first then delete/);

  // 2. Delete empty draft product
  const draftDeleteBtn = container.querySelector('[data-delete-product="draft-p1"]');
  assert.ok(draftDeleteBtn);
  draftDeleteBtn.click();
  await flush();
  assert.equal(calls.filter(c => c.method === 'DELETE' && c.url.includes('draft-p1')).length, 1);
  assert.match(container.querySelector('#catalog-status').textContent, /Product deleted/);

  view.destroy();
});

test('delete collection unlinks products and deletes collection via admin UI', async () => {
  const container = install();
  const calls = [];
  globalThis.window.confirm = () => true;

  const col1 = { id: 'col-1', name: 'Winter Edit', slug: 'winter-edit', is_active: true, edit_version: 1 };
  let colList = [col1];

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, method: options.method || 'GET' });
    let data = {}, status = 200;
    if (url === '/api/v1/admin/collections') {
      data = { collections: colList, total: colList.length };
    } else if (url.includes('/admin/media')) {
      data = { assets: [], total: 0 };
    } else if (url === '/api/v1/admin/collections/col-1' && options.method === 'DELETE') {
      colList = [];
      status = 204;
    }
    return { ok: status < 400, status, json: async () => data };
  };

  const view = mountCatalogSection('collections', container, { isCurrent: () => true, setDirty() {}, canLeave: () => true });
  await view.ready;

  const delBtn = container.querySelector('[data-delete-collection="col-1"]');
  assert.ok(delBtn);
  delBtn.click();
  await flush();

  assert.equal(calls.filter(c => c.method === 'DELETE' && c.url.includes('col-1')).length, 1);
  assert.match(container.querySelector('#catalog-status').textContent, /Collection "Winter Edit" deleted/);

  view.destroy();
});

test('products list renders compact toolbar, front image thumbnail, slug, and 10-item pagination', async () => {
  const container = install();
  const calls = [];

  const sampleProducts = [
    {
      id: 'p-with-img',
      title: 'Silk Embroidered Kurta',
      slug: 'silk-kurta',
      status: 'published',
      image_url: 'https://alphazee.tech/media/sample.jpg',
      variants: [{ id: 1, sku: 'KURTA-BLK-M' }],
    },
    {
      id: 'p-no-img',
      title: 'Linen Casual Trouser',
      slug: 'linen-trouser',
      status: 'draft',
      image_url: null,
      variants: [],
    }
  ];

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, method: options.method || 'GET' });
    let data = {}, status = 200;
    if (url.includes('/admin/products?')) {
      data = { products: sampleProducts, total: 25, page: 1, page_size: 10 };
    } else if (url === '/api/v1/admin/collections') {
      data = { collections: [{ id: 'col-1', name: 'Summer 2026' }] };
    }
    return { ok: status < 400, status, json: async () => data };
  };

  const view = mountCatalogSection('products', container, { isCurrent: () => true, setDirty() {}, canLeave: () => true });
  await view.ready;

  // 1. Verify query parameter requested page_size=10
  const productFetchCall = calls.find(c => c.url.includes('/admin/products?'));
  assert.ok(productFetchCall);
  assert.match(productFetchCall.url, /page_size=10/);

  // 2. Verify compact toolbar
  assert.ok(container.querySelector('#catalog-new-product'));
  assert.ok(container.querySelector('.catalog-search-input'));
  assert.ok(container.querySelector('select[name="status"]'));
  assert.ok(container.querySelector('select[name="collection_id"]'));
  assert.match(container.querySelector('.catalog-total-pill').textContent, /25 products/);

  // 3. Verify product cards have thumbnail, title, slug, and action buttons
  const cards = container.querySelectorAll('.catalog-card');
  assert.equal(cards.length, 2);

  const firstCard = cards[0];
  const imgNode = firstCard.querySelector('.catalog-card-thumb');
  assert.ok(imgNode);
  assert.equal(imgNode.getAttribute('src'), 'https://alphazee.tech/media/sample.jpg');
  assert.match(firstCard.querySelector('.catalog-card-title').textContent, /Silk Embroidered Kurta/);
  assert.match(firstCard.querySelector('.catalog-card-slug').textContent, /\/silk-kurta/);
  assert.ok(firstCard.querySelector('[data-edit-product="p-with-img"]'));
  assert.ok(firstCard.querySelector('[data-delete-product="p-with-img"]'));

  const secondCard = cards[1];
  assert.ok(secondCard.querySelector('.catalog-card-thumb-empty'));
  assert.match(secondCard.querySelector('.catalog-card-title').textContent, /Linen Casual Trouser/);
  assert.match(secondCard.querySelector('.catalog-card-slug').textContent, /\/linen-trouser/);

  // 4. Verify pagination controls
  const prevBtn = container.querySelector('#catalog-products-prev');
  const nextBtn = container.querySelector('#catalog-products-next');
  assert.ok(prevBtn);
  assert.ok(nextBtn);
  assert.equal(prevBtn.disabled, true); // on page 1
  assert.equal(nextBtn.disabled, false); // total 25 > 10 items
  assert.match(container.querySelector('.catalog-page-indicator').textContent, /Page.*1.*of.*3/);

  view.destroy();
});
