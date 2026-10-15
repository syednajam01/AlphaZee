"""Final mobile, replacement-RTO and purchased-history checks on SAMPLE lab data."""
import base64,json
from verify_m8_browser import main,ORIGIN

def finish_acceptance(b,context):
    js=b.js;expect=b.expect;click=b.click;fill=b.fill;submit=b.submit
    api=context['api'];goto=context['goto'];owner_order=context['owner_order'];tracking=context['tracking']
    product_id=context['product_id'];slug=context['slug'];token=context['token'];cod=context['cod']
    b.cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
    def mobile_before_submit():
        expect('document.documentElement.scrollWidth<=innerWidth+1','mobile_checkout_no_page_overflow')
        expect('document.querySelector("#checkout-body-content").scrollHeight>document.querySelector("#checkout-body-content").clientHeight','mobile_checkout_content_scrollable')
        js('document.querySelector("#btn-place-order").scrollIntoView({block:"center"})')
        expect('document.querySelector("#btn-place-order").getBoundingClientRect().width>=44','mobile_checkout_submit_touch_target')
        # A real keyboard tab moves focus within the active modal.
        b.cdp('Input.dispatchKeyEvent',{'type':'keyDown','key':'Tab','code':'Tab','windowsVirtualKeyCode':9})
        b.cdp('Input.dispatchKeyEvent',{'type':'keyUp','key':'Tab','code':'Tab','windowsVirtualKeyCode':9})
        expect('!!document.activeElement.closest("[role=dialog]")','mobile_checkout_keyboard_focus_remains_in_dialog')
        (context['artifacts']/'mobile-checkout.png').write_bytes(base64.b64decode(b.cdp('Page.captureScreenshot',{'format':'png'})['data']))
        b.cdp('Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
        click('#btn-place-order')
        expect('document.querySelector("#checkout-error-banner").style.display!=="none" && !document.querySelector("#btn-place-order").disabled','mobile_offline_submission_retains_retry')
        assert js('document.querySelector("#input-customer-name").value')=='SAMPLE M8 '+token
        assert js('window.__m8attempts.length')==0
        b.cdp('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
        b.checks.append('offline_attempt_did_not_confirm_or_clear_customer_input')
    mobile=context['checkout']('cod',before_submit=mobile_before_submit)
    owner_order(mobile)
    expect('document.documentElement.scrollWidth<=innerWidth+1','mobile_private_order_table_contained')
    b.answers.append('SAMPLE mobile supplier');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-dispatch-order")','mobile_order_supplier_accepted')
    click('.btn-dispatch-order');fill('#dispatch-courier-code','manual');fill('#dispatch-tracking-number','SAMPLE-M9-MOBILE-'+token);fill('#dispatch-shipping-cost','0');fill('#dispatch-tracking-url','');submit('#admin-dispatch-form')
    expect('!!document.querySelector(".btn-mark-delivered")','mobile_order_dispatched');click('.btn-mark-delivered');expect('!!document.querySelector(".btn-remit-order")','mobile_order_delivered')
    tracking(mobile);click('#btn-toggle-return-form');fill('#return-select-type','size_exchange')
    expect('document.querySelector("#return-exchange-variant").options.length>0','mobile_exchange_options_loaded')
    submit('#form-submit-return');expect('document.querySelector("#return-req-msg").textContent.toLowerCase().includes("submitted")','mobile_customer_exchange_requested')
    goto('/admin/returns');expect('!!document.querySelector("#admin-return-filters")','mobile_owner_returns_route')
    ret=next(r for r in api('/admin/returns') if r['order_id']==mobile['id'])
    def button(kind):return f'.btn-{kind}[data-ret-id="{ret["id"]}"]'
    b.answers.append('0');click(button('approve-ret'));expect(f'!!document.querySelector({json.dumps(button("receive-ret"))})','rto_replacement_reserved')
    b.answers.append('1');click(button('receive-ret'));expect(f'!!document.querySelector({json.dumps(button("inspect-ret"))})','rto_original_received')
    b.answers.extend(['1','0','SAMPLE original sellable']);click(button('inspect-ret'));expect(f'!!document.querySelector({json.dumps(button("dispatch-replacement"))})','rto_original_inspected')
    b.answers.extend(['manual','SAMPLE-M9-REPLACEMENT-'+token]);click(button('dispatch-replacement'));expect(f'!!document.querySelector({json.dumps(button("replacement-status")+"[data-next=rto_initiated]")})','replacement_rto_available')
    click(button('replacement-status')+'[data-next="rto_initiated"]');expect(f'!!document.querySelector({json.dumps(button("replacement-status")+"[data-next=rto_delivered]")})','replacement_rto_started')
    b.answers.append('1');click(button('replacement-status')+'[data-next="rto_delivered"]');expect(f'!!document.querySelector({json.dumps(button("inspect-replacement-rto"))})','replacement_rto_received_quarantine')
    replacement=next(v for v in context['product']['variants'] if v['id']!=context['variant'])
    stock_path='/admin/catalog/variants/'+str(replacement['id'])+'/stock'
    assert api(stock_path)['mapping']['physical_on_hand']==18
    b.answers.extend(['1','0','SAMPLE replacement inspected sellable']);click(button('inspect-replacement-rto'))
    expect(f'!!document.querySelector("#admin-return-filters") && !document.querySelector({json.dumps(button("inspect-replacement-rto"))})','replacement_rto_inspected_once')
    assert api(stock_path)['mapping']['physical_on_hand']==19
    b.checks.append('replacement_rto_restock_only_after_inspection')
    # Capture immutable purchase evidence and current report before archival.
    before_order=context['order_state'](cod)
    before_returns=[r for r in api('/admin/returns') if r['order_id']==cod['id']]
    before_report=api('/admin/analytics/profit-loss')
    goto('/admin/products');expect(f'!!document.querySelector(\'[data-edit-product="{product_id}"]\')','purchased_product_in_owner_catalog')
    click(f'[data-edit-product="{product_id}"]');expect('!!document.querySelector("#catalog-archive")','purchased_product_editor')
    click('#catalog-archive');expect('document.querySelector("#catalog-product-state").textContent.startsWith("archived")','purchased_product_archived_through_dashboard')
    assert context['order_state'](cod)==before_order
    assert [r for r in api('/admin/returns') if r['order_id']==cod['id']]==before_returns
    assert api('/admin/analytics/profit-loss')==before_report
    b.checks.extend(['archive_preserves_order_snapshots_and_financial_evidence','archive_preserves_customer_returns','archive_does_not_change_financial_summary'])
    assert js(f'fetch("/api/v1/products/{slug}").then(r=>r.status)')==404
    assert js(f'fetch("/api/v1/catalog/products/{product_id}").then(r=>r.status)')==404
    goto('/');expect(f'!!document.querySelector("#site-header") && !document.querySelector(\'.product-card-btn[data-slug="{slug}"]\')','archived_product_removed_from_storefront')
    tracking(mobile);expect('document.querySelector("#tracking-results-area").textContent.includes("SAMPLE M8")','private_tracking_survives_product_archive')
    click('#tracking-close-btn');goto('/admin/reports');expect('document.body.innerText.toLowerCase().includes("estimated contribution")','reports_accessible_after_archive')
    expect('getComputedStyle(document.querySelector(".admin-report-summary")).gridTemplateColumns.split(" ").length===1','mobile_report_cards_stack_readably')
    (context['artifacts']/'mobile-reports.png').write_bytes(base64.b64decode(b.cdp('Page.captureScreenshot',{'format':'png'})['data']))
    b.cdp('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})

if __name__=='__main__':main(phase='M9',additional_checks=finish_acceptance)
