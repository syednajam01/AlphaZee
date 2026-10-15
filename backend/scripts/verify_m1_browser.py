"""Headless Chrome/CDP acceptance with a fresh isolated database and SAMPLE owner."""
from datetime import datetime, timezone
import base64
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.services.owners import provision_owner


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_http(url):
    for _ in range(50):
        try:
            with urlopen(url, timeout=.5) as response:
                return response.read()
        except Exception:
            time.sleep(.2)
    raise RuntimeError('Isolated service did not become ready')


def main(*, report_name='m1_browser_verification.json', phase='M1', normal_admin_check=False):
    sys.stdout.reconfigure(encoding='utf-8')
    source = make_url(settings.database_url)
    if source.get_backend_name() != 'postgresql' or source.host not in {'localhost', '127.0.0.1', '::1'} or source.query:
        raise RuntimeError('Require loopback PostgreSQL without connection overrides')
    chrome = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    if not chrome.is_file():
        raise RuntimeError('Chrome executable unavailable; browser checks not executed')
    name = f'alphazee_{phase.lower()}_browser_' + uuid.uuid4().hex[:10] + '_test'
    target = source.set(database=name)
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as db:
        db.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
    admin.dispose()
    api_port, web_port, cdp_port = free_port(), free_port(), free_port()
    origin = f'http://127.0.0.1:{web_port}'
    env = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False),
           'APP_ENV': 'test', 'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false',
           'ALLOWED_ORIGINS': origin, 'VITE_API_PROXY_TARGET': f'http://127.0.0.1:{api_port}'}
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT / 'backend',
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    engine = create_engine(target, hide_parameters=True)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db:
        provision_owner(db, 'sample_m1_owner', password)
        db.commit()
    artifacts = ROOT / '.local' / f'{phase.lower()}-browser' / uuid.uuid4().hex[:10]
    artifacts.mkdir(parents=True)
    processes = []
    checks = []
    events = []
    try:
        for args, cwd, environment in [
            ([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(api_port)], ROOT / 'backend', env),
            (['node', str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(web_port), '--mode', 'test'], ROOT / 'frontend', env),
            ([str(chrome), '--headless=new', '--no-first-run', '--no-default-browser-check',
              '--disable-background-networking', '--disable-extensions', f'--remote-debugging-port={cdp_port}',
              f'--user-data-dir={artifacts / "profile"}', 'about:blank'], ROOT, os.environ),
        ]:
            processes.append(subprocess.Popen(args, cwd=cwd, env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        wait_http(f'http://127.0.0.1:{api_port}/api/v1/ready')
        wait_http(origin)
        print('Isolated API and frontend ready; checking Chrome', flush=True)
        pages = json.loads(wait_http(f'http://127.0.0.1:{cdp_port}/json/list'))
        page = next(item for item in pages if item.get('type') == 'page' and not item.get('url', '').startswith('chrome-extension:'))
        with connect(page['webSocketDebuggerUrl'], open_timeout=10) as ws:
            sequence = 0
            console_errors = []
            request_urls = {}
            def cdp(method, params=None):
                nonlocal sequence
                sequence += 1
                ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
                while True:
                    message = json.loads(ws.recv(timeout=15))
                    if message.get('method') == 'Runtime.exceptionThrown': events.append('runtime_exception')
                    if message.get('method') == 'Runtime.consoleAPICalled' and message['params']['type'] == 'error':
                        console_errors.extend(arg.get('description', arg.get('value', '')) for arg in message['params']['args'])
                    if message.get('method') == 'Network.requestWillBeSent':
                        request_urls[message['params']['requestId']] = message['params']['request']['url']
                    if (message.get('method') == 'Network.loadingFailed' and not message.get('params', {}).get('canceled')
                            and request_urls.get(message['params']['requestId'], '').startswith(origin)):
                        events.append('network_failure')
                    if message.get('id') == sequence:
                        if 'error' in message: raise RuntimeError('CDP command failed')
                        return message.get('result', {})
            def evaluate(expression):
                value = cdp('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
                if 'exceptionDetails' in value: raise RuntimeError('Browser evaluation failed')
                return value.get('result', {}).get('value')
            def expect(expression, label):
                for _ in range(80):
                    if evaluate(f'(() => {{ try {{ return Boolean({expression}); }} catch {{ return false; }} }})()'):
                        checks.append(label); return
                    time.sleep(.1)
                print('Browser diagnostic:', evaluate('document.body.innerText.slice(0,1000)'), flush=True)
                if label == 'direct_login':
                    print('Startup diagnostic:', console_errors, flush=True)
                    print('Page state:', evaluate('JSON.stringify({url:location.href,ready:document.readyState,html:document.documentElement.outerHTML.slice(0,1600)})'), flush=True)
                    print('Requested:', list(request_urls.values())[:8], flush=True)
                raise RuntimeError('Browser check failed: ' + label)
            def click(selector):
                point = evaluate(f'(() => {{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect(); return {{x:r.x+r.width/2,y:r.y+r.height/2}};}})()')
                cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', **point, 'button': 'left', 'clickCount': 1})
                cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', **point, 'button': 'left', 'clickCount': 1})
            def screenshot(name):
                encoded = cdp('Page.captureScreenshot', {'format': 'png'})['data']
                (artifacts / name).write_bytes(base64.b64decode(encoded))
            cdp('Page.enable'); cdp('Runtime.enable'); cdp('Network.enable')
            # Verify functionality without dependence on remote typography.
            cdp('Network.setBlockedURLs', {'urls': ['*fonts.googleapis.com*', '*fonts.gstatic.com*']})
            cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
            print('Navigate:', cdp('Page.navigate', {'url': origin + '/admin/orders'}), flush=True)
            expect('!!document.querySelector("#admin-auth-form")', 'direct_login')
            expect('getComputedStyle(document.querySelector("#admin-sidebar")).display === "none"', 'private_navigation_hidden')
            evaluate(f'document.querySelector("#admin-username").value="sample_m1_owner"; document.querySelector("#admin-password").value={json.dumps(password)}; document.querySelector("#admin-auth-form").requestSubmit(); true')
            expect('!document.querySelector("#admin-auth-form") && document.querySelector("#admin-tab-content").textContent.includes("No customer orders")', 'login_orders')
            if phase == 'M2':
                result = evaluate('''(async () => {
                  const session = await fetch('/api/v1/auth/session').then(r => r.json());
                  const headers = {'Content-Type':'application/json', 'X-CSRF-Token':session.csrf_token};
                  const response = await fetch('/api/v1/admin/products', {method:'POST',headers,
                    body:JSON.stringify({title:'SAMPLE browser draft',variants:[{sku:'SAMPLE-BROWSER-M2',price_minor:123450}]})});
                  const product = await response.json();
                  const publish = await fetch('/api/v1/admin/products/'+product.id+'/publish', {method:'POST',headers,
                    body:JSON.stringify({expected_version:product.edit_version})});
                  const publicCatalog = await fetch('/api/v1/products').then(r=>r.json());
                  return response.status===201 && product.status==='draft' && product.variants[0].price_minor===123450 && publish.status===422 && publicCatalog.total===0;
                })()''')
                if not result: raise RuntimeError('Browser catalog draft/publication guard failed')
                checks.append('owner_catalog_draft_and_publication_guard')
            click('[data-tab="products"]')
            expect('location.pathname === "/admin/products" && document.querySelector("#admin-tab-content").textContent.includes("coming next")', 'products_route_placeholder')
            evaluate('window.__m1ReloadSentinel = true; true')
            cdp('Page.reload')
            expect('window.__m1ReloadSentinel === undefined && !document.querySelector("#admin-auth-form") && document.querySelector("#admin-tab-content").textContent.includes("coming next")', 'refresh_restores_session_and_section')
            click('[data-tab="inventory"]')
            expect('location.pathname === "/admin/inventory" && !document.querySelector("#admin-tab-content").textContent.includes("Loading")', 'inventory_route')
            evaluate('history.back(); true')
            expect('location.pathname === "/admin/products" && document.querySelector("#admin-tab-content").textContent.includes("coming next")', 'back_navigation')
            evaluate('history.forward(); true')
            expect('location.pathname === "/admin/inventory" && !document.querySelector("#admin-tab-content").textContent.includes("Loading")', 'forward_navigation')
            screenshot('desktop-dashboard.png')
            cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
            expect('document.documentElement.scrollWidth <= 390', 'mobile_no_document_overflow')
            screenshot('mobile-dashboard.png')
            click('#btn-admin-logout')
            expect('!!document.querySelector("#admin-auth-form")', 'logout_login_screen')
            status = evaluate('fetch("/api/v1/admin/overview").then(r=>r.status)')
            if status != 401: raise RuntimeError('Owner endpoint accepted logged-out session')
            checks.append('logout_server_revocation')
            # The test owner/session is isolated; expire it directly to check the UI.
            evaluate(f'document.querySelector("#admin-username").value="sample_m1_owner"; document.querySelector("#admin-password").value={json.dumps(password)}; document.querySelector("#admin-auth-form").requestSubmit(); true')
            expect('!document.querySelector("#admin-auth-form")', 'second_login')
            with engine.begin() as db:
                db.execute(text("UPDATE owner_sessions SET expires_at=now()-interval '1 minute'"))
            click('#btn-refresh-admin-tab')
            expect('!!document.querySelector("#admin-auth-form") && document.querySelector("#admin-session-message").textContent.includes("session has ended")', 'expired_session_login_screen')
            if normal_admin_check:
                cdp('Page.navigate', {'url': 'http://localhost:13000/admin'})
                expect('location.origin === "http://localhost:13000" && !!document.querySelector("#admin-auth-form") && !document.querySelector("#nav-track-order") && document.querySelector("#admin-session-message").textContent === ""', 'actual_normal_admin_shows_login_not_home')
                screenshot('normal-admin-login.png')
            if events: raise RuntimeError('Browser runtime/network errors observed')
        report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'phase': phase,
                  'database': name, 'sample_owner_only': True, 'source_database_modified': False,
                  'checkout_enabled': False, 'browser': 'headless Chrome via CDP', 'checks': checks,
                  'runtime_network_errors': events, 'screenshots': str(artifacts.relative_to(ROOT)),
                  'external_fonts_blocked_to_verify_local_startup': True,
                  'passed': True, 'database_retained': True}
        (ROOT / '.context' / report_name).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        engine.dispose()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase-m2', action='store_true')
    args = parser.parse_args()
    if args.phase_m2:
        main(report_name='m2_browser_verification.json', phase='M2', normal_admin_check=True)
    else:
        main()
