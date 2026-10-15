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


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    prepared = json.loads((ROOT / '.local/m3-media-check/runtime-prepared.json').read_text())
    assert prepared['database'] == 'alphazee_m3_media_test' and prepared['development_modified'] is False
    assert json.loads(wait_http('http://127.0.0.1:18003/api/v1/storefront/capabilities'))['checkout_enabled'] is False
    token = secrets.token_hex(4)
    username, password = 'sample_m4_' + token, secrets.token_urlsafe(24)
    subprocess.run(['docker', 'compose', '-f', 'compose.media-check.yml', 'exec', '-T', 'api',
                    'python', 'scripts/verify_m3_media_runtime.py', '--browser-owner', username],
                   cwd=ROOT, input=password.encode(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    artifacts = ROOT / '.local/m4-browser' / token; artifacts.mkdir(parents=True)
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
                    if message.get('method') == 'Network.requestWillBeSent':
                        request = message['params']['request']
                        if '/api/v1/admin/products/' in request['url'] and request.get('postData'):
                            data = json.loads(request['postData']); print('SAMPLE catalog request:', request['url'].split('/api/v1')[-1], data, flush=True)
                    if message.get('method') == 'Page.javascriptDialogOpening':
                        # Fixture-only discard/archive prompts are intentionally accepted.
                        ws.send(json.dumps({'id': 100000 + sequence, 'method': 'Page.handleJavaScriptDialog', 'params': {'accept': True}}))
                    if message.get('method') == 'Runtime.exceptionThrown': failures.append('runtime_exception')
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
                    if evaluate(f'Boolean({expression})'): checks.append(label); print('Passed:', label, flush=True); return
                    time.sleep(.1)
                print('UI diagnostic:', evaluate('document.body.innerText.slice(-3000)'), flush=True)
                raise RuntimeError('Browser acceptance failed: ' + label)
            def fill(selector, value, checked=False):
                evaluate(f'(() => {{ const n=document.querySelector({json.dumps(selector)}); n.{"checked" if checked else "value"}={json.dumps(value)}; n.dispatchEvent(new Event("input", {{bubbles:true}})); n.dispatchEvent(new Event("change", {{bubbles:true}})); }})()')
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
            expect('document.querySelector("[name=description]").value === "SAMPLE authored description"', 'description_saved_without_loss')
            files([first, second, video]); expect('document.querySelectorAll(".catalog-upload-row").length===3 && [...document.querySelectorAll(".catalog-upload-row")].every(n=>n.innerText.includes("accepted"))', 'multiple_image_video_uploads_accepted')
            def choose_asset(name, role):
                identifier = evaluate(f'[...document.querySelector("#catalog-attach-asset").options].find(o=>o.textContent.startsWith({json.dumps(name)})).value')
                fill('#catalog-attach-asset', identifier); fill('#catalog-attach-role', role); click('#catalog-attach'); return identifier
            image_id = choose_asset(first.name, 'primary'); second_id = choose_asset(second.name, 'gallery'); video_id = choose_asset(video.name, 'gallery')
            print('Description after upload/attach:', evaluate('document.querySelector("[name=description]").value'), flush=True)
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
            print('Description revisited:', evaluate('document.querySelector("[name=description]").value'), flush=True)
            fill('[name="is_hero"]', True, checked=True); choose_asset(video.name, 'hero_video'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'featured_video_and_poster_saved')
            click('#catalog-publish'); expect('document.querySelector("#catalog-product-state").textContent.startsWith("published")', 'complete_product_published')
            public = evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.json())')
            assert public['variants'][0]['price']['minor'] == 12345 and public['image_url'].endswith(image_id + '/content'); checks.append('storefront_json_matches_saved_media_price')
            fill('[name="description"]', 'SAMPLE edited description'); fill('[name="price"]', '99.95'); choose_asset(second.name, 'primary'); click('#catalog-save-product')
            expect('document.querySelector("#catalog-status").textContent === "Product and media saved."', 'published_description_price_primary_replaced')
            cdp('Page.reload'); expect('!!document.querySelector("#catalog-new-product")', 'session_and_route_survive_refresh'); open_product()
            expect('document.querySelector("[name=description]").value==="SAMPLE edited description" && document.querySelector("[name=price]").value==="99.95"', 'edits_survive_refresh')
            before = evaluate('document.querySelector(".catalog-media-card img, .catalog-media-card video").src')
            evaluate('document.querySelector("[data-link-down]:not([disabled])").focus()')
            cdp('Input.dispatchKeyEvent', {'type':'keyDown','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
            cdp('Input.dispatchKeyEvent', {'type':'keyUp','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
            expect(f'document.querySelector(".catalog-media-card img, .catalog-media-card video").src!=={json.dumps(before)}', 'gallery_reorder_works_from_keyboard')
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
            expect('document.querySelector("#catalog-status").textContent.includes("record changed") && document.querySelector("[name=description]").value==="SAMPLE unsaved conflict input"', 'stale_edit_error_preserves_input')
            click('#catalog-reload-product'); expect('document.querySelector("[name=description]").value==="SAMPLE concurrent edit"', 'conflict_reload_explicitly_recovers')
            click('#catalog-archive'); expect('document.querySelector("#catalog-product-state").textContent.startsWith("archived")', 'archive_retains_edit_history')
            assert evaluate(f'fetch("/api/v1/products/sample-m4-{token}").then(r=>r.status)') == 404; checks.append('archived_product_hidden_publicly')
            click('#btn-admin-logout'); expect('!!document.querySelector("#admin-auth-form")', 'logout_clears_owner_view')
            if failures: raise RuntimeError('Unexpected browser console/runtime failure: ' + str(failures))
        report = {'phase': 'M4', 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'browser': 'headless Chrome via CDP',
                  'origin': ORIGIN, 'database': 'alphazee_m3_media_test', 'checks': checks, 'checks_passed': len(checks),
                  'artifacts': str(artifacts.relative_to(ROOT)), 'development_modified': False, 'unexpected_browser_errors': failures}
        (ROOT / '.context/m4_browser_verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        for process in reversed(processes):
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == '__main__': main()
