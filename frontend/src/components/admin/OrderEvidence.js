import {escapeHtml as esc, sanitizeMediaUrl} from '../../utils/dom.js';
import {formatPkr} from '../../utils/money.js';
import {verifyOrderPayment, recoverAdminOrderAccess} from '../../utils/api.js';

export function orderEvidence(order) {
  return `<details class="admin-order-evidence"><summary>Order details and payment evidence</summary>
    <p>${[order.shipping_address_line1, order.shipping_address_line2, order.shipping_city, order.shipping_province, order.shipping_postal_code].filter(Boolean).map(esc).join(', ')}</p>
    ${order.customer_notes ? `<p>Customer notes: ${esc(order.customer_notes)}</p>` : ''}
    <ul>${(order.lines || []).map(line => `<li>${esc(line.product_title)} / ${esc(line.variant_sku)} ${esc(line.size || '')} ${esc(line.color || '')} · ${line.quantity} × ${esc(line.unit_price?.formatted || '')} · ${esc(line.fulfillment_kind || 'original')}</li>`).join('') || '<li>No purchased line details available.</li>'}</ul>
    <p>Supplier accepted: ${esc(order.supplier_confirmed_at || 'Awaiting acceptance')}${order.supplier_notes ? ' · '+esc(order.supplier_notes) : ''}</p>
    <p>Payment proof is evidence only. Verify cleared funds in the bank independently.</p>
    <ul>${(order.receipts || []).map(receipt => { const url=sanitizeMediaUrl(receipt.receipt_image_url,''); return `<li>${esc(receipt.bank_reference || 'No bank reference')} · ${esc(receipt.uploaded_at || '')} · ${receipt.verified_at ? 'Verified by owner' : 'Not verified'} ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Open payment proof</a>` : 'Proof URL unavailable'}</li>`; }).join('') || '<li>No customer payment proof submitted.</li>'}</ul>
    ${(order.shipments || []).map(s => `<p>Shipment ${esc(s.tracking_number)} · ${esc(s.status)}${s.replacement_return_id ? ' · replacement' : ''}</p>`).join('')}
    </details>`;
}

export function mountFundsReview(panel, order, {isCurrent,onSaved}) {
  panel.innerHTML = `<form data-funds-review class="admin-operation-form"><h3>Verify bank funds for ${esc(order.order_number)}</h3>
    ${orderEvidence(order)}<p>Order amount: ${esc(order.total?.formatted || '')}. This records received bank funds; supplier acceptance remains separate.</p>
    <label>Receipt to mark verified (optional)<select name="receipt_id"><option value="">Independent bank verification; no selected proof</option>${(order.receipts || []).map(r=>`<option value="${esc(r.id)}">${esc(r.bank_reference || r.id)}</option>`).join('')}</select></label>
    <label><input type="checkbox" name="funds_checked" required> I checked the bank account and confirmed cleared funds for this order</label>
    <button type="submit" class="btn btn-primary">Record verified bank funds</button><p role="status" aria-live="polite"></p></form>`;
  const form=panel.querySelector('form'), button=form.querySelector('button');
  form.addEventListener('submit',async event=>{
    event.preventDefault(); if (button.disabled || !isCurrent()) return;
    const feedback=form.querySelector('[role="status"]');
    if (!form.querySelector('[name="funds_checked"]').checked) { feedback.textContent='Confirm cleared funds before recording verification.'; return; }
    button.disabled=true; feedback.textContent='Recording bank verification…';
    try { await verifyOrderPayment(order.id,form.querySelector('[name="receipt_id"]').value || null); if(isCurrent()) await onSaved(); }
    catch(error) { if(isCurrent()) {feedback.textContent=error.message; button.disabled=false;} }
  });
}

export function mountAccessRecovery(panel, order, {isCurrent,onIssued=()=>{}}) {
  panel.innerHTML=`<form class="admin-operation-form"><h3>Recover access for ${esc(order.order_number)}</h3>
    <label>How you independently verified this customer<textarea name="verification_note" minlength="10" maxlength="500" required></textarea></label>
    <button type="submit" class="btn btn-primary">Issue a new private code</button><p role="status" aria-live="polite"></p></form>`;
  const form=panel.querySelector('form'), button=form.querySelector('button');
  form.addEventListener('submit',async event=>{
    event.preventDefault(); if(button.disabled || !isCurrent())return;
    const note=form.querySelector('textarea').value.trim(), status=form.querySelector('[role="status"]');
    if(note.length<10){status.textContent='Enter a verification note of at least 10 characters.';return;}
    button.disabled=true; status.textContent='Issuing code…';
    try {
      const result=await recoverAdminOrderAccess(order.id,note); if(!isCurrent())return;
      onIssued();
      panel.innerHTML=`<div class="admin-operation-form"><h3>Private code for ${esc(result.order_number)}</h3><p>Copy and convey it only through your independently verified customer channel. It is shown once.</p><input aria-label="New private access code" readonly value="${esc(result.access_code)}"><button type="button" class="btn btn-secondary" data-clear-private-code>Clear code from this view</button></div>`;
      panel.querySelector('button').addEventListener('click',()=>{panel.textContent='Private code cleared. It cannot be retrieved again.';});
    } catch(error) {if(isCurrent()){status.textContent=error.message;button.disabled=false;}}
  });
}

export function returnEvidence(ret) {
  return `<details><summary>Return references and refund history</summary><p>Order <a href="/admin/orders?order_id=${encodeURIComponent(ret.order_id)}">${esc(ret.order_id)}</a> · line ${esc(ret.order_line_id)}</p>
    <p>${esc(ret.inspection_notes || 'No inspection notes recorded.')}</p>
    <ul>${(ret.refund_executions || []).map(r=>`<li>${esc(formatPkr(r.amount_minor))} · ${esc(r.channel)} · ${esc(r.reference)} · ${esc(r.executed_at)}</li>`).join('') || '<li>No executed refund payments recorded.</li>'}</ul></details>`;
}
