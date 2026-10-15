"""Actual owner operations in Chrome, confined to the checkout-disabled M7 stack."""
import base64
from datetime import datetime,timezone
import json,os,secrets,subprocess,sys,time
from pathlib import Path
from websockets.sync.client import connect
from verify_m1_browser import free_port,wait_http

ROOT=Path(__file__).resolve().parents[2]
ORIGIN='http://127.0.0.1:13003'
COMPOSE=['docker','compose','-f','compose.media-check.yml','-f','compose.operations-check.yml']


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    assert json.loads(wait_http('http://127.0.0.1:18003/api/v1/storefront/capabilities'))['checkout_enabled'] is False
    token=secrets.token_hex(4);username='sample_m4_'+token;password=secrets.token_urlsafe(24)
    subprocess.run(COMPOSE+['exec','-T','api','python','scripts/verify_m3_media_runtime.py','--browser-owner',username],cwd=ROOT,input=password.encode(),check=True,stdout=subprocess.DEVNULL)
    fixture=json.loads(subprocess.check_output(COMPOSE+['exec','-T','api','python','scripts/prepare_m7_operations.py',username,token],cwd=ROOT))
    assert fixture['database']=='alphazee_m3_media_test' and fixture['development_modified'] is False
    artifacts=ROOT/'.local/m7-browser'/token;artifacts.mkdir(parents=True)
    port=free_port();processes=[];checks=[];errors=[];answers=[];writes=[];responses=[]
    try:
        env={**os.environ,'VITE_API_PROXY_TARGET':'http://127.0.0.1:18003'}
        commands=[(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','13003','--strictPort','--mode','test'],ROOT/'frontend',env),
            (['C:/Program Files/Google/Chrome/Application/chrome.exe','--headless=new','--disable-extensions','--no-first-run','--disable-background-networking',f'--remote-debugging-port={port}',f'--user-data-dir={artifacts/"profile"}','about:blank'],ROOT,os.environ)]
        for command,cwd,environ in commands:processes.append(subprocess.Popen(command,cwd=cwd,env=environ,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW))
        wait_http(ORIGIN);pages=json.loads(wait_http(f'http://127.0.0.1:{port}/json/list'))
        with connect(next(p for p in pages if p['type']=='page')['webSocketDebuggerUrl']) as ws:
            sequence=0
            def cdp(method,params=None):
                nonlocal sequence
                sequence+=1;ws.send(json.dumps({'id':sequence,'method':method,'params':params or {}}))
                while True:
                    msg=json.loads(ws.recv(timeout=30))
                    if msg.get('method')=='Page.javascriptDialogOpening':
                        dialog=msg['params'];value=answers.pop(0) if dialog['type']=='prompt' and answers else dialog.get('defaultPrompt','')
                        ws.send(json.dumps({'id':100000+sequence,'method':'Page.handleJavaScriptDialog','params':{'accept':True,'promptText':value}}))
                    if msg.get('method')=='Runtime.exceptionThrown':errors.append(msg['params']['exceptionDetails'].get('exception',{}).get('description','Runtime exception'))
                    if msg.get('method')=='Runtime.consoleAPICalled' and msg['params']['type']=='error':errors.append(str(msg['params']['args'])[:300])
                    if msg.get('method')=='Network.requestWillBeSent' and msg['params']['request']['method'] not in ('GET','HEAD','OPTIONS'):writes.append(msg['params']['request']['url'])
                    if msg.get('method')=='Network.responseReceived':responses.append(msg['params']['response'])
                    if msg.get('id')==sequence:
                        if 'error' in msg:raise RuntimeError(str(msg['error']))
                        return msg.get('result',{})
            def evaluate(js):
                result=cdp('Runtime.evaluate',{'expression':js,'returnByValue':True,'awaitPromise':True,'userGesture':True})
                if 'exceptionDetails' in result:raise RuntimeError(str(result['exceptionDetails'])[:500])
                return result.get('result',{}).get('value')
            def expect(js,label):
                for _ in range(160):
                    if evaluate(f'(()=>{{try{{return Boolean({js})}}catch{{return false}}}})()'):
                        checks.append(label);print('Passed:',label,flush=True);return
                    time.sleep(.1)
                print(evaluate('document.body?.innerText.slice(-4000)'),flush=True)
                raise RuntimeError('Acceptance failed: '+label)
            def click(selector):evaluate(f'document.querySelector({json.dumps(selector)}).click()')
            def fill(selector,value,checked=False):evaluate(f'''(()=>{{const n=document.querySelector({json.dumps(selector)});n.{'checked' if checked else 'value'}={json.dumps(value)};n.dispatchEvent(new Event('input',{{bubbles:true}}));n.dispatchEvent(new Event('change',{{bubbles:true}}));}})()''')
            def goto(path):cdp('Page.navigate',{'url':ORIGIN+path})
            def order_path(name):return '/admin/orders?order_id='+fixture[name]['id']
            def order_state(name):return evaluate(f'fetch("/api/v1/admin/orders?order_id={fixture[name]["id"]}").then(r=>r.json()).then(r=>r.orders[0])')
            def ret_button(name,kind):return f'.btn-{kind}[data-ret-id="{fixture[name]["id"]}"]'
            def submit(selector):click(selector+' button[type="submit"]')
            def returns_page():goto('/admin/returns');expect('!!document.querySelector("#admin-return-filters")','returns_route')
            def receive_inspect(name):
                answers.append('1');click(ret_button(name,'receive-ret'));expect(f'!!document.querySelector({json.dumps(ret_button(name,"inspect-ret"))})',name+'_received_quarantine')
                answers.extend(['1','0','SAMPLE inspected sellable']);click(ret_button(name,'inspect-ret'))
                expect(f'!!document.querySelector({json.dumps(ret_button(name,"complete-ret"))})',name+'_inspection_recorded')
            cdp('Page.enable');cdp('Runtime.enable');cdp('Network.enable');cdp('Network.setBlockedURLs',{'urls':['*fonts.googleapis.com*','*fonts.gstatic.com*']})
            cdp('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
            goto(order_path('bank'));expect('!!document.querySelector("#admin-auth-form")','direct_owner_login')
            fill('#admin-username',username);fill('#admin-password',password);click('#admin-login-submit')
            expect('!!document.querySelector(".btn-confirm-supplier")','bank_requires_supplier_acceptance')
            assert not evaluate('!!document.querySelector(".btn-prepare-instructions")');checks.append('no_instructions_before_supplier_acceptance')
            answers.append('SAMPLE supplier ready');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-prepare-instructions")','supplier_confirmed')
            click('.btn-prepare-instructions');expect('!!document.querySelector("#instructions-sent-form")','instructions_preview_is_read_only')
            assert order_state('bank')['payment_instructions_sent_at'] is None
            fill('#instructions-sent-form [name="reference"]','SAMPLE-HANDOFF-'+token);fill('#instructions-sent-form [name="confirmed_sent"]',True,True)
            submit('#instructions-sent-form');expect('document.body.innerText.includes("Instructions sent")','explicit_handoff_recorded')
            bank=order_state('bank');assert bank['payment_deadline_at'] and bank['payment_status']=='pending';checks.append('handoff_sets_deadline_without_verifying_funds')
            subprocess.check_output(COMPOSE+['exec','-T','api','python','scripts/prepare_m7_operations.py','--proof',bank['id']],cwd=ROOT)
            cdp('Page.reload');expect('!!document.querySelector(".admin-order-evidence summary")','proof_order_reloaded');click('.admin-order-evidence summary');expect('document.body.innerText.includes("SAMPLE-M7-PROOF")','proof_reference_available_to_owner')
            click('.btn-verify-payment');expect('!!document.querySelector("[data-funds-review]")','funds_review_form')
            assert order_state('bank')['payment_status']=='pending';checks.append('proof_does_not_verify_bank_funds')
            fill('[name="funds_checked"]',True,True);submit('[data-funds-review]');expect('!!document.querySelector(".btn-dispatch-order")','owner_records_cleared_funds')
            goto(order_path('expired'));expect('!!document.querySelector("#btn-review-expired-orders")','expired_order_read')
            assert order_state('expired')['payment_review_status']=='none';checks.append('opening_orders_does_not_review_expiry')
            click('#btn-review-expired-orders');expect('!!document.querySelector(".btn-resolve-payment")','expiry_explicitly_flagged')
            click('.btn-resolve-payment');fill('#payment-review-form [name="funds_checked"]',True,True);fill('#payment-review-form [name="resolution"]','release_unpaid');fill('#payment-review-form [name="note"]','SAMPLE checked no cleared or pending funds')
            submit('#payment-review-form');expect('document.querySelector("tbody tr").innerText.toLowerCase().includes("cancelled")','explicit_review_releases_unpaid_order')
            assert order_state('expired')['order_status']=='cancelled'
            goto(order_path('cod'));expect('!!document.querySelector(".btn-confirm-supplier")','cod_order_loaded');answers.append('SAMPLE fulfill');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-dispatch-order")','cod_supplier_confirmed')
            click('.btn-dispatch-order');fill('#dispatch-courier-code','manual');fill('#dispatch-tracking-number','SAMPLE-COD-'+token);fill('#dispatch-shipping-cost','1.25');fill('#dispatch-tracking-url','');submit('#admin-dispatch-form')
            expect('!!document.querySelector(".btn-update-shipment[data-next=in_transit]")','cod_dispatched')
            click('.btn-update-shipment[data-next="in_transit"]');expect('!!document.querySelector(".btn-update-shipment[data-next=out_for_delivery]")','cod_in_transit');click('.btn-update-shipment[data-next="out_for_delivery"]')
            expect('!!document.querySelector(".btn-mark-delivered") && !document.querySelector(".btn-update-shipment")','cod_out_for_delivery');click('.btn-mark-delivered');expect('!!document.querySelector(".btn-remit-order")','cod_delivery_recorded')
            click('.btn-remit-order');expect('document.querySelector("#admin-remittance-modal").style.display==="flex"','cod_settlement_open')
            fill('#remit-amount-pkr','246.90');fill('#remit-ref','SAMPLE-COD-RECEIPT-'+token);fill('#remit-final-statement',True,True);submit('#admin-remittance-form')
            expect('document.querySelector("#admin-remittance-modal").style.display==="none"','cod_cash_receipt_saved')
            assert order_state('cod')['shipments'][0]['cod_remittance_status']=='remitted';checks.append('cod_cash_cleared')
            returns_page();click(ret_button('refund','approve-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("refund","receive-ret"))})','refund_approved');receive_inspect('refund')
            click(ret_button('refund','complete-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("refund","record-refund"))})','refund_liability_completed')
            answers.extend(['123.45','SAMPLE-REFUND-'+token]);click(ret_button('refund','record-refund'));expect(f'!!document.querySelector("#admin-return-filters") && !document.querySelector({json.dumps(ret_button("refund","record-refund"))})','refund_fully_paid')
            evaluate(f'''[...document.querySelectorAll('tbody tr')].find(row=>row.innerText.includes({json.dumps(fixture['refund']['id'][:8])})).querySelector('summary').click()''');expect('document.body.innerText.toUpperCase().includes("SAMPLE-REFUND-'+token.upper()+'")','actual_refund_execution_visible')
            answers.append('2.50');click(ret_button('exchange','approve-ret'));expect(f'!!document.querySelector({json.dumps(ret_button("exchange","receive-ret"))})','exchange_stock_reserved');receive_inspect('exchange')
            answers.extend(['manual','SAMPLE-EX-'+token]);click(ret_button('exchange','dispatch-replacement'));expect(f'!!document.querySelector({json.dumps(ret_button("exchange","replacement-status")+"[data-next=in_transit]")})','replacement_dispatched')
            click(ret_button('exchange','replacement-status')+'[data-next="in_transit"]');expect(f'!!document.querySelector({json.dumps(ret_button("exchange","replacement-status")+"[data-next=out_for_delivery]")}) && !document.querySelector({json.dumps(ret_button("exchange","replacement-status")+"[data-next=in_transit]")})','replacement_in_transit')
            click(ret_button('exchange','replacement-status')+'[data-next="out_for_delivery"]');expect(f'!!document.querySelector({json.dumps(ret_button("exchange","replacement-status")+"[data-next=delivered]")}) && !document.querySelector({json.dumps(ret_button("exchange","replacement-status")+"[data-next=out_for_delivery]")})','replacement_out_for_delivery')
            exchange_settlement=f'''[...document.querySelectorAll('tbody tr')].find(row=>row.innerText.includes({json.dumps(fixture['exchange']['id'][:8])})).querySelector('.btn-remit-replacement')'''
            click(ret_button('exchange','replacement-status')+'[data-next="delivered"]');expect(f'!!({exchange_settlement})','replacement_delivered_with_cod_settlement')
            evaluate(f'({exchange_settlement}).click()');expect('document.querySelector("#admin-remittance-modal").style.display==="flex"','replacement_settlement_open')
            fill('#remit-amount-pkr','2.50');fill('#remit-ref','SAMPLE-EX-RECEIPT-'+token);fill('#remit-final-statement',True,True);submit('#admin-remittance-form');expect('document.querySelector("#admin-remittance-modal").style.display==="none"','replacement_charge_receipt_saved')
            goto(order_path('cancel'));expect('!!document.querySelector(".btn-cancel-order")','cancellable_order_loaded');click('.btn-cancel-order');expect('document.querySelector("tbody tr").innerText.toLowerCase().includes("cancelled")','pre_dispatch_cancellation')
            goto(order_path('rto'));expect('!!document.querySelector(".btn-confirm-supplier")','rto_order_loaded');answers.append('SAMPLE fulfill');click('.btn-confirm-supplier');expect('!!document.querySelector(".btn-dispatch-order")','rto_supplier_confirmed')
            click('.btn-dispatch-order');fill('#dispatch-courier-code','manual');fill('#dispatch-tracking-number','SAMPLE-RTO-'+token);fill('#dispatch-shipping-cost','0');fill('#dispatch-tracking-url','');submit('#admin-dispatch-form');expect('!!document.querySelector(".btn-rto-order")','rto_parcel_dispatched')
            answers.extend(['SAMPLE refused parcel','1.25']);click('.btn-rto-order');expect('!!document.querySelector(".btn-rto-receive")','rto_started')
            answers.append('1');click('.btn-rto-receive');expect('!!document.querySelector(".btn-rto-inspect")','rto_received_quarantine')
            answers.extend(['1','0','SAMPLE sellable']);click('.btn-rto-inspect');expect('!!document.querySelector("#admin-order-filters") && !document.querySelector(".btn-rto-inspect")','rto_inspected_once')
            goto(order_path('cod'));expect('!!document.querySelector(".btn-recover-order-access")','historical_delivered_order_accessible');click('.btn-recover-order-access');fill('[name="verification_note"]','SAMPLE independently verified customer through offline evidence');submit('#payment-workflow-panel form')
            expect('!!document.querySelector("[data-clear-private-code]")','owner_access_recovery_issued_once');click('[data-clear-private-code]');assert not evaluate("[...document.querySelectorAll('input')].some(n=>n.getAttribute('aria-label')==='New private access code')");checks.append('private_code_cleared')
            click('.btn-revoke-order-access')
            for _ in range(100):
                evaluate('true')
                if any(r['url'].endswith('/access-revoke') and r['status']==200 for r in responses):break
                time.sleep(.1)
            else:raise RuntimeError('Access revocation was not acknowledged')
            checks.append('owner_access_revocation_recorded')
            goto('/admin/coupons');expect('!!document.querySelector("#new-coupon-form")','coupon_route');fill('#cpn-code','M7-'+token);fill('#cpn-type','fixed_amount');fill('#cpn-val','12.34');fill('#cpn-min-pkr','100.50');fill('#cpn-limit','3');submit('#new-coupon-form')
            expect('document.querySelector("#admin-tab-content").innerText.includes("M7-'+token.upper()+'")','fractional_coupon_created');evaluate(f'''[...document.querySelectorAll('.btn-del-coupon')].find(b=>b.closest('tr').innerText.includes({json.dumps('M7-'+token.upper())})).click()''');expect('!!document.querySelector("#new-coupon-form") && !document.querySelector("#admin-tab-content").innerText.includes("M7-'+token.upper()+'")','coupon_deleted')
            goto('/admin/reports');expect('document.body.innerText.toLowerCase().includes("estimated contribution")','report_financial_definitions');expect('document.body.innerText.toLowerCase().includes("order value (not cash)")','marketing_not_mislabeled_cash')
            (artifacts/'reports-desktop.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{'format':'png'})['data']))
            baseline=len(writes)
            for path,selector in [('/admin','.admin-financial-overview'),('/admin/inventory','#inventory-adjust-form'),('/admin/suppliers','#supplier-variant-form'),('/admin/returns','#admin-return-filters'),('/admin/orders','#admin-order-filters')]:
                goto(path);expect(f'!!document.querySelector({json.dumps(selector)})','navigation_'+path.rsplit('/',1)[-1])
            assert len(writes)==baseline;checks.append('navigation_reads_do_not_mutate_business_state')
            cdp('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True});expect('document.documentElement.scrollWidth<=innerWidth+1','mobile_operations_no_page_overflow')
            if errors:raise RuntimeError('Browser errors: '+str(errors))
        report={'phase':'M7','checked_at_utc':datetime.now(timezone.utc).isoformat(),'database':fixture['database'],'origin':ORIGIN,'checks':checks,'checks_passed':len(checks),'unexpected_browser_errors':errors,'development_modified':False,'public_checkout_enabled':False,'artifacts':str(artifacts.relative_to(ROOT))}
        (ROOT/'.context/m7_browser_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        for process in reversed(processes):
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


if __name__=='__main__':main()
