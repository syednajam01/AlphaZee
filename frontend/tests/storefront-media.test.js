import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createMockElement} from './helpers/dom.js';
import {mountProductGallery} from '../src/components/ProductGallery.js';
import {mediaForVariant, variantImage} from '../src/utils/productMedia.js';
import {cart} from '../src/utils/cart.js';
import {createProductModal} from '../src/components/ProductModal.js';

const product = {id:'sample-m6', slug:'sample-old', title:'SAMPLE tee', image_url:'/primary.png', media:[
  {id:'a',role:'primary',kind:'image',url:'/primary.png',alt_text:'SAMPLE primary',variant_id:null},
  {id:'b',role:'gallery',kind:'image',url:'/blue.png',alt_text:'SAMPLE blue',variant_id:1},
  {id:'c',role:'gallery',kind:'image',url:'/green.png',alt_text:'SAMPLE green',variant_id:2},
  {id:'v',role:'gallery',kind:'video',url:'/sample.mp4',poster_url:'/poster.png',content_type:'video/mp4',variant_id:null},
]};
function install() {
  globalThis.document = {createElement:createMockElement};
  globalThis.window = {};
  return createMockElement('div');
}

test('gallery scopes variant images, uses controlled video/poster and pauses on replacement/destruction', () => {
  const host=install();
  assert.deepEqual(mediaForVariant(product,1).map(m=>m.id),['a','b','v']);
  assert.equal(variantImage(product,2),'/green.png');
  const view=mountProductGallery(host,product,1);
  assert.equal(host.querySelector('img').src,'/blue.png');
  host.querySelector('[data-gallery-index="2"]').click();
  const video=host.querySelector('video');
  assert.equal(video.poster,'/poster.png'); assert.equal(video.src,'/sample.mp4');
  assert.equal(video.preload,'none'); assert.equal(video.controls,true);
  let pauses=0; video.pause=()=>pauses++;
  host.querySelector('[data-gallery-index="0"]').click();
  assert.equal(pauses,1);
  assert.equal(host.querySelector('[data-gallery-index="0"]').getAttribute('aria-pressed'),'true');
  host.querySelector('img').dispatchEvent({type:'error'});
  assert.match(host.querySelector('[role="status"]').textContent,/could not load/);
  host.querySelector('[data-gallery-index="2"]').click();
  host.querySelector('video').pause=()=>pauses++;
  view.destroy(); assert.equal(pauses,2);
});

test('unsupported video stays unloaded and exposes recoverable feedback', () => {
  const host=install();
  const view=mountProductGallery(host,{...product,media:[{role:'gallery',kind:'video',url:'/bad.mov',content_type:'video/quicktime'}]},1);
  assert.equal(host.querySelector('video').src,undefined);
  assert.match(host.querySelector('[role="status"]').textContent,/unavailable/);
  view.destroy();
});

test('product detail defaults to an available exact variant and its scoped image', async () => {
  install(); document.body=createMockElement('body'); document.activeElement=null;
  const modal=createProductModal();
  await modal.open({...product, variants:[
    {id:2,size:'L',color:'Green',price:{minor:15025},availability:'unavailable'},
    {id:1,size:'M',color:'Blue',price:{minor:9995},availability:'available'},
  ]});
  assert.equal(modal.element.querySelector('#btn-modal-add-to-cart').disabled,false);
  assert.equal(modal.element.querySelector('.product-gallery-stage img').src,'/blue.png');
  modal.close();
});

test('cart uses stable identity after slug edits and updates exact price, details and variant image', async () => {
  install(); cart.clear(); const calls=[];
  cart.addItem({variant_id:1,product_id:product.id,slug:product.slug,title:'Old title',price_minor:100});
  globalThis.fetch=async (url,options)=> {calls.push({url,options}); return {ok:true,json:async()=>({...product,slug:'sample-new',title:'SAMPLE updated',variants:[{id:1,sku:'SAMPLE-BLUE',size:'M',color:'Blue',price:{minor:12345},availability:'available'}]})};};
  await cart.reconcileWithApi(); const item=cart.getState().items[0];
  assert.match(calls[0].url,/catalog\/products\/sample-m6$/); assert.equal(calls[0].options.cache,'no-store');
  assert.equal(item.slug,'sample-new'); assert.equal(item.variant_id,1); assert.equal(item.title,'SAMPLE updated');
  assert.equal(item.price_minor,12345); assert.equal(item.image_url,'/blue.png'); assert.equal(item.is_available,true);
  globalThis.fetch=async()=>({ok:true,json:async()=>({...product,variants:[]})});
  await cart.reconcileWithApi(); assert.equal(cart.getState().hasUnavailable,true);
  assert.equal(cart.getState().items[0].variant_id,1); cart.clear();
});

test('legacy slug resolving to a different product never replaces the saved variant', async () => {
  install(); cart.clear(); cart.addItem({variant_id:1,slug:'sample-old',price_minor:100});
  globalThis.fetch=async()=>({ok:true,json:async()=>({id:'sample-other',slug:'sample-old',variants:[{id:2,price:{minor:100},availability:'available'}]})});
  await cart.reconcileWithApi();
  assert.equal(cart.getState().hasUnavailable,true); assert.equal(cart.getState().items[0].variant_id,1); cart.clear();
});

test('items added during reconciliation remain unverified until their own refresh', async () => {
  install(); cart.clear(); cart.addItem({variant_id:1,product_id:product.id,price_minor:100});
  let finish; globalThis.fetch=()=>new Promise(resolve=>{finish=resolve;});
  const pending=cart.reconcileWithApi();
  cart.addItem({variant_id:2,product_id:'sample-other',price_minor:100});
  finish({ok:true,json:async()=>({...product,variants:[{id:1,price:{minor:100},availability:'available'}]})});
  await pending;
  assert.equal(cart.getState().items.find(i=>i.variant_id===2).availability,'unverified'); cart.clear();
});
