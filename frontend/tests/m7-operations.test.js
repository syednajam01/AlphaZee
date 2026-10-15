import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createMockElement} from './helpers/dom.js';
import {orderEvidence,mountFundsReview,mountAccessRecovery} from '../src/components/admin/OrderEvidence.js';
import {createAdminConsoleModal} from '../src/components/AdminConsole.js';
import {confirmSupplierAcceptance,markPaymentInstructionsSent,resolvePaymentReview,deleteAdminCoupon} from '../src/utils/api.js';
const tick=()=>new Promise(resolve=>setTimeout(resolve,35));
function install(){const doc=createMockElement('document');doc.body=createMockElement('body');doc.createElement=createMockElement;doc.activeElement=doc.body;globalThis.document=doc;globalThis.window={confirm:()=>true,location:{search:''},addEventListener(){},removeEventListener(){}};return createMockElement('div');}
const sample={id:'sample-order',order_number:'SAMPLE-7',customer_name:'SAMPLE',total:{formatted:'PKR 12.34'},order_status:'confirmed',payment_method:'bank_transfer',payment_status:'pending',lines:[],receipts:[{id:'receipt-7',receipt_image_url:'javascript:alert(1)',bank_reference:'<script>bad</script>'}],shipments:[]};
const response=data=>({ok:true,status:200,json:async()=>data});

test('replacement RTO offers inspection only while pending and reconciled',async()=>{
  install();const base={order_id:'SAMPLE-order',order_line_id:'SAMPLE-line',return_type:'size_exchange',status:'completed',quantity:1,received_quantity:1,sellable_quantity:1,damaged_quantity:0,refund_amount:{formatted:'PKR 0'},refund_paid:{formatted:'PKR 0'},refund_outstanding:{minor:0,formatted:'PKR 0'},replacement_shipment_id:'SAMPLE-shipment',replacement_shipment_status:'rto_delivered'};
  globalThis.fetch=async url=>response(url.endsWith('/auth/session')?{csrf_token:'SAMPLE'}:[
    {...base,id:'pending',replacement_stock_reconciliation_status:'reconciled'},
    {...base,id:'done',replacement_rto_inspected_at:'2026-10-15T00:00:00Z'},
    {...base,id:'legacy',replacement_stock_reconciliation_status:'legacy_review'}]);
  const admin=createAdminConsoleModal({page:true,initialTab:'returns'});await admin.open();
  assert.deepEqual(admin.element.querySelectorAll('.btn-inspect-replacement-rto').map(node=>node.dataset.retId),['pending']);
  assert.match(admin.element.querySelector('#admin-tab-content').innerHTML,/Replacement RTO inspection completed/);admin.destroy();
});

test('successful coupon deletion accepts an empty 204 response',async()=>{
  install();globalThis.fetch=async()=>({ok:true,status:204,json:async()=>{throw new Error('No response body');}});
  assert.equal(await deleteAdminCoupon('SAMPLE-coupon'),null);
});

test('supplier acceptance, handoff and expiry decisions send JSON content type to the API',async()=>{
  install();const calls=[];globalThis.fetch=async(url,options)=>{calls.push(options);return response({});};
  await confirmSupplierAcceptance('SAMPLE','SAMPLE ready');
  await markPaymentInstructionsSent('SAMPLE',{channel:'other',reference:'SAMPLE handoff'});
  await resolvePaymentReview('SAMPLE',{resolution:'release_unpaid',note:'SAMPLE checked'});
  assert.equal(calls.length,3);for(const options of calls)assert.equal(options.headers['Content-Type'],'application/json');
});

test('payment evidence is escaped and verification requires explicit cleared-funds confirmation, submits once',async()=>{
  const host=install();let finish;const calls=[];let saved=0;
  globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Promise(resolve=>{finish=resolve;});};
  const markup=orderEvidence(sample);assert.doesNotMatch(markup,/href="javascript:/);assert.match(markup,/&lt;script&gt;/);
  mountFundsReview(host,sample,{isCurrent:()=>true,onSaved:()=>saved++});
  const form=host.querySelector('form');const submit=()=>form.dispatchEvent({type:'submit',preventDefault(){}});
  submit();await tick();assert.equal(calls.length,0);
  form.querySelector('[name="funds_checked"]').checked=true;form.querySelector('[name="receipt_id"]').value='receipt-7';
  submit();submit();await tick();assert.equal(calls.length,1);assert.match(calls[0].url,/receipt_id=receipt-7/);
  finish(response({}));await tick();assert.equal(saved,1);
});

test('access recovery retains failed input and never displays late private codes after session/view change',async()=>{
  const host=install();let current=true,finish;
  globalThis.fetch=async()=>({ok:false,status:400,json:async()=>({detail:'SAMPLE failure'})});
  mountAccessRecovery(host,sample,{isCurrent:()=>current});
  const form=host.querySelector('form');form.querySelector('textarea').value='SAMPLE independently checked customer';
  form.dispatchEvent({type:'submit',preventDefault(){}});await tick();
  assert.match(form.querySelector('[role="status"]').textContent,/SAMPLE failure/);assert.match(form.querySelector('textarea').value,/independently/);
  globalThis.fetch=()=>new Promise(resolve=>{finish=resolve;});
  form.dispatchEvent({type:'submit',preventDefault(){}});await tick();current=false;
  finish(response({order_number:'SAMPLE-7',access_code:'SAMPLE-private-never-display'}));await tick();
  assert.doesNotMatch(host.innerHTML,/SAMPLE-private-never-display/);
});

test('orders paginate/filter without business mutations and coupon currency retains paisas',async()=>{
  install();const calls=[];globalThis.confirm=()=>true;
  globalThis.fetch=async(url,options={})=>{
    calls.push({url,options});const parsed=new URL(url,'http://localhost');
    if(url.endsWith('/auth/session'))return response({csrf_token:'SAMPLE'});
    if(parsed.pathname.endsWith('/admin/orders'))return response({orders:[{...sample,payment_method:'cod'}],total:21,page:Number(parsed.searchParams.get('page')),page_size:20});
    if(parsed.pathname.endsWith('/admin/coupons'))return response(options.method==='POST'?{}:[]);
    return response({});
  };
  const admin=createAdminConsoleModal({page:true,initialTab:'orders'});await admin.open();
  assert.equal(admin.element.querySelector('#dispatch-shipping-cost').getAttribute('step'),'0.01');
  admin.element.querySelector('[data-orders-next]').click();await tick();
  assert.ok(calls.some(c=>c.url.includes('page=2')));
  const filter=admin.element.querySelector('#admin-order-filters');filter.querySelector('[name="search"]').value='SAMPLE-7';filter.querySelector('[name="status"]').value='confirmed';
  filter.dispatchEvent({type:'submit',preventDefault(){}});await tick();
  assert.ok(calls.some(c=>c.url.includes('q=SAMPLE-7')&&c.url.includes('order_status=confirmed')&&c.url.includes('page=1')));
  assert.equal(calls.filter(c=>c.options.method==='POST').length,0);
  admin.selectTab('coupons');await tick();
  assert.equal(admin.element.querySelector('#cpn-min-pkr').getAttribute('step'),'0.01');
  function fillCoupon(value){const form=admin.element.querySelector('#new-coupon-form');for(const[id,v]of[['cpn-code','SAMPLE'],['cpn-type','fixed_amount'],['cpn-val',value],['cpn-min-pkr','100.50'],['cpn-limit','3']])form.querySelector('#'+id).value=v;return form;}
  let form=fillCoupon('12.34');form.dispatchEvent({type:'submit',preventDefault(){}});await tick();
  const post=calls.find(c=>c.options.method==='POST');const body=JSON.parse(post.options.body);assert.equal(body.discount_value,1234);assert.equal(body.min_subtotal_minor,10050);
  form=fillCoupon('12.345');form.dispatchEvent({type:'submit',preventDefault(){}});await tick();
  assert.equal(calls.filter(c=>c.options.method==='POST').length,1);admin.destroy();
});
