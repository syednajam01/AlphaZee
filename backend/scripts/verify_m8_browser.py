"""Verify actual checkout against the independent lab, never the real catalog."""
import base64,hashlib,http.cookiejar,json,secrets,subprocess,sys,time,urllib.request,urllib.error,zipfile
from datetime import datetime,timezone
from pathlib import Path
from browser_driver import Browser
from verify_m1_browser import wait_http

ROOT=Path(__file__).resolve().parents[2]
LAB=['docker','compose','-f','compose.checkout-lab.yml']
SOURCE=['docker','compose','-f','compose.media-check.yml']
ORIGIN='http://127.0.0.1:13001'

def command(arguments,input=None):
    return subprocess.check_output(arguments,cwd=ROOT,input=input,stderr=subprocess.PIPE)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    token=secrets.token_hex(4);username='sample_m8_'+token;password=secrets.token_urlsafe(24)
    assert json.loads(wait_http(ORIGIN+'/api/v1/storefront/capabilities'))=={'checkout_enabled':True,'test_mode':True,'payment_methods':['cod','bank_transfer']}
    assert json.loads(wait_http('http://localhost:13000/api/v1/storefront/capabilities'))['checkout_enabled'] is False
    fixture=json.loads(command(SOURCE+['exec','-T','api','python','scripts/prepare_m8_source.py',token],password.encode()))
    folder=ROOT/'backend/.local/catalog-transfer';folder.mkdir(parents=True,exist_ok=True);archive=folder/('sample-'+token+'.zip')
    command(SOURCE+['cp','api:'+fixture['archive'],str(archive)])
    with zipfile.ZipFile(archive) as bundle:
        assert b'PRIVATE SUPPLIER NOTES' not in bundle.read('manifest.json')
        assert b'CONTACT MUST NOT COPY' not in bundle.read('manifest.json')
    command(LAB+['exec','-T','api','python','scripts/lab_runtime.py','--provision',username],password.encode())
    importer=LAB+['exec','-T','api','python','scripts/catalog_lab.py','import','/transfer/'+archive.name,'--owner',username,'--stock','20']
    dry=json.loads(command(importer));assert dry['dry_run'] and dry['products'][0]['action']=='create_draft'
    applied=json.loads(command(importer+['--apply']));product_id=applied['products'][0]['id']
    repeated=json.loads(command(importer+['--apply']));assert repeated['products'][0]['action']=='skip_existing'
    artifacts=ROOT/'.local/m8-browser'/token
    with Browser(artifacts) as b:
        js=b.js;expect=b.expect;click=b.click;fill=b.fill;submit=b.submit
        def goto(path):b.goto(ORIGIN+path)
        def api(path):return js(f'fetch("/api/v1{path}").then(r=>r.json())')
        def order_state(order):return api('/admin/orders?order_id='+order['id'])['orders'][0]
        def owner_order(order):goto('/admin/orders?order_id='+order['id']);expect('!!document.querySelector("#admin-order-filters")','private_order_route')
        goto('/admin');expect('!!document.querySelector("#admin-auth-form")','lab_direct_owner_login')
        expect('document.querySelector(".checkout-lab-notice")?.textContent.includes("Do not transfer")','admin_simulation_banner')
        fill('#admin-username',username);fill('#admin-password',password);click('#admin-login-submit');expect('!!document.querySelector(".admin-financial-overview")','lab_owner_authenticated')
        product=api('/admin/products/'+product_id)
        assert product['status']=='draft' and product['variants'][0]['id']!=15
        assert len(product['media'])==2 and product['media'][1]['asset']['poster_id']
        holds=api('/admin/catalog/variants/'+str(product['variants'][0]['id'])+'/stock')
        # The quantity was explicitly chosen, not copied from the source's 73 units.
        assert holds['mapping']['physical_on_hand']==20 and holds['mapping']['held_reservations']==0
        for link in product['media']:
            content=urllib.request.urlopen(ORIGIN+link['asset']['url']).read()
            source=next(a for a in fixture['assets'] if a['kind']==link['asset']['kind'])
            assert hashlib.sha256(content).hexdigest()==source['checksum']
        b.checks.extend(['catalog_only_bundle','dry_run_before_import','draft_media_and_poster_remapped','explicit_stock_not_source_stock','rerun_skips_existing','copied_media_checksums_match'])
        # Publish through the same owner API client used by the authoring workspace.
        js(f'''import('/src/utils/api.js').then(api=>api.transitionOwnerProduct({json.dumps(product_id)},'publish',{product['edit_version']}))''')
        b.checks.append('imported_draft_reviewed_then_published')
        slug=product['slug'];variant=product['variants'][0]['id']
        def checkout(method,quantity=1,drop=False):
            goto('/');expect(f'!!document.querySelector(\'.product-card-btn[data-slug="{slug}"]\')','copied_product_on_storefront')
            click(f'.product-card-btn[data-slug="{slug}"]');expect('!!document.querySelector("#btn-modal-add-to-cart") && !document.querySelector("#btn-modal-add-to-cart").disabled','variant_purchasable')
            click('#btn-modal-add-to-cart');click('#btn-cart');expect('!!document.querySelector(".cart-item")','cart_contains_copied_variant')
            if quantity==2:click('.btn-qty-inc')
            expect('!document.querySelector("#btn-checkout").disabled','checkout_open_in_lab');click('#btn-checkout')
            expect('!!document.querySelector("#checkout-form")','customer_checkout_form')
            for selector,value in [('#input-customer-name','SAMPLE M8 '+token),('#input-customer-phone','03001234567'),('#input-shipping-address-1','SAMPLE fixture street'),('#input-shipping-city','Lahore'),('#input-shipping-province','Punjab')]:fill(selector,value)
            expect('!document.querySelector("#btn-place-order").disabled && document.querySelector("#checkout-form").checkValidity()','customer_form_valid_and_ready')
            expect(f'!document.querySelector(\'[name="payment_method"][value="{method}"]\').disabled','selected_payment_method_available')
            click('[name="payment_method"][value="'+method+'"]')
            assert js('document.querySelector("[name=payment_method]:checked").value')==method
            js('''(()=>{const original=window.fetch.bind(window);window.__m8attempts=[];window.__m8drop='''+str(drop).lower()+''';window.fetch=async(url,options)=>{const res=await original(url,options);if(String(url).endsWith('/orders')&&options?.method==='POST'&&res.ok){window.__m8created=await res.clone().json();window.__m8attempts.push({key:options.headers['Idempotency-Key'],id:window.__m8created.id});if(window.__m8drop){window.__m8drop=false;throw new TypeError('SAMPLE lost response');}}return res;};})()''')
            click('#btn-place-order')
            if drop:
                expect('document.querySelector("#checkout-error-banner").style.display!=="none" && !document.querySelector("#btn-place-order").disabled','lost_response_preserves_checkout_for_retry');click('#btn-place-order')
            expect('!!document.querySelector("#checkout-access-code")','order_confirmation_and_private_code')
            created=js('({id:window.__m8created.id,order_number:window.__m8created.order_number,total:window.__m8created.total.minor})')
            if drop:
                assert js('window.__m8attempts.length===2 && window.__m8attempts[0].id===window.__m8attempts[1].id && window.__m8attempts[0].key===window.__m8attempts[1].key');b.checks.append('lost_response_retry_same_order_and_attempt_key')
            click('#btn-finish-checkout');return created
        cod=checkout('cod',2,True);owner_order(cod)
        stock=api('/admin/catalog/variants/'+str(variant)+'/stock')
        assert stock['mapping']['physical_on_hand']==20 and stock['mapping']['held_reservations']==2 and stock['mapping']['available_to_sell']==18
        assert any(h['order_id']==cod['id'] and h['quantity']==2 for h in stock['mapping']['holds'])
        b.checks.append('customer_order_visible_to_owner_with_exact_hold')
        b.answers.append('SAMPLE supplier accepts');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-dispatch-order")','checkout_order_supplier_acceptance')
        click('.btn-dispatch-order');fill('#dispatch-courier-code','manual');fill('#dispatch-tracking-number','SAMPLE-M8-'+token);fill('#dispatch-shipping-cost','1.25');fill('#dispatch-tracking-url','');submit('#admin-dispatch-form')
        expect('!!document.querySelector(".btn-mark-delivered")','checkout_order_dispatched');click('.btn-mark-delivered');expect('!!document.querySelector(".btn-remit-order")','checkout_order_delivered')
        click('.btn-remit-order');expect('document.querySelector("#admin-remittance-modal").style.display==="flex"','cod_settlement_dialog')
        fill('#remit-amount-pkr',format(cod['total']/100,'.2f'));fill('#remit-ref','SAMPLE-M8-COD-'+token);fill('#remit-final-statement',True,True);submit('#admin-remittance-form')
        expect('document.querySelector("#admin-remittance-modal").style.display==="none"','customer_cod_settlement_saved')
        assert order_state(cod)['shipments'][0]['cod_remittance_status']=='remitted'
        def tracking(order):
            goto('/');expect('!!document.querySelector("#nav-track-order")','customer_tracking_navigation');click('#nav-track-order');fill('#tracking-order-num',order['order_number']);click('#btn-search-order');expect('document.querySelector("#tracking-results-area").style.display!=="none"','private_tracking_session_restored')
        tracking(cod);click('#btn-toggle-return-form');click('#form-submit-return button[type="submit"]')
        expect('document.querySelector("#return-req-msg").textContent.toLowerCase().includes("submitted")','customer_return_requested')
        goto('/admin/returns');expect('!!document.querySelector(".btn-approve-ret")','owner_sees_customer_return')
        returns=api('/admin/returns');ret=next(r for r in returns if r['order_id']==cod['id'])
        def ret_button(kind):return f'.btn-{kind}[data-ret-id="{ret["id"]}"]'
        click(ret_button('approve-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("receive-ret"))})','customer_return_approved')
        b.answers.append('1');click(ret_button('receive-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("inspect-ret"))})','customer_return_received')
        b.answers.extend(['1','0','SAMPLE inspected']);click(ret_button('inspect-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("complete-ret"))})','customer_return_inspected')
        click(ret_button('complete-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("record-refund"))})','customer_return_liability')
        b.answers.extend(['123.45','SAMPLE-PAID-'+token]);click(ret_button('record-refund'));expect(f'!!document.querySelector("#admin-return-filters") && !document.querySelector({json.dumps(ret_button("record-refund"))})','customer_refund_paid')
        tracking(cod);click('#btn-toggle-return-form');fill('#return-select-type','size_exchange')
        expect('document.querySelector("#return-exchange-variant").options.length>0','customer_exchange_options_from_purchased_product')
        submit('#form-submit-return');expect('document.querySelector("#return-req-msg").textContent.toLowerCase().includes("submitted")','customer_exchange_requested')
        goto('/admin/returns');expect('!!document.querySelector("#admin-return-filters")','owner_exchange_route')
        ret=next(r for r in api('/admin/returns') if r['order_id']==cod['id'] and r['return_type']=='size_exchange')
        b.answers.append('0');click(ret_button('approve-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("receive-ret"))})','exchange_replacement_reserved')
        b.answers.append('1');click(ret_button('receive-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("inspect-ret"))})','exchange_received')
        b.answers.extend(['1','0','SAMPLE exchange inspected']);click(ret_button('inspect-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("dispatch-replacement"))})','exchange_original_inspected')
        b.answers.extend(['manual','SAMPLE-M8-EX-'+token]);click(ret_button('dispatch-replacement'));expect(f'!!document.querySelector({json.dumps(ret_button("replacement-status")+"[data-next=delivered]")})','customer_replacement_dispatched')
        click(ret_button('replacement-status')+'[data-next="delivered"]');expect(f'''[...document.querySelectorAll('tbody tr')].find(row=>row.innerText.includes({json.dumps(ret['id'][:8])})).innerText.includes('Replacement: delivered')''','customer_replacement_delivered')
        bank=checkout('bank_transfer');owner_order(bank);b.answers.append('SAMPLE bank supplier acceptance');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-prepare-instructions")','bank_supplier_before_instructions')
        click('.btn-prepare-instructions');expect('!!document.querySelector("#instructions-sent-form")','simulated_bank_preview');fill('#instructions-sent-form [name="reference"]','SAMPLE SIMULATED HANDOFF');fill('#instructions-sent-form [name="confirmed_sent"]',True,True);submit('#instructions-sent-form')
        expect('document.body.innerText.includes("Instructions sent")','simulated_bank_handoff')
        tracking(bank);expect('!!document.querySelector("#track-receipt-form")','proof_form_after_handoff')
        fill('#track-receipt-url',ORIGIN+'/favicon.svg');fill('#track-receipt-ref','SAMPLE-PROOF-'+token);submit('#track-receipt-form')
        expect('document.querySelector("#track-receipt-status").textContent.toLowerCase().includes("receipt submitted")','customer_proof_submitted')
        owner_order(bank);assert order_state(bank)['payment_status']=='pending';b.checks.append('proof_is_not_automatic_funds_verification')
        click('.btn-verify-payment');fill('[name="funds_checked"]',True,True);submit('[data-funds-review]');expect('!!document.querySelector(".btn-dispatch-order")','simulated_cleared_funds_verified')
        cancelled=checkout('cod');owner_order(cancelled);click('.btn-cancel-order');expect('document.querySelector("tbody tr").innerText.toLowerCase().includes("cancelled")','lab_cancellation_releases_hold')
        expired=checkout('bank_transfer');owner_order(expired);b.answers.append('SAMPLE expiry acceptance');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-prepare-instructions")','expiry_supplier_acceptance')
        click('.btn-prepare-instructions');expect('!!document.querySelector("#instructions-sent-form")','expiry_preview')
        fill('#instructions-sent-form [name="reference"]','SAMPLE EXPIRY HANDOFF');fill('#instructions-sent-form [name="confirmed_sent"]',True,True);submit('#instructions-sent-form');expect('document.body.innerText.includes("Instructions sent")','expiry_handoff')
        command(LAB+['exec','-T','api','python','scripts/lab_runtime.py','--expire',expired['id']])
        owner_order(expired);assert order_state(expired)['payment_review_status']=='none';click('#btn-review-expired-orders');expect('!!document.querySelector(".btn-resolve-payment")','lab_expiry_explicit_review')
        click('.btn-resolve-payment');fill('#payment-review-form [name="funds_checked"]',True,True);fill('#payment-review-form [name="resolution"]','release_unpaid');fill('#payment-review-form [name="note"]','SAMPLE no actual or pending funds in simulation');submit('#payment-review-form')
        expect('document.querySelector("tbody tr").innerText.toLowerCase().includes("cancelled")','lab_expiry_release_after_review')
        goto('/admin/reports');expect('document.body.innerText.toLowerCase().includes("estimated contribution")','lab_reports_from_checkout_orders')
        (artifacts/'reports.png').write_bytes(base64.b64decode(b.cdp('Page.captureScreenshot',{'format':'png'})['data']))
        # A valid non-lab session and lab session coexist on the same cookie host.
        jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        request=urllib.request.Request('http://127.0.0.1:18003/api/v1/auth/login',data=json.dumps({'username':username,'password':password}).encode(),headers={'Origin':'http://127.0.0.1:13003','Content-Type':'application/json'})
        with client.open(request) as response:assert response.status==200
        source_cookie=next(c for c in jar if c.name=='alphazee_owner_session')
        b.cdp('Network.setCookie',{'name':source_cookie.name,'value':source_cookie.value,'domain':'127.0.0.1','path':'/','httpOnly':True,'sameSite':'Strict'})
        assert api('/auth/session').get('csrf_token')
        with client.open('http://127.0.0.1:18003/api/v1/auth/session') as response:assert response.status==200
        cookies=b.cdp('Network.getCookies',{'urls':[ORIGIN]})['cookies']
        names={c['name'] for c in cookies}
        assert {'alphazee_owner_session','alphazee_lab_owner_session','alphazee_lab_order_session','alphazee_lab_checkout_session'}<=names
        lab_token=next(c['value'] for c in cookies if c['name']=='alphazee_lab_owner_session')
        def rejected(url,cookie):
            try:urllib.request.urlopen(urllib.request.Request(url,headers={'Cookie':cookie}))
            except urllib.error.HTTPError as error:return error.code==401
            return False
        assert rejected('http://127.0.0.1:18003/api/v1/auth/session','alphazee_owner_session='+lab_token)
        assert rejected(ORIGIN+'/api/v1/auth/session','alphazee_lab_owner_session='+source_cookie.value)
        assert rejected('http://localhost:13000/api/v1/auth/session','alphazee_owner_session='+lab_token)
        b.checks.extend(['non_lab_and_lab_sessions_coexist_on_same_host','all_three_lab_cookie_names_isolated','cross_database_tokens_rejected'])
        click('#btn-admin-logout');expect('!!document.querySelector("#admin-auth-form")','lab_logout')
        assert js('fetch("/api/v1/admin/orders").then(r=>r.status)')==401
        assert any(c['name']=='alphazee_owner_session' and c['value']==source_cookie.value for c in b.cdp('Network.getCookies',{'urls':[ORIGIN]})['cookies'])
        b.checks.append('lab_logout_preserves_non_lab_session')
        goto('/');expect('!!document.querySelector(".product-card-btn")','lab_storefront_reload')
        b.cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        expect('document.documentElement.scrollWidth<=innerWidth+1','mobile_lab_no_page_overflow')
        assert not b.errors,b.errors
        report={'phase':'M8','checked_at_utc':datetime.now(timezone.utc).isoformat(),'origin':ORIGIN,'database':'alphazee_checkout_test',
            'checks':b.checks,'checks_passed':len(b.checks),'unexpected_browser_errors':b.errors,'normal_development_modified':False,
            'lab_checkout_enabled':True,'public_checkout_enabled':False,'artifacts':str(artifacts.relative_to(ROOT))}
    (ROOT/'.context/m8_browser_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
