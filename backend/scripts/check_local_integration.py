"""Terminal-only HTTP smoke checks; no browser or database writes."""
import json
from pathlib import Path
import urllib.error
import urllib.request


def fetch(url, *, method='GET', payload=None):
    request = urllib.request.Request(url, data=payload, method=method)
    if payload is not None:
        request.add_header('Content-Type', 'application/json')
    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read().decode('utf-8')
        return response.status, body


results = []
paths = ['/api/v1/health', '/api/v1/ready', '/api/v1/storefront/capabilities',
         '/api/v1/collections', '/api/v1/products', '/api/v1/products/hero']
for origin in ['http://127.0.0.1:8000', 'http://127.0.0.1:3000']:
    for path in paths:
        status, body = fetch(origin + path)
        data = json.loads(body)
        assert status == 200, (origin, path, status)
        if path.endswith('/ready'):
            assert data == {'status': 'ready', 'database': 'connected'}
        if path.endswith('/capabilities'):
            assert data == {'checkout_enabled': False, 'test_mode': False}
        results.append({'url': origin + path, 'status': status, 'response': data})
    # Empty payload cannot create an order, even if the gate regresses.
    status, body = fetch(origin + '/api/v1/orders', method='POST', payload=b'{}')
    assert status == 503, ('Public checkout must remain closed', status)
    results.append({'url': origin + '/api/v1/orders', 'method': 'POST (empty payload)', 'status': status})
    status, _ = fetch(origin + '/api/v1/admin/overview')
    assert status == 401, ('Anonymous owner access must remain rejected', status)
    results.append({'url': origin + '/api/v1/admin/overview', 'status': status})

for path, expected in [
    ('/', '<div id="app">'),
    ('/src/main.js', 'startStorefront'),
    ('/src/app.js', 'initApp'),
    ('/src/utils/overlay.js', 'surface.hidden'),
    ('/src/utils/startup.js', 'DOMContentLoaded'),
    ('/src/styles/components.css', 'display: none !important'),
]:
    status, body = fetch('http://127.0.0.1:3000' + path)
    assert status == 200 and expected in body, path
    results.append({'url': 'http://127.0.0.1:3000' + path, 'status': status, 'expected_source_found': True})

report = {'verification': 'terminal HTTP only; no browser execution', 'checks': results}
destination = Path(__file__).resolve().parents[2] / '.context' / 'phase_l1_http_checks.json'
destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'{len(results)} HTTP checks passed; evidence saved to {destination}')
