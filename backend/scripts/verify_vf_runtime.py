"""Read-only HTTP smoke checks for the two local stacks; no browser or order writes."""
import json
from pathlib import Path
import urllib.error
import urllib.request


def request(base, path, expected, method='GET', payload=None, origin=None):
    headers = {'Origin': origin or base}
    data = None
    if method == 'POST':
        data = json.dumps(payload or {}).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    assert status == expected, f'{base}{path}: expected {expected}, got {status}'
    return body


def main():
    results = []
    for port, api_port, lab in [(13000, 18000, False), (13001, 18001, True)]:
        web = f'http://127.0.0.1:{port}'
        api = f'http://127.0.0.1:{api_port}'
        checks = []
        for base in [web, api]:
            for path in ['/api/v1/health', '/api/v1/ready', '/api/v1/storefront/capabilities']:
                body = request(base, path, 200)
                if path.endswith('capabilities'):
                    capabilities = json.loads(body)
                    assert capabilities['checkout_enabled'] is lab
                checks.append({'port': port if base == web else api_port, 'path': path, 'status': 200})
            status = 200 if lab else 503
            request(base, '/api/v1/orders/checkout-session', status)
            checks.append({'path': '/api/v1/orders/checkout-session', 'status': status})
            # Never place a lab order here; containment is checked on both closed endpoints.
            if not lab:
                for path in ['/api/v1/orders', '/api/v1/orders/quote']:
                    request(base, path, 503, 'POST', origin=web)
                    checks.append({'path': path, 'status': 503})
            request(base, '/api/v1/auth/session', 401)
            request(base, '/api/v1/vendor/auth/session', 401)
        for path in ['/', '/admin', '/vendor']:
            body = request(web, path, 200)
            assert b'<html' in body.lower()
            checks.append({'path': path, 'status': 200})
        results.append({'environment': 'lab' if lab else 'development', 'checks': checks})
    target = Path(__file__).resolve().parents[2] / '.local/vf-runtime-verification.json'
    target.write_text(json.dumps({'browser_verified': False, 'results': results}, indent=2), encoding='utf-8')
    print('PASS: both stacks ready; public checkout contained; lab checkout session enabled; private sessions guarded; page shells served.')


if __name__ == '__main__':
    main()
