"""Actual catalog authoring in Chrome against the isolated M3 Docker API."""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
from PIL import Image
from websockets.sync.client import connect
from verify_m1_browser import free_port, wait_http

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'http://127.0.0.1:13003'


def main(phase='M4'):
    sys.stdout.reconfigure(encoding='utf-8')
    prepared = json.loads((ROOT / '.local/m3-media-check/runtime-prepared.json').read_text())
    assert prepared['database'] == 'alphazee_m3_media_test' and prepared['development_modified'] is False
    assert json.loads(wait_http('http://127.0.0.1:18003/api/v1/storefront/capabilities'))['checkout_enabled'] is False
    token = secrets.token_hex(4)
    username, password = 'sample_m4_' + token, secrets.token_urlsafe(24)
    subprocess.run(['docker', 'compose', '-f', 'compose.media-check.yml', 'exec', '-T', 'api',
                    'python', 'scripts/verify_m3_media_runtime.py', '--browser-owner', username],
                   cwd=ROOT, input=password.encode(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    artifacts = ROOT / ('.local/' + phase.lower() + '-browser') / token; artifacts.mkdir(parents=True)
    first, second, video, corrupt = [artifacts / ('SAMPLE-' + token + name) for name in ('-a.png', '-b.png', '-video.mp4', '-corrupt.png')]
    Image.new('RGB', (80, 60), 'navy').save(first)
    Image.new('RGB', (80, 60), 'green').save(second)
    with urllib.request.urlopen('http://127.0.0.1:18003' + prepared['assets'][1]['url']) as response: video.write_bytes(response.read())
    corrupt.write_bytes(b'<html>not an image</html>')
    cdp_port = free_port()
    chrome = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    env = {**os.environ, 'VITE_API_PROXY_TARGET': 'http://127.0.0.1:18003'}
    commands = [(['node', str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '13003', '--strictPort', '--mode', 'test'], ROOT / 'frontend', env),
                ([str(chrome), '--headless=new', '--disable-extensions', '--no-first-run', '--disable-background-networking',
                  f'--remote-debugging-port={cdp_port}', f'--user-data-dir={artifacts / "profile"}', 'about:blank'], ROOT, os.environ)]
    processes, checks, failures = [], [], []
    try:
        for args, cwd, environment in commands:
            processes.append(subprocess.Popen(args, cwd=cwd, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
        wait_http(ORIGIN)
        pages = json.loads(wait_http(f'http://127.0.0.1:{cdp_port}/json/list'))
        page = next(p for p in pages if p.get('type') == 'page' and not p.get('url','').startswith('chrome-extension:'))
        with connect(page['webSocketDebuggerUrl']) as ws:
            sequence = 0
            def cdp(method, params=None):
                nonlocal sequence
                sequence += 1; ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
                while True:
                    message = json.loads(ws.recv(timeout=30))
                    if message.get('method') == 'Page.javascriptDialogOpening':
                        # Fixture-only discard/archive prompts are intentionally accepted.
                        ws.send(json.dumps({'id': 100000 + sequence, 'method': 'Page.handleJavaScriptDialog', 'params': {'accept': True}}))
                    if message.get('method') == 'Runtime.exceptionThrown':
                        detail = message['params']['exceptionDetails']
                        failure = {'text': detail.get('exception', {}).get('description', detail.get('text')), 'url': detail.get('url'),
                                   'stack': detail.get('stackTrace', {}).get('callFrames', [])[:4]}
                        failures.append(failure); print('Runtime error:', json.dumps(failure), flush=True)
                    if message.get('method') == 'Runtime.consoleAPICalled' and message['params']['type'] == 'error':
                        description = ' '.join(str(a.get('description', a.get('value',''))) for a in message['params']['args'])
                        if 'Failed to load resource' not in description: failures.append(description[:300])
                    if message.get('id') == sequence:
                        if 'error' in message: raise RuntimeError('CDP command failed')
                        return message.get('result', {})
            def evaluate(expression):
                result = cdp('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
                if 'exceptionDetails' in result: raise RuntimeError('Browser evaluation failed: ' + str(result['exceptionDetails'])[:300])
                return result.get('result', {}).get('value')
            def expect(expression, label):
                for _ in range(150):
                    if evaluate(f'(() => {{ try {{ return Boolean({expression}); }} catch {{ return false; }} }})()'): checks.append(label); print('Passed:', label, flush=True); return
                    time.sleep(.1)
                print('UI diagnostic:', evaluate('document.body.innerText.slice(-3000)'), flush=True)
                raise RuntimeError('Browser acceptance failed: ' + label)
            def fill(selector, value, checked=False):
                evaluate(f'(() => {{ const n=[...document.querySelectorAll({json.dumps(selector)})].find(n=>n.matches("input,select,textarea")); n.{"checked" if checked else "value"}={json.dumps(value)}; n.dispatchEvent(new Event("input", {{bubbles:true}})); n.dispatchEvent(new Event("change", {{bubbles:true}})); }})()')
            def click(selector):
                evaluate(f'document.querySelector({json.dumps(selector)}).click()')
            def files(paths):
                root = cdp('DOM.getDocument')['root']['nodeId']
                node = cdp('DOM.querySelector', {'nodeId': root, 'selector': '#catalog-file-input'})['nodeId']
                cdp('DOM.setFileInputFiles', {'nodeId': node, 'files': [str(p.resolve()) for p in paths]})
            def open_product():
                evaluate(f'[...document.querySelectorAll("[data-edit-product]")].find(b=>b.closest("article").innerText.includes({json.dumps("SAMPLE M4 " + token)})).click()')
                expect('!!document.querySelector("#catalog-product-form")', 'product_editor_opened')
            cdp('Page.enable'); cdp('Runtime.enable'); cdp('Network.enable')
            cdp('Network.setBlockedURLs', {'urls': ['*fonts.googleapis.com*','*fonts.gstatic.com*']})
            cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False})
            cdp('Page.navigate', {'url': ORIGIN + '/admin/collections'})
            expect('!!document.querySelector("#admin-auth-form")', 'direct_login')
            fill('#admin-username', username); fill('#admin-password', password); click('#admin-login-submit')
            expect('!!document.querySelector("#catalog-new-collection")', 'collections_route_after_login')
            click('#catalog-new-collection'); fill('[name="name"]', 'SAMPLE M4 ' + token); fill('[name="slug"]', 'sample-m4-' + token); click('#catalog-save-collection')
            expect('document.querySelector("#catalog-status").textContent === "Collection saved."', 'collection_created_through_ui')
            click('[data-tab="products"]'); expect('!!document.querySelector("#catalog-new-product")', 'products_route')
            click('#catalog-new-product'); expect('!!document.querySelector("#catalog-product-form")', 'incomplete_draft_created')
            fill('[name="title"]', 'SAMPLE M4 ' + token); fill('[name="slug"]', 'sample-m4-' + token); fill('[name="description"]', 'SAMPLE authored description')
            collection_id = evaluate(f'[...document.querySelector("[name=collection_id]").options].find(o=>o.textContent==={json.dumps("SAMPLE M4 " + token)}).value')
            fill('[name="collection_id"]', collection_id)
            click('#catalog-add-variant'); fill('[name="sku"]', 'SAMPLE-M4-' + token); fill('[name="size"]', 'M'); fill('[name="color"]', 'Blue'); fill('[name="price"]', '123.45'); fill('[name="variant_active"]', True, checked=True)
            click('#catalog-save-product'); expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'draft_and_exact_fractional_price_saved')
            expect('document.querySelector("#catalog-product-form [name=description]").value === "SAMPLE authored description"', 'description_saved_without_loss')
            files([first, second, video]); expect('document.querySelectorAll(".catalog-upload-row").length===3 && [...document.querySelectorAll(".catalog-upload-row")].every(n=>n.innerText.includes("accepted"))', 'multiple_image_video_uploads_accepted')
            expect(f'[...document.querySelector("#catalog-attach-asset").options].some(o=>o.textContent.startsWith({json.dumps(video.name)}))', 'uploaded_assets_available_in_picker')
            def choose_asset(name, role):
                identifier = evaluate(f'[...document.querySelector("#catalog-attach-asset").options].find(o=>o.textContent.startsWith({json.dumps(name)})).value')
                fill('#catalog-attach-asset', identifier); fill('#catalog-attach-role', role); click('#catalog-attach'); return identifier
            image_id = choose_asset(first.name, 'primary'); second_id = choose_asset(second.name, 'gallery'); video_id = choose_asset(video.name, 'gallery')
            fill('[name="alt_text"]', 'SAMPLE primary description'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'primary_and_gallery_saved')
            click('#catalog-publish'); expect('document.querySelector("#catalog-status").textContent.includes("poster")', 'publication_missing_poster_actionable')
            video_selector = '[data-library-asset="' + video_id + '"]'
            click('[data-tab="media"]'); expect(f'!!document.querySelector({json.dumps(video_selector)})', 'media_library_usage_visible')
            fill(f'[data-library-asset="{video_id}"] [name="poster_id"]', image_id); click(f'[data-save-poster="{video_id}"]')
            expect('document.querySelector("#catalog-status").textContent === "Video poster saved."', 'video_poster_saved')
            files([corrupt]); expect('document.querySelector(".catalog-upload-row").innerText.includes("failed")', 'invalid_upload_shows_error_and_retry')
            expect('!!document.querySelector("[data-upload-retry]")', 'failed_file_retained_for_retry')
            click('[data-tab="products"]'); expect('!!document.querySelector("#catalog-new-product")', 'return_to_products'); open_product()
            fill('[name="is_hero"]', True, checked=True); choose_asset(video.name, 'hero_video'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'featured_video_and_poster_saved')
            click('#catalog-publish'); expect('document.querySelector("#catalog-product-state").textContent.startsWith("published")', 'complete_product_published')
            if phase in {'M5', 'M6'}:
                fill('[name="availability"]', 'available'); click('#catalog-save-product')
                expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'm5_owner_availability_saved')
                click('[data-load-stock]')
                expect('!!document.querySelector("[data-new-supplier]")', 'm5_stock_panel_loaded')
                fill('[name="stock_new_name"]', 'SAMPLE M5 ' + token); fill('[name="stock_new_slug"]', 'sample-m5-' + token)
                click('[data-new-supplier]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("Supplier registered")', 'm5_inline_supplier_registered')
                fill('[name="stock_cost"]', '12.34'); click('[data-save-mapping]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("cost saved")', 'm5_exact_wholesale_mapping_saved')
                expect('document.querySelector(".variant-stock-panel").innerText.includes("No active holds")', 'm5_zero_holds_visible')
                fill('[name="stock_delta"]', '10'); fill('[name="stock_reference"]', 'SAMPLE-M5-INVOICE'); fill('[name="stock_notes"]', 'SAMPLE stock received')
                click('[data-adjust-stock]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("adjustment saved")', 'm5_versioned_receipt_saved')
                variant_id = evaluate('Number(document.querySelector("[data-variant-stock]").dataset.variantStock)')
                payload = json.loads(subprocess.check_output(['docker', 'compose', '-f', 'compose.media-check.yml', 'exec', '-T', 'api',
                    'python', 'scripts/prepare_m5_holds.py', str(variant_id)], cwd=ROOT))
                click('[data-reload-stock]')
                expect('document.querySelector(".variant-stock-panel").innerText.includes("6 units reserved across 3 holds")', 'm5_two_orders_and_legacy_hold_reconcile')
                expect('document.querySelector(".variant-stock-panel").innerText.includes("legacy reconciliation required")', 'm5_legacy_hold_explained')
                expect('document.querySelector("[data-current-holds]").innerText.includes("Physical 10 / Reserved 6 / Available 4")', 'm5_stock_triple_matches_breakdown')
                public_stock = evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.json())')
                assert public_stock['variants'][0]['availability'] == 'available' and 'supplier_cost_minor' not in json.dumps(public_stock)
                checks.append('m5_public_eligibility_and_private_cost')
                # Verify the real anchor reloads the owner route and filters the order.
                target = evaluate('document.querySelector("[data-current-holds] a").href')
                cdp('Page.navigate', {'url': target})
                expect(f'document.body.innerText.includes({json.dumps(payload["orders"][0]["number"])}) || document.body.innerText.includes({json.dumps(payload["orders"][1]["number"])})', 'm5_hold_links_to_filtered_order')
                expect('document.querySelectorAll(".btn-recover-order-access").length===1 && new URLSearchParams(location.search).has("order_id")', 'm5_order_link_filter_applied')
                cdp('Page.navigate', {'url': ORIGIN + '/admin/products'})
                expect('!!document.querySelector("#catalog-new-product")', 'm5_return_to_products'); open_product(); click('[data-load-stock]')
                expect('!!document.querySelector("[data-current-holds]")', 'm5_holds_survive_navigation')
                fill('[name="stock_delta"]', '-9'); click('[data-adjust-stock]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("below 6 active holds") && document.querySelector("[name=stock_delta]").value==="-9"', 'm5_invalid_adjustment_retains_input')
                click('[data-reload-stock]')
                expect('document.querySelector("[name=stock_delta]").value===""', 'm5_explicit_stock_reload_recovers')
                fill('[name="stock_new_name"]', 'SAMPLE M5 replacement ' + token); fill('[name="stock_new_slug"]', 'sample-m5-next-' + token)
                click('[data-new-supplier]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("Supplier registered")', 'm5_second_supplier_registered')
                fill('[name="stock_cost"]', '23.45'); click('[data-save-mapping]')
                expect('document.querySelector("[data-stock-feedback]").textContent.includes("cost saved")', 'm5_supplier_switched')
                evaluate('document.querySelector("[data-history-holds]").parentElement.querySelector("summary").click()')
                expect('document.querySelector("[data-history-holds]").innerText.includes("Physical 10 / Reserved 6 / Available 4") && document.querySelector("[data-current-holds]").innerText.includes("Physical 0 / Reserved 0 / Available 0")', 'm5_historical_allocations_preserved')
                assert evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.json()).then(p=>p.variants[0].availability)') == 'unavailable'
                checks.append('m5_empty_new_supplier_prevents_purchase')
                if phase == 'M6':
                    fill('[name="stock_delta"]', '10'); click('[data-adjust-stock]')
                    expect('document.querySelector("[data-stock-feedback]").textContent.includes("adjustment saved")', 'm6_receive_replacement_supplier_stock')
            public = evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.json())')
            assert public['variants'][0]['price']['minor'] == 12345 and public['image_url'].endswith(image_id + '/content'); checks.append('storefront_json_matches_saved_media_price')
            fill('[name="description"]', 'SAMPLE edited description'); fill('[name="price"]', '99.95'); choose_asset(second.name, 'primary'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'published_description_price_primary_replaced')
            cdp('Page.reload'); expect('!!document.querySelector("#catalog-new-product")', 'session_and_route_survive_refresh'); open_product()
            expect('document.querySelector("#catalog-product-form [name=description]").value==="SAMPLE edited description" && document.querySelector("[name=price]").value==="99.95"', 'edits_survive_refresh')
            order_expression = '[...document.querySelectorAll(".catalog-media-card")].map(n=>n.querySelector("strong").textContent+":"+n.querySelector("img,video").src).join("|")'
            before = evaluate(order_expression)
            evaluate('document.querySelector("[data-link-down]:not([disabled])").focus()')
            cdp('Input.dispatchKeyEvent', {'type':'keyDown','key':' ','code':'Space','windowsVirtualKeyCode':32,'text':' '})
            cdp('Input.dispatchKeyEvent', {'type':'keyUp','key':' ','code':'Space','windowsVirtualKeyCode':32})
            expect(f'({order_expression})!=={json.dumps(before)}', 'gallery_reorder_works_from_keyboard')
            click('#catalog-save-product'); expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'gallery_order_saved')
            expect('!!document.querySelector("video") && document.querySelector("video").readyState>=1', 'actual_browser_video_metadata_loaded')
            assert evaluate('(() => {const v=document.querySelector("video");v.muted=true;return v.play().then(()=>true).catch(()=>false);})()'); checks.append('actual_browser_video_playback')
            screenshot = cdp('Page.captureScreenshot', {'format': 'png'})['data']; (artifacts / 'desktop.png').write_bytes(base64.b64decode(screenshot))
            cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
            expect('document.documentElement.scrollWidth<=window.innerWidth+1', 'mobile_has_no_page_overflow')
            screenshot = cdp('Page.captureScreenshot', {'format': 'png'})['data']; (artifacts / 'mobile.png').write_bytes(base64.b64decode(screenshot))
            evaluate('''(async()=>{const session=await fetch('/api/v1/auth/session').then(r=>r.json());const list=await fetch('/api/v1/admin/products').then(r=>r.json());
              const p=list.products.find(p=>p.title===document.querySelector('[name=title]').value);return fetch('/api/v1/admin/products/'+p.id,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:JSON.stringify({expected_version:p.edit_version,description:'SAMPLE concurrent edit'})}).then(r=>r.status);})()''')
            fill('[name="description"]','SAMPLE unsaved conflict input'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent.includes("record changed") && document.querySelector("#catalog-product-form [name=description]").value==="SAMPLE unsaved conflict input"', 'stale_edit_error_preserves_input')
            click('#catalog-reload-product'); expect('document.querySelector("#catalog-product-form [name=description]").value==="SAMPLE concurrent edit"', 'conflict_reload_explicitly_recovers')
            if phase == 'M6':
                fill('[name="material"]','SAMPLE cotton'); fill('[name="care"]','SAMPLE cold wash'); fill('[name="sizing"]','SAMPLE relaxed fit')
                fill('[name="is_hero"]', True, checked=True)
                click('#catalog-add-variant')
                for name, value in [('sku','SAMPLE-M6-L-'+token),('size','L'),('color','Green'),('price','150.25'),('availability','available')]:
                    fill('#catalog-variants .catalog-variant:last-child [name="'+name+'"]', value)
                fill('#catalog-variants .catalog-variant:last-child [name="variant_active"]', True, checked=True)
                click('#catalog-save-product')
                expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'm6_details_and_second_variant_saved')
                second_variant = evaluate('Number(document.querySelector(".catalog-variant:last-child").dataset.variantId)')
                choose_asset(first.name,'gallery')
                fill('.catalog-media-card:last-child [name="media_variant"]', str(second_variant)); fill('.catalog-media-card:last-child [name="alt_text"]','SAMPLE green variant image')
                click('#catalog-save-product')
                expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'm6_variant_gallery_saved')
                public = evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.json())')
                product_id, first_variant = public['id'], next(v['id'] for v in public['variants'] if v['sku']=='SAMPLE-M4-'+token)
                evaluate(f'''(async()=>{{const api=await import('/src/utils/api.js');const list=await api.fetchOwnerCollections();const c=list.collections.find(c=>c.id==={json.dumps(collection_id)});return api.updateOwnerCollection(c.id,{{expected_version:c.edit_version,image_media_id:{json.dumps(second_id)}}});}})()''')
                media_urls = [m['url'] for m in public['media'] if m['kind']=='video']
                # Capture requests to prove product grids do not download gallery videos.
                cdp('Performance.enable')
                cdp('Page.navigate', {'url': ORIGIN + '/'})
                card = '#product-'+product_id
                expect(f'!!document.querySelector({json.dumps(card)})', 'm6_real_product_card_visible')
                expect(f'document.querySelector({json.dumps(card+" img")}).src.endsWith({json.dumps(second_id+"/content")})', 'm6_card_uses_updated_managed_primary')
                expect(f'[...document.querySelectorAll(".hero-cta-btn")].some(b=>b.dataset.id==={json.dumps(product_id)})', 'm6_managed_hero_visible')
                expect(f'document.querySelector({json.dumps("[data-collection="+chr(34)+collection_id+chr(34)+"] img")}).src.endsWith({json.dumps(second_id+"/content")})', 'm6_collection_uses_managed_cover')
                assert evaluate('document.querySelectorAll(".products-grid video").length') == 0
                checks.append('m6_grid_never_loads_gallery_video')
                click(card+' .product-card-btn')
                expect('document.querySelector("#product-modal").innerText.includes("SAMPLE cotton") && document.querySelector("#product-modal").innerText.includes("SAMPLE cold wash") && document.querySelector("#product-modal").innerText.includes("SAMPLE relaxed fit")', 'm6_material_care_sizing_rendered')
                expect(f'document.querySelector(".product-gallery-stage img").src.endsWith({json.dumps(second_id+"/content")})', 'm6_gallery_starts_on_primary')
                assert not evaluate("[...document.querySelectorAll('[data-gallery-index]')].some(b=>b.getAttribute('aria-label')==='View image: SAMPLE green variant image')"); checks.append('m6_other_variant_image_hidden')
                evaluate('[...document.querySelectorAll("[data-gallery-index]")].find(b=>b.textContent.includes("Video")).click()')
                expect('!!document.querySelector(".product-gallery-stage video") && document.querySelector(".product-gallery-stage video").controls && !!document.querySelector(".product-gallery-stage video").poster', 'm6_gallery_video_has_controls_and_poster')
                assert evaluate('document.querySelector(".product-gallery-stage video").preload') == 'none'; checks.append('m6_gallery_video_defers_download')
                assert evaluate('(() => { const v=document.querySelector(".product-gallery-stage video"); v.muted=true; return v.play().then(()=>true).catch(()=>false); })()'); checks.append('m6_gallery_video_really_plays')
                click('[data-size="L"]'); click('[data-color="Green"]')
                expect(f'document.querySelector(".product-gallery-stage img").src.endsWith({json.dumps(image_id+"/content")}) && document.querySelector("#btn-modal-add-to-cart").disabled', 'm6_variant_specific_media_and_unavailable_stock')
                click('[data-size="M"]'); click('[data-color="Blue"]'); click('#btn-modal-add-to-cart')
                expect('!document.querySelector("#cart-drawer").hidden && document.querySelector("#cart-subtotal").textContent.includes("99.95")', 'm6_cart_has_selected_variant_and_exact_price')
                expect(f'document.querySelector("#checkout-items-list img").src.endsWith({json.dumps(second_id+"/content")})', 'm6_checkout_summary_uses_managed_image')
                click('#cart-close-btn')
                # Use the same accepted owner client that broadcasts to the storefront.
                def edit_owner(fields):
                    return evaluate(f'''(async()=>{{const api=await import('/src/utils/api.js');await api.fetchOwnerSession();const p=await api.fetchOwnerProduct({json.dumps(product_id)});return api.updateOwnerProduct(p.id,{{expected_version:p.edit_version,...{json.dumps(fields)}}});}})()''')
                edit_owner({'slug':'sample-m6-renamed-'+token,'description':'SAMPLE live description', 'variants':[{'id':first_variant,'price_minor':23456}]})
                expect(f'document.querySelector({json.dumps(card)}).innerText.includes("150.25") && document.querySelector({json.dumps(card+" .product-card-btn")}).dataset.slug==={json.dumps("sample-m6-renamed-"+token)}', 'm6_accepted_owner_edit_refreshes_storefront')
                click('#btn-cart')
                expect('document.querySelector("#cart-subtotal").textContent.includes("234.56")', 'm6_cart_follows_stable_identity_after_slug_change')
                assert evaluate(f'JSON.parse(localStorage.getItem("alphazee_cart_v2"))[0].variant_id') == first_variant
                checks.append('m6_cart_never_substitutes_variant')
                click('#cart-close-btn'); click(card+' .product-card-btn')
                expect('document.querySelector("#product-modal").innerText.includes("SAMPLE live description")', 'm6_detail_refetches_latest_description')
                cdp('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
                expect('document.documentElement.scrollWidth<=window.innerWidth+1', 'm6_mobile_gallery_no_overflow')
                (artifacts/'storefront-mobile.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot', {'format':'png'})['data']))
                click('#modal-close-btn')
                edit_owner({'variants':[{'id':first_variant,'is_active':False}]})
                click('#btn-cart')
                expect('document.querySelector("#cart-availability-alert").style.display!=="none" && document.querySelector("#btn-checkout").disabled', 'm6_deactivated_variant_blocks_saved_cart')
                click('#cart-close-btn')
                evaluate(f'''(async()=>{{const api=await import('/src/utils/api.js');const p=await api.fetchOwnerProduct({json.dumps(product_id)});return api.transitionOwnerProduct(p.id,'unpublish',p.edit_version);}})()''')
                expect(f'!document.querySelector({json.dumps(card)})', 'm6_unpublish_removes_card')
                assert evaluate(f'fetch("/api/v1/catalog/products/{product_id}").then(r=>r.status)') == 404; checks.append('m6_unpublished_identity_is_private')
                cdp('Page.navigate', {'url':ORIGIN+'/admin/products'}); expect('!!document.querySelector("#catalog-new-product")','m6_return_to_owner'); open_product()
            click('#catalog-archive'); expect('document.querySelector("#catalog-product-state").textContent.startsWith("archived")', 'archive_retains_edit_history')
            if phase == 'M6':
                assert evaluate(f'fetch("/api/v1/catalog/products/{product_id}").then(r=>r.status)') == 404; checks.append('m6_archived_identity_is_private')
            assert evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.status)') == 404; checks.append('archived_product_hidden_publicly')
            click('#btn-admin-logout'); expect('!!document.querySelector("#admin-auth-form")', 'logout_clears_owner_view')
            if failures:
                (artifacts/'runtime-errors.json').write_text(json.dumps(failures, indent=2))
                raise RuntimeError('Unexpected browser console/runtime failure: ' + str(failures))
        report = {'phase': phase, 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'browser': 'headless Chrome via CDP',
                  'origin': ORIGIN, 'database': 'alphazee_m3_media_test', 'checks': checks, 'checks_passed': len(checks),
                  'artifacts': str(artifacts.relative_to(ROOT)), 'development_modified': False, 'unexpected_browser_errors': failures}
        (ROOT / ('.context/' + phase.lower() + '_browser_verification.json')).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        for process in reversed(processes):
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == '__main__': main('M6' if '--phase-m6' in sys.argv else ('M5' if '--phase-m5' in sys.argv else 'M4'))
